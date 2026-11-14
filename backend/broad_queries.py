"""
Questions that normal vector search cannot answer well:

  * "Summarize this document" / "What is this PDF about?"
  * "What are the main concepts?"
  * "Explain a diagram" / "Explain figure 3"
  * "Summarize page 3" / "What does the table on page 5 show?"

Instead of searching, these build their context directly:
  - summary / concepts -> chunks sampled evenly across the whole document
  - diagram            -> described images (+ the text on the same page)
  - page questions     -> every chunk stored for the requested page(s)

Put this file in backend/ and call plan_special_query() from main.py.
"""

import re

from backend.retrieval import (
    model,
    text_collection,
    table_collection,
    image_collection,
)

# Must match num_ctx in generation.py, otherwise Ollama reloads the model
OPTIONS = {"temperature": 0.2, "num_ctx": 3072, "num_predict": 350}

MAX_CONTEXT_CHARS = 5000   # total excerpt text sent to the model
CHUNK_CHARS = 700          # max characters taken from one chunk
MAX_PAGES = 5              # "pages 3-40" is capped to the first 5
SUMMARY_CHUNKS = 8
CONCEPT_CHUNKS = 10
DIAGRAM_COUNT = 3


# ---------------------------------------------------------------------
# 1. Detecting the question type
# ---------------------------------------------------------------------

PAGE_RE = re.compile(
    r"\bpages?\s*(\d{1,4})(?:\s*(-|–|to|and)\s*(\d{1,4}))?", re.I
)

SUMMARY_WORD_RE = re.compile(
    r"\b(summar\w*|summeri\w*|overview|tl;?dr|gist|recap)\b", re.I
)
ABOUT_RE = re.compile(
    r"what(?:'s| is) (?:this|the|my) (?:document|pdf|file|paper|book|report|doc|chapter)\b.*\babout"
    r"|what(?:'s| is) it about"
    r"|what does (?:this|the) (?:document|pdf|file|paper|book|report) "
    r"(?:say|cover|contain|discuss)",
    re.I,
)
DOC_WORD_RE = re.compile(
    r"\b(document|pdf|file|paper|book|report|doc|chapter|whole|entire|overall)\b",
    re.I,
)

CONCEPT_RE = re.compile(
    r"\b(?:main|key|important|core|major|central|top)\s+"
    r"(?:concepts?|ideas?|topics?|points?|themes?|takeaways?|terms?|definitions?)\b"
    r"|\btakeaways?\b"
    r"|\b(?:concepts|topics)\s+(?:covered|discussed|explained)\b",
    re.I,
)

VISUAL_STRONG_RE = re.compile(
    r"\b(?:diagrams?|figures?(?!\s+out)|fig\.?\s*\d+|charts?|illustrations?"
    r"|flow\s?charts?|schematics?|infographics?)\b",
    re.I,
)
VISUAL_WEAK_RE = re.compile(
    r"\b(?:the|this|that|these|those)\s+(?:image|picture|plot|graph|visual)s?\b",
    re.I,
)
EXPLAIN_RE = re.compile(
    r"\b(?:explain|describe|interpret|analy[sz]e|walk me through|show me"
    r"|tell me about|understand"
    r"|what (?:does|do) .{0,40}?(?:show|depict|represent|illustrate|mean))\b",
    re.I,
)
FIGURE_NUMBER_RE = re.compile(r"\b(?:figure|fig\.?)\s*\d+", re.I)


def find_pages(query):
    """'page 3' -> [3];  'pages 3-5' -> [3, 4, 5];  'pages 3 and 8' -> [3, 8]"""
    match = PAGE_RE.search(query)

    if not match:
        return []

    first = int(match.group(1))

    if match.group(3):
        second = int(match.group(3))

        if match.group(2).lower() == "and":
            pages = [first, second]
        else:
            low, high = sorted((first, second))
            pages = list(range(low, min(high, low + MAX_PAGES - 1) + 1))
    else:
        pages = [first]

    return [p for p in pages if p > 0][:MAX_PAGES]


def _word_count(text):
    return len(re.findall(r"[A-Za-z']+", text))


def is_summary_request(query):
    if ABOUT_RE.search(query):
        return True

    if SUMMARY_WORD_RE.search(query):
        # "summary of the CNN section" is a normal question,
        # "summarize this document" / "give me a summary" is not
        return bool(DOC_WORD_RE.search(query)) or _word_count(query) <= 4

    return False


def is_concepts_request(query):
    if CONCEPT_RE.search(query):
        return bool(DOC_WORD_RE.search(query)) or _word_count(query) <= 5

    return False


def is_diagram_request(query):
    if FIGURE_NUMBER_RE.search(query):
        return True

    has_visual = VISUAL_STRONG_RE.search(query) or VISUAL_WEAK_RE.search(query)

    return bool(has_visual and EXPLAIN_RE.search(query))


# ---------------------------------------------------------------------
# 2. Helpers for reading the vector store
# ---------------------------------------------------------------------

TYPE_ORDER = {"text": 0, "table": 1, "image": 2}


