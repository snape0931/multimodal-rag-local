import json
import re

import ollama
import pymupdf

ANSWER_MODEL = "llama3.2:3b"   # if still too slow, use "llama3.2:1b" (ollama pull llama3.2:1b)
KEEP_ALIVE = "30m"

NOT_FOUND_MESSAGE = "😕 Sorry, I couldn't find that in your uploaded documents."
NOT_FOUND_TOKEN = "NOT_FOUND"

OLLAMA_OPTIONS = {
    "temperature": 0.2,
    "num_ctx": 3072,
    "num_predict": 250,   # hard cap on answer length = big speed win
}

# How much earlier conversation is shown to the model (keeps prompts short and fast)
MAX_HISTORY_MESSAGES = 4
MAX_HISTORY_CHARS = 400

SYSTEM_PROMPT = """You are OmniDoc AI, a friendly and helpful assistant that answers
questions about the user's PDF documents.

You are given context excerpts from the PDFs. Each one is labelled with its type
(text, table or image), the PDF name and the page number.

Tone:
- Warm, clear and conversational, like a helpful teammate. Plain language.
- Start with the answer itself. No filler like "Based on the context provided".
- One emoji now and then is fine, but don't overdo it.
- Keep answers short: about 120 words at most, unless the user asks for detail.

Rules:
1. Answer ONLY from the excerpts. Never use outside knowledge to fill gaps.
2. If the excerpts do not contain the answer, reply with exactly the single
   word NOT_FOUND and nothing else: no explanation, no apology, no sources.
3. Mention where information came from in brackets, like (deeplearning.pdf, p. 5).
   Use only PDF names and page numbers that appear in the excerpts.
4. Copy numbers, units, names and table values exactly. Never round or guess.
5. Image excerpts are automatic descriptions and may be inaccurate. Prefer
   text and table excerpts, and say so when you rely on an image.
6. If excerpts disagree, point that out and mention both sources.
7. Use short bullet points for lists or steps.
8. Write formulas in plain text, like f_s = 2B or E = m × c^2.
   Never use LaTeX, backslashes or dollar signs.
9. Earlier messages in the conversation are only there so you can understand
   words like "this" or "it". Facts must still come only from the excerpts.
"""


# ---------- friendly small talk (no document search needed) ----------

GREETINGS = {
    "hi", "hii", "hiii", "hello", "hey", "heyy", "hola", "namaste",
    "good morning", "good afternoon", "good evening", "yo", "sup",
}
THANKS = {"thanks", "thank you", "thx", "ty", "thank u", "thanks a lot"}
HELP = {
    "help", "what can you do", "who are you", "what are you",
    "how do you work", "how does this work",
}
BYE = {"bye", "goodbye", "see you", "see ya", "good night"}


def _normalize(text):
    return re.sub(r"[^a-z\s]", "", text.lower()).strip()


def small_talk_reply(query):
    """Return a friendly reply for greetings, thanks, etc., else None."""
    q = _normalize(query)

    if q in GREETINGS:
        return (
            "Hi there! 👋 I'm OmniDoc AI. Upload a PDF and ask me anything "
            "about its text, tables or images."
        )

    if q in THANKS:
        return "You're welcome! 😊 Let me know if you'd like to ask anything else."

    if q in HELP:
        return (
            "I'm OmniDoc AI 🤖 I read your uploaded PDFs, including their text, "
            "tables and images, and answer your questions with the page where I "
            "found the information. Try asking something like "
            "\"Summarize page 3\" or \"What does the table on page 5 show?\"."
        )

    if q in BYE:
        return "Goodbye! 👋 Come back anytime you have more questions."

    return None


# ---------- conversation history (for follow-up questions) ----------

FOLLOW_UP_WORDS = {
    "this", "that", "it", "its", "these", "those", "they", "them", "their",
    "he", "she", "his", "her", "above", "same", "previous", "also", "more",
}


