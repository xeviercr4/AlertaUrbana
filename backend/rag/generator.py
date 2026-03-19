"""LLM answer generation using retrieved context chunks."""
import os

from openai import OpenAI

GENERATION_MODEL = "gpt-3.5-turbo"

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions based solely on the "
    "provided context documents. If the answer cannot be found in the context, "
    "say so clearly. Be concise and accurate."
)


def generate_answer(question: str, context_chunks: list[dict]) -> str:
    """
    Generate an answer for `question` using the retrieved `context_chunks`.

    Each chunk dict must have a 'text' key.
    Returns the generated answer string.
    """
    if not context_chunks:
        return (
            "I could not find any relevant documents to answer your question. "
            "Please upload documents first."
        )

    context_parts = []
    for i, chunk in enumerate(context_chunks, start=1):
        source = chunk.get("filename", "unknown")
        context_parts.append(f"[Source {i} – {source}]\n{chunk['text']}")
    context_text = "\n\n".join(context_parts)

    user_message = (
        f"Context:\n{context_text}\n\n"
        f"Question: {question}\n\n"
        "Answer based on the context above:"
    )

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=GENERATION_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()