def _trailing_number(identifier):
    match = re.search(r"(\d+)$", identifier or "")
    return int(match.group(1)) if match else 0


def _sort_key(row):
    return (
        row["source"],
        row["page"],
        TYPE_ORDER.get(row["type"], 3),
        _trailing_number(row["id"]),
    )


def _where(document=None, pages=None):
    conditions = []

    if document:
        conditions.append({"source": document})

    if pages:
        conditions.append(
            {"page": pages[0]} if len(pages) == 1 else {"page": {"$in": pages}}
        )

    if not conditions:
        return None

    return conditions[0] if len(conditions) == 1 else {"$and": conditions}


def _fetch(collection, row_type, where):
    """All stored chunks of one collection that match 'where'."""
    if collection.count() == 0:
        return []

    try:
        result = collection.get(where=where, include=["documents", "metadatas"])
    except Exception as e:
        print(f"Could not read {row_type} records: {e}")
        return []

    rows = []

    for identifier, doc, meta in zip(
        result["ids"], result["documents"], result["metadatas"]
    ):
        if not doc or not meta:
            continue

        page = meta.get("page")

        rows.append({
            "id": identifier,
            "type": row_type,
            "text": doc,
            "source": meta.get("source", "Unknown"),
            "page": page if isinstance(page, int) else 0,
            "image": meta.get("image"),
        })

    return rows


def _even_sample(items, count):
    """Pick 'count' items spread evenly, always keeping the first and last."""
    if len(items) <= count:
        return items

    if count <= 1:
        return items[:1]

    step = (len(items) - 1) / (count - 1)
    indexes = sorted({round(i * step) for i in range(count)})

    return [items[i] for i in indexes]


def _build_context(rows):
    """Join chunks into one prompt block without going over the size budget."""
    parts = []
    used_rows = []
    used = 0

    for row in rows:
        text = row["text"]

        if len(text) > CHUNK_CHARS:
            text = text[:CHUNK_CHARS].rstrip() + "..."

        part = f"[{row['source']}, p. {row['page']}, {row['type']}]\n{text}"

        if parts and used + len(part) > MAX_CONTEXT_CHARS:
            break

        parts.append(part)
        used_rows.append(row)
        used += len(part)

    return "\n\n".join(parts), used_rows


def _sources(rows):
    result = []

    for row in rows:
        item = {
            "type": row["type"],
            "source": row["source"],
            "page": row["page"],
        }

        if row.get("image"):
            item["image"] = row["image"]

        result.append(item)

    return result


def _plan(system_prompt, context, query, rows, label=""):
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"{label}Excerpts:\n\n{context}\n\n"
                    f"User request: {query}"
                ),
            },
        ],
        "options": OPTIONS,
        "sources": _sources(rows),
    }


# ---------------------------------------------------------------------
# 3. Which document?
# ---------------------------------------------------------------------

NO_DOCS_MESSAGE = (
    "📂 There are no documents indexed yet. Upload a PDF first and "
    "then ask me again."
)
PICK_DOC_MESSAGE = (
    "📚 You have {n} documents. Please choose one in the SOURCE dropdown "
    "above the chat, then ask again, so I know which one you mean."
)


def list_sources():
    if text_collection.count() == 0:
        return []

    result = text_collection.get(include=["metadatas"])

    return sorted({
        meta.get("source")
        for meta in result["metadatas"]
        if meta and meta.get("source")
    })


def resolve_document(document):
    """Returns (document_name, None) or (None, message_for_the_user)."""
    if document:
        return document, None

    sources = list_sources()

    if not sources:
        return None, NO_DOCS_MESSAGE

    if len(sources) == 1:
        return sources[0], None

    return None, PICK_DOC_MESSAGE.format(n=len(sources))


# ---------------------------------------------------------------------
# 4. Prompts
# ---------------------------------------------------------------------

SUMMARY_SYSTEM = """You are OmniDoc AI, a friendly assistant that explains PDF documents.
You receive excerpts sampled from across one PDF, in page order.

Write a summary of the whole document:
- First, one sentence saying what the document is about.
- Then 3 to 5 short bullet points covering the main topics in the order they appear.
- Use only the excerpts. Never add outside knowledge.
- Do not mention that the excerpts were sampled. Just summarize what you see.
- Mention pages in brackets where helpful, like (p. 5).
- Plain text only. No LaTeX, no dollar signs. At most 150 words."""

CONCEPTS_SYSTEM = """You are OmniDoc AI, a friendly assistant that explains PDF documents.
You receive excerpts sampled from across one PDF, in page order.

List the most important concepts of the document:
- 4 to 7 bullet points. Each one: the concept name, then a one-sentence plain-language explanation.
- Add the page in brackets, like (p. 5).
- Use only the excerpts. Never add outside knowledge.
- Do not mention that the excerpts were sampled.
- Plain text only. No LaTeX, no dollar signs. At most 180 words."""

