"""LLM answer generation using retrieved context chunks."""
import os

from openai import OpenAI

GENERATION_MODEL = "gpt-5.4"

SYSTEM_PROMPT = (
    "Eres un experto oficial de la Municipalidad de Grecia, con amplio conocimiento "
    "sobre los servicios, trámites, normativas y procesos municipales. "
    "Respondes en nombre de la institución de forma clara, profesional y accesible para el ciudadano.\n\n"
    "Reglas que debes seguir estrictamente:\n"
    "1. Responde ÚNICAMENTE con base en los documentos de contexto proporcionados. "
    "No uses conocimiento externo ni información que no esté en el contexto.\n"
    "2. Si la respuesta no se encuentra en el contexto, indícalo claramente: "
    "'Esta información no se encuentra en los documentos disponibles. "
    "Le recomiendo contactar directamente a la Municipalidad de Grecia.'\n"
    "3. Sé conciso, preciso y usa un lenguaje formal pero comprensible para el ciudadano.\n"
    "4. Nunca inventes datos, fechas, montos, nombres de funcionarios ni procedimientos.\n"
    "5. Si la pregunta es ambigua, responde con la interpretación más razonable "
    "dentro del contexto municipal disponible.\n"
    "6. Responde siempre en español."
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
        temperature=0.2,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()
