import json
import logging
from langchain_openai import ChatOpenAI

logger = logging.getLogger("alertaurbana.multiagent.decision")
llm = ChatOpenAI(model="gpt-4o-mini")


def decision_node(state):

    prompt = f"""
Eres el agente de decisión final. Asigna la prioridad definitiva a cada ticket
combinando el análisis del analista con la normativa del researcher.

PLAN A SEGUIR:
{state.get('plan', '')}

NORMATIVA / REGLAS APLICABLES:
{state.get('rules', '')}

ANÁLISIS DETALLADO:
{state.get('analysis', [])}

Reglas de decisión:
- Si el ticket implica riesgo a la vida, servicios esenciales o peligro: ALTA
- Si la normativa lo contempla como prioritario: ALTA
- Si afecta infraestructura sin riesgo inmediato: MEDIA
- Si es estético o no urgente: BAJA

Responde SOLO en JSON válido sin markdown.
Formato exacto:
[
  {{"id": "...", "prioridad": "ALTA|MEDIA|BAJA", "razon": "..."}}
]
"""

    response = llm.invoke(prompt)

    try:
        clean = response.content.replace("```json", "").replace("```", "").strip()
        state["prioritized"] = json.loads(clean)
    except json.JSONDecodeError:
        logger.warning("decision: respuesta no parseable como JSON, devuelvo texto crudo")
        state["prioritized"] = response.content

    n = len(state["prioritized"]) if isinstance(state["prioritized"], list) else 0
    logger.info("PRIORITIZED: %d tickets", n)

    return state
