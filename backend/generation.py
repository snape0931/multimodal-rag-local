
import ollama


def generate_answer(question, context):

    prompt = f"""
You are a helpful multimodal PDF research assistant.

Answer the user's question using only the retrieved context.

Instructions:
1. Do not invent information.
2. Compare information across PDFs when relevant.
3. Mention PDF names and page numbers.
4. If the answer is not present in the context, say so.
5. Give a clear and structured answer.

Retrieved Context:
{context}

Question:
{question}

Answer:
"""

    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response["message"]["content"]
