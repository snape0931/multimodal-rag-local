
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.retrieval import retrieve_context
from backend.generation import generate_answer


app = FastAPI(
    title="Multimodal RAG API",
    description="Local PDF question-answering system",
    version="2.0"
)


class QuestionRequest(BaseModel):
    question: str


@app.get("/")
def home():
    return {"message": "Multimodal RAG API is running!"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/ask")
def ask_question(request: QuestionRequest):

    query = request.question.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    context, sources = retrieve_context(query)

    if not context:
        raise HTTPException(
            status_code=404,
            detail="No relevant information found."
        )

    try:
        answer = generate_answer(query, context)

        return {
            "question": query,
            "answer": answer,
            "sources": sources
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Answer generation failed: {str(e)}"
        )