DIAGRAM_SYSTEM = """You are OmniDoc AI, a friendly assistant that explains figures from PDFs.
For each figure you get an automatic description (it can be inaccurate) and
the text printed on the same page.

Explain each figure in plain language:
- What kind of figure it is and what it shows.
- Its main parts and how they relate.
- Use the page text to confirm or correct the description.
- If the page text does not confirm the description, say the description is approximate.
- Mention the page in brackets, like (p. 5).
- Use only the information given. Plain text only. At most 150 words per figure."""

PAGE_SYSTEM = """You are OmniDoc AI, a friendly assistant that answers questions about PDF pages.
You receive everything stored for the requested page(s): text, table rows and image descriptions.

- Do exactly what the user asks (summarize, explain, list, answer) using ONLY these excerpts.
- If the page does not answer the question, briefly say what the page does contain.
- Copy numbers and names exactly. Image descriptions are automatic and may be inaccurate.
- Mention the page in brackets, like (p. 3).
- Plain text only. No LaTeX, no dollar signs. At most 150 words."""


# ---------------------------------------------------------------------
# 5. The four plans
# ---------------------------------------------------------------------

def plan_overview(query, document, kind):
    """Summary or key concepts, built from chunks spread across the document."""
    doc, problem = resolve_document(document)

    if problem:
        return {"reply": problem}

    rows = _fetch(text_collection, "text", _where(doc))

    if not rows:
        return {
            "reply": (
                f"😕 I couldn't find readable text in {doc}. If it is a scanned "
                "PDF, it needs OCR before I can read it."
            )
        }

    rows.sort(key=_sort_key)

    count = SUMMARY_CHUNKS if kind == "summary" else CONCEPT_CHUNKS
    context, used = _build_context(_even_sample(rows, count))
    system = SUMMARY_SYSTEM if kind == "summary" else CONCEPTS_SYSTEM

    return _plan(system, context, query, used, label=f"Document: {doc}\n\n")


def plan_diagram(query, document, pages):
    """Explain figures using their stored descriptions plus the page text."""
    count = image_collection.count()

    if count == 0:
        return {
            "reply": (
                "🖼️ I don't have any described figures yet. They may still be "
                "processing (check the upload status), or this PDF's diagrams "
                "may not be stored as images. Try asking about the text next "
                "to the figure instead."
            )
        }

    try:
        result = image_collection.query(
            query_embeddings=[model.encode(query).tolist()],
            n_results=min(DIAGRAM_COUNT, count),
            where=_where(document, pages),
            include=["documents", "metadatas"],
        )
        docs, metas = result["documents"][0], result["metadatas"][0]
    except Exception as e:
        print(f"Image search failed: {e}")
        docs, metas = [], []

    if not docs:
        where_text = f" on page {', '.join(map(str, pages))}" if pages else ""
        return {
            "reply": f"😕 I couldn't find a described figure{where_text}."
        }

    blocks = []
    rows = []

    for number, (doc, meta) in enumerate(zip(docs, metas), start=1):
        source = meta.get("source", "Unknown")
        page = meta.get("page", 0)

        block = (
            f"Figure {number} ({source}, p. {page}), automatic description:\n"
            f"{doc}"
        )

        page_rows = sorted(
            _fetch(text_collection, "text", _where(source, [page])),
            key=_sort_key,
        )[:2]

        if page_rows:
            page_text = " ".join(r["text"] for r in page_rows)[:700]
            block += f"\nText on the same page:\n{page_text}"

        blocks.append(block)
        rows.append({
            "type": "image",
            "source": source,
            "page": page,
            "image": meta.get("image"),
        })

    return _plan(DIAGRAM_SYSTEM, "\n\n".join(blocks), query, rows)


def plan_pages(query, document, pages):
    """Questions about specific pages: use everything stored for those pages."""
    doc, problem = resolve_document(document)

    if problem:
        return {"reply": problem}

    where = _where(doc, pages)
    rows = (
        _fetch(text_collection, "text", where)
        + _fetch(table_collection, "table", where)
        + _fetch(image_collection, "image", where)
    )

    if not rows:
        label = ", ".join(map(str, pages))
        return {
            "reply": (
                f"😕 I couldn't find any content on page {label} of {doc}. "
                "The page may be blank, scanned, or past the last page."
            )
        }

    rows.sort(key=_sort_key)
    context, used = _build_context(rows)

    return _plan(PAGE_SYSTEM, context, query, used, label=f"Document: {doc}\n\n")


# ---------------------------------------------------------------------
# 6. Entry point used by main.py
# ---------------------------------------------------------------------

def plan_special_query(query, document=None):
    """
    Returns None for normal questions (use the usual search + answer path), or:
      {"reply": "text"}                                  -> show this text directly
      {"messages": [...], "options": {...}, "sources": [...]}  -> send to the LLM
    """
    query = query.strip()
    pages = find_pages(query)

    if pages:
        if is_diagram_request(query):
            return plan_diagram(query, document, pages)

        return plan_pages(query, document, pages)

    if is_diagram_request(query):
        return plan_diagram(query, document, None)

    if is_summary_request(query):
        return plan_overview(query, document, "summary")

    if is_concepts_request(query):
        return plan_overview(query, document, "concepts")

    return None