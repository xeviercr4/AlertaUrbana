import json
import logging
from langchain_openai import ChatOpenAI

logger = logging.getLogger("alertaurbana.multiagent.verifier")
llm = ChatOpenAI(model="gpt-4o-mini")

MAX_ATTEMPTS = 2


def verifier_node(state):
    state["attempts"] = state.get("attempts", 0) + 1

    prompt = f"""
Eres un verificador de calidad. Revisa este reporte ejecutivo y dictamina si
cumple con los siguientes criterios:

1. Coherencia interna (no se contradice).
2. Cubre todos los incidentes priorizados.
3. Incluye recomendaciones accionables.
4. Está alineado con la normativa entregada.

NORMATIVA DE REFERENCIA:
{state.get('rules', '')}

INCIDENTES PRIORIZADOS:
{state.get('prioritized', [])}

REPORTE A VERIFICAR:
{state.get('final', '')}

Responde SOLO en JSON válido (sin markdown):
{{"status": "OK" | "REVIEW", "feedback": "qué corregir si REVIEW; vacío si OK"}}
"""

    response = llm.invoke(prompt)
    raw = response.content.replace("```json", "").replace("```", "").strip()

    try:
        verdict = json.loads(raw)
        if verdict.get("status") not in ("OK", "REVIEW"):
            verdict = {"status": "OK", "feedback": ""}
    except json.JSONDecodeError:
        logger.warning("verifier: respuesta no parseable, asumo OK para evitar loop")
        verdict = {"status": "OK", "feedback": ""}

    state["verification"] = verdict
    logger.info(
        "VERIFICATION attempt=%d status=%s",
        state["attempts"], verdict.get("status")
    )

    return state


def verifier_router(state):
    if state.get("attempts", 0) >= MAX_ATTEMPTS:
        return "end"
    if state.get("verification", {}).get("status") == "OK":
        return "end"
    return "retry"
