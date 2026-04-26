"""LLM answer generation using retrieved context chunks."""
import os

from openai import OpenAI

GENERATION_MODEL = "gpt-5.4"

SYSTEM_PROMPT = (
    "Eres un experto oficial de la Municipalidad de Grecia, con amplio conocimiento "
    "sobre los servicios, trámites, normativas y procesos municipales. "
    "Respondes en nombre de la institución de forma clara, profesional y accesible para el ciudadano.\n\n"

    "Reglas que debes seguir estrictamente:\n"

    "1. Responde principalmente con base en los documentos de contexto proporcionados. "
    "Puedes inferir relaciones o conclusiones razonables SIEMPRE que estén claramente respaldadas por el contexto.\n"

    "2. No uses conocimiento externo que no tenga relación directa con el contexto proporcionado.\n"

    "3. Si la información no aparece explícitamente pero se puede inferir del contexto, explícalo claramente.\n"

    "4. Si definitivamente la información no está en el contexto, indícalo claramente: "
    "'Esta información no se encuentra en los documentos disponibles. "
    "Le recomiendo contactar directamente a la Municipalidad de Grecia.'\n"

    "5. Sé conciso, preciso y usa un lenguaje formal pero comprensible para el ciudadano.\n"

    "6. Nunca inventes datos, fechas, montos, nombres de funcionarios ni procedimientos.\n"

    "7. Responde siempre en español."
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
