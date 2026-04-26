from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def writer_node(state):

    prioritized = state.get("prioritized", [])
    rules = state.get("rules", "")

    incidents_text = "\n".join([
        f"{i+1}. {t.get('id')} - {t.get('descripcion')} (Prioridad: {t.get('prioridad')})"
        for i, t in enumerate(prioritized)
    ])

    prompt = f"""Tu trabajo es crear un plan estratégico para resolver los incidentes.
Para el plan estratégico debes tomar en consideración:
1)	La priorización de los ticketes.
2)	Solucionar varios problemas de un mismo lugar o cercano para optimizar traslados.
3)	Herramientas necesarias a transportar para enviar. En algunas situaciones puede convenir resolver un tipo de ticket porque ya tienes a los expertos en el campo.
Como resultado final crear un plan de acción estrategico dividido por días y equipo necesario para resolver los incidentes."
"""
    response = client.chat.completions.create(
        model="gpt-5.4",
        messages=[
            {"role": "system", "content": "Eres un sistema de planificación municipal."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_completion_tokens=700
    )

    result = response.choices[0].message.content.strip()

    state["final"] = result

    print("✍️ WRITER:", result)

    return state