
import ollama


def generate_answer(question, context):

    prompt = f"""
You are an accurate multimodal document research assistant.

Your task is to answer the user's question using ONLY the retrieved context.

STRICT RULES:

1. Use only facts explicitly available in the retrieved context.
2. Never invent facts, examples, analogies, table contents or diagram descriptions.
3. Do not assume information that is not explicitly provided.
4. If the retrieved context does not contain enough information, clearly state:
   "The available documents do not contain sufficient information to answer this."
5. For every important claim, mention the source PDF and page number.
6. Distinguish between information from text, tables and image descriptions.
7. When comparing multiple PDFs, identify which document supports each point.
8. Never claim to have seen a diagram or image unless its description is present in the context.
9. Avoid repeating the same information.
10. Keep the answer concise, relevant and well structured.

RESPONSE FORMAT:

- Direct Answer
- Key Findings
- Relevant Tables / Diagrams (only if present in context)
- Sources (PDF name and page number)

If a section has no relevant information, omit it.

RETRIEVED CONTEXT:
{context}

USER QUESTION:
{question}

GROUNDED ANSWER:
"""

    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={
            "temperature": 0.1
        }
    )

    return response["message"]["content"]
