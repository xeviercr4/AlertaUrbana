"""LLM answer generation using retrieved context chunks."""
import os

from openai import OpenAI

GENERATION_MODEL = "gpt-5.4"

SYSTEM_PROMPT = (
    "Eres un experto de la Municipalidad de Grecia en normativa municipal.\n\n"

    "Tu función es analizar información del contexto y resumirla de forma clara para la toma de decisiones.\n\n"

    "Reglas obligatorias:\n"

    "1. Responde SOLO con base en el contexto proporcionado.\n"

    "2. Resume la información en formato de lista o puntos clave.\n"

    "3. NO generes explicaciones largas ni textos extensos.\n"
)


def generate_answer(question: str, context_chunks: list[dict]) -> str:
    """
    Generate an answer for `question` using the retrieved `context_chunks`.

    Each chunk dict must have a 'text' key.
    Returns the generated answer string.
    """
    if not context_chunks:
        return (
            "No se encontraron documentos relevantes para responder su consulta. "
            "Por favor, asegúrese de que los documentos estén cargados en el sistema."
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
        temperature=0.1,
        max_completion_tokens=1024,
    )
    return response.choices[0].message.content.strip()
