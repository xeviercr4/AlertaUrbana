import logging
import os
from openai import OpenAI

logger = logging.getLogger("alertaurbana.multiagent.writer")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def writer_node(state):

    prioritized = state.get("prioritized", [])
    rules = state.get("rules", "")
    plan = state.get("plan", "")
    feedback = state.get("verification", {}).get("feedback", "")

    if isinstance(prioritized, list):
        incidents_text = "\n".join([
            f"{i+1}. {t.get('id')} — {t.get('descripcion','')} "
            f"(Prioridad: {t.get('prioridad')}; Razón: {t.get('razon','')})"
            for i, t in enumerate(prioritized)
        ])
    else:
        incidents_text = str(prioritized)

    revision_block = ""
    if feedback:
        revision_block = (
            f"\n---\nESTE ES UN REINTENTO. El verificador detectó:\n{feedback}\n"
            "Corrige esos puntos en esta versión.\n---\n"
        )

    prompt = f"""Tu trabajo es crear un plan estratégico ejecutivo para la municipalidad
para resolver los incidentes priorizados.

CRITERIOS APLICABLES:
{rules}

PLAN GENERAL:
{plan}

INCIDENTES PRIORIZADOS:
{incidents_text}
{revision_block}
Considera:
1) Atender primero los de prioridad ALTA.
2) Agrupar incidentes cercanos para optimizar traslados.
3) Herramientas y equipo necesarios por tipo de incidente.

Entrega un plan de acción dividido por días con:
- Equipo asignado
- Incidentes a resolver ese día
- Recursos necesarios
- Resumen ejecutivo final con recomendaciones
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un sistema de planificación municipal."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=900
    )

    state["final"] = response.choices[0].message.content.strip()
    logger.info("REPORT generado (%d chars)", len(state["final"]))

    return state