def clean_history(history):
    """Keep only the last few valid turns, shortened."""
    cleaned = []

    for item in (history or [])[-MAX_HISTORY_MESSAGES:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()

        if role not in ("user", "assistant") or not content:
            continue

        if content == NOT_FOUND_MESSAGE:
            continue

        cleaned.append({"role": role, "content": content[:MAX_HISTORY_CHARS]})

    return cleaned


def build_search_query(query, history):
    """
    For follow-ups like "give formula for this rate", add the previous
    question so the search knows what "this" refers to.
    """
    previous = [
        turn["content"]
        for turn in clean_history(history)
        if turn["role"] == "user"
    ]

    if not previous:
        return query

    words = re.findall(r"[a-z']+", query.lower())
    is_follow_up = len(words) <= 3 or any(w in FOLLOW_UP_WORDS for w in words)

    if is_follow_up:
        return f"{previous[-1]} {query}"

    return query


# ---------- helpers ----------

def build_messages(query, context, history=None):
    user_prompt = (
        f"Context excerpts:\n\n{context}\n\n"
        f"Question: {query}\n\n"
        "Answer using only the excerpts above. "
        "If they do not contain the answer, reply NOT_FOUND."
    )

    return (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + clean_history(history)
        + [{"role": "user", "content": user_prompt}]
    )


def _starts_with_not_found(text):
    cleaned = text.upper().replace(" ", "_").lstrip("_.!*`\"'\n")
    return cleaned.startswith(NOT_FOUND_TOKEN)


def is_not_found(answer):
    if not answer or not answer.strip():
        return True

    if _starts_with_not_found(answer):
        return True

    # The model sometimes wraps the token in a short sentence
    cleaned = answer.upper().replace(" ", "_")
    return NOT_FOUND_TOKEN in cleaned and len(answer) < 80


def warm_up():
    """Load the answer model into memory so the first question isn't slow."""
    try:
        ollama.generate(model=ANSWER_MODEL, prompt="", keep_alive=KEEP_ALIVE)
        print("Answer model loaded and ready.")
    except Exception as e:
        print(f"Warm-up skipped: {e}")


# ---------- answer generation ----------

def generate_answer(query, context, history=None):
    """Non-streaming version (used by /ask, handy for testing in /docs)."""
    response = ollama.chat(
        model=ANSWER_MODEL,
        messages=build_messages(query, context, history),
        keep_alive=KEEP_ALIVE,
        options=OLLAMA_OPTIONS,
    )

    answer = response["message"]["content"].strip()

    if is_not_found(answer):
        return NOT_FOUND_MESSAGE

    return answer


def stream_answer(query, context, history=None):
    """
    Streaming version. Yields ("token", text) pieces, or a single
    ("not_found", "") if the model says the answer isn't in the documents.
    The first few characters are held back so NOT_FOUND is never shown.
    """
    stream = ollama.chat(
        model=ANSWER_MODEL,
        messages=build_messages(query, context, history),
        stream=True,
        keep_alive=KEEP_ALIVE,
        options=OLLAMA_OPTIONS,
    )

    buffer = ""
    decided = False

    for part in stream:
        token = part["message"]["content"]

        if not token:
            continue

        if decided:
            yield ("token", token)
            continue

        buffer += token

        if len(buffer) >= 12:
            if _starts_with_not_found(buffer):
                yield ("not_found", "")
                return

            decided = True
            yield ("token", buffer)

    # Very short answer: the stream ended before the buffer filled up
    if not decided:
        if is_not_found(buffer):
            yield ("not_found", "")
        else:
            yield ("token", buffer)


# ---------- document summary + suggested questions ----------

SUMMARY_PAGES_SAMPLED = 8        # pages sampled across the document
SUMMARY_CHARS_PER_PAGE = 600
SUMMARY_MAX_CHARS = 3500

SUMMARY_PROMPT = """You are helping a user get started with a PDF document.
You will be given short excerpts sampled from across the document.

Return ONLY a JSON object with exactly these keys:
{"summary": "...", "questions": ["...", "...", "..."]}

Rules:
- "summary": 2-3 plain sentences (at most 60 words) saying what the document is about.
- "questions": 3 short, specific questions a reader could ask about this document
  (each under 12 words), answerable from the excerpts.
- Use only the excerpts. Plain text only: no LaTeX, no markdown, no emojis.
"""

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "questions"],
}


def sample_pdf_text(pdf_path):
    """Read a little text from pages spread evenly across the PDF."""
    pdf = pymupdf.open(str(pdf_path))

    try:
        total = len(pdf)

        if total == 0:
            return ""

        count = min(SUMMARY_PAGES_SAMPLED, total)

        if count == 1:
            indexes = [0]
        else:
            indexes = sorted({
                round(i * (total - 1) / (count - 1)) for i in range(count)
            })

        parts = []
        used = 0

        for index in indexes:
            text = " ".join(pdf.load_page(index).get_text("text").split())

            if not text:
                continue

            piece = text[:SUMMARY_CHARS_PER_PAGE]
            parts.append(f"[Page {index + 1}] {piece}")
            used += len(piece)

            if used >= SUMMARY_MAX_CHARS:
                break

        return "\n".join(parts)

    finally:
        pdf.close()


def generate_summary(sample_text):
    """Return {"summary": str, "questions": [str, ...]} or None if it fails."""

    if not sample_text or not sample_text.strip():
        return None

    messages = [
        {"role": "system", "content": SUMMARY_PROMPT},
        {"role": "user", "content": f"Excerpts:\n\n{sample_text}"},
    ]

    content = None

    # Try a strict JSON schema first, then plain JSON mode
    for output_format in (SUMMARY_SCHEMA, "json"):
        try:
            response = ollama.chat(
                model=ANSWER_MODEL,
                messages=messages,
                format=output_format,
                keep_alive=KEEP_ALIVE,
                options={
                    "temperature": 0.3,
                    "num_ctx": 3072,
                    "num_predict": 300,
                },
            )
            content = response["message"]["content"]
            break
        except Exception as e:
            print(f"Summary attempt failed: {e}")

    if not content:
        return None

    try:
        data = json.loads(content)
    except Exception:
        return None

    summary = " ".join(str(data.get("summary", "")).replace("$", "").split())

    questions = []
    raw_questions = data.get("questions", [])

    if isinstance(raw_questions, list):
        for item in raw_questions:
            question = " ".join(str(item).replace("$", "").split())

            if question and question not in questions:
                questions.append(question)

    if not summary:
        return None

    return {"summary": summary, "questions": questions[:4]}