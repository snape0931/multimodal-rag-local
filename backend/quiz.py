"""
Quiz Me: writes multiple-choice questions from one PDF.

How it works
  * Chunks of the PDF are picked evenly across the whole document.
  * The language model writes ONE question per chunk, so every question is
    grounded in a specific passage and its page number is reliable.
  * The model returns the correct answer and 3 wrong answers separately; we
    shuffle them ourselves (small models love putting the right answer first).
  * Questions are yielded one by one, so the first appears within seconds.

Put this file in backend/ and call quiz_events() from main.py.
"""

import json
import random
import re

import ollama

from backend.broad_queries import _even_sample, _fetch, _sort_key
from backend.generation import ANSWER_MODEL, KEEP_ALIVE
from backend.retrieval import text_collection

# num_ctx matches the other calls so Ollama does not reload the model
QUIZ_OPTIONS = {"temperature": 0.5, "num_ctx": 3072, "num_predict": 260}

MIN_CHUNK_CHARS = 250      # skip tiny fragments and headings
MAX_EXCERPT_CHARS = 900
MAX_QUESTION_CHARS = 240
MAX_OPTION_CHARS = 140

QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "correct_answer": {"type": "string"},
        "wrong_answers": {"type": "array", "items": {"type": "string"}},
        "explanation": {"type": "string"},
    },
    "required": ["question", "correct_answer", "wrong_answers", "explanation"],
}

SYSTEM_PROMPT = """You write multiple-choice quiz questions for students from a short excerpt of a PDF.

Return ONLY a JSON object with exactly these keys:
{"question": "...", "correct_answer": "...", "wrong_answers": ["...", "...", "..."], "explanation": "..."}

Rules:
- Use ONLY facts stated in the excerpt. Never add outside knowledge.
- The question must make sense on its own. Never say "the excerpt", "the text", "the passage" or "the document".
- Exactly 3 wrong answers. They must be plausible but clearly wrong according to the excerpt, and similar in length and style to the correct answer.
- Keep every answer short (under 15 words).
- "explanation": one sentence saying why the correct answer is right.
- Plain text only. No LaTeX, no markdown, no dollar signs."""

DIFFICULTY_RULES = {
    "easy": "Ask about a main fact or definition that is stated directly.",
    "medium": "Ask about a reason, a relationship or a comparison between ideas.",
    "hard": (
        "Ask a question that needs understanding: applying an idea, "
        "or telling apart two similar concepts."
    ),
}

BANNED_PHRASES = re.compile(
    r"\b(the|this|that) (excerpt|passage|text|document|pdf|page)\b"
    r"|\baccording to the\b",
    re.I,
)


def _clean(value):
    return " ".join(str(value).replace("$", "").split())


def _is_usable(text):
    """Keep chunks with real sentences; skip tables of numbers, link lists, etc."""
    if len(text) < MIN_CHUNK_CHARS:
        return False

    letters = sum(1 for ch in text if ch.isalpha())

    if letters / len(text) < 0.6:
        return False

    return text.lower().count("http") < 2


def build_question(data, page, source):
    """Validates the model's JSON and returns a finished question, or None."""
    if not isinstance(data, dict):
        return None

    question = _clean(data.get("question", ""))
    correct = _clean(data.get("correct_answer", ""))
    explanation = _clean(data.get("explanation", ""))
    raw_wrong = data.get("wrong_answers", [])

    if not isinstance(raw_wrong, list):
        return None

    if len(question) < 10 or len(question) > MAX_QUESTION_CHARS or not correct:
        return None

    if BANNED_PHRASES.search(question):
        return None

    wrong = []
    seen = {correct.lower()}

    for item in raw_wrong:
        text = _clean(item)

        if text and text.lower() not in seen:
            seen.add(text.lower())
            wrong.append(text)

    if len(wrong) < 3:
        return None

    options = [correct] + wrong[:3]

    if any(len(option) > MAX_OPTION_CHARS for option in options):
        return None

    random.shuffle(options)

    return {
        "type": "question",
        "question": question,
        "options": options,
        "answer": options.index(correct),
        "explanation": explanation,
        "page": page,
        "source": source,
    }


def _ask_model(excerpt, page, difficulty):
    rule = DIFFICULTY_RULES.get(difficulty, DIFFICULTY_RULES["medium"])

    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n- {rule}"},
        {
            "role": "user",
            "content": f"Excerpt (page {page}):\n{excerpt}\n\nWrite one question.",
        },
    ]

    # Strict schema first, then plain JSON mode
    for output_format in (QUESTION_SCHEMA, "json"):
        try:
            response = ollama.chat(
                model=ANSWER_MODEL,
                messages=messages,
                format=output_format,
                keep_alive=KEEP_ALIVE,
                options=QUIZ_OPTIONS,
            )
            return json.loads(response["message"]["content"])
        except Exception as e:
            print(f"Quiz question attempt failed: {e}")

    return None


def quiz_events(document, count, difficulty):
    """
    Yields dicts: {"type": "question", ...} for each question as soon as it is
    ready, then {"type": "done", "count": n}. On failure: {"type": "error"}.
    """
    rows = _fetch(text_collection, "text", {"source": document})
    usable = [r for r in sorted(rows, key=_sort_key) if _is_usable(r["text"])]

    if not usable:
        yield {
            "type": "error",
            "text": (
                "I couldn't find enough readable text in this PDF to write "
                "questions. If it is a scanned PDF, it needs OCR first."
            ),
        }
        return

    # One target per question, spread over the whole document
    targets = _even_sample(usable, count)
    target_ids = {r["id"] for r in targets}

    # Backup chunks (also spread out) in case a question fails validation
    spare = [r for r in usable if r["id"] not in target_ids]
    spare = _even_sample(spare, min(len(spare), count)) if spare else []

    seen_questions = set()

    def attempt(chunk):
        """Asks the model about one chunk; returns a valid new question or None."""
        data = _ask_model(
            chunk["text"][:MAX_EXCERPT_CHARS], chunk["page"], difficulty
        )
        question = build_question(data, chunk["page"], document)

        if not question:
            return None

        key = question["question"].lower()

        if key in seen_questions:
            return None

        seen_questions.add(key)
        return question

    produced = 0

    for target in targets:
        candidates = [target]
        borrowed = 0
        question = None

        while candidates and question is None:
            question = attempt(candidates.pop(0))

            # Backup chunks are only used when a question fails (max 2 per slot)
            if question is None and borrowed < 2 and spare:
                candidates.append(spare.pop(0))
                borrowed += 1

        if question:
            question["index"] = produced
            produced += 1
            yield question

    # If some slots failed, top up from the backups that are left
    while produced < count and spare:
        question = attempt(spare.pop(0))

        if question:
            question["index"] = produced
            produced += 1
            yield question

    yield {"type": "done", "count": produced}