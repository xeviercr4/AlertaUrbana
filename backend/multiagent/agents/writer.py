from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

def writer_node(state):

    prompt = f"""
Genera un reporte ejecutivo claro para la municipalidad.

Incluye:
- Top 5 incidentes más críticos
- Resumen general
- Recomendaciones

Datos:
{state['prioritized']}
"""

    response = llm.invoke(prompt)

    state["final"] = response.content

    print("✍️ REPORT:", state["final"])

    return state