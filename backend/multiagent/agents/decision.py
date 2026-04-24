import json
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

def decision_node(state):

    prompt = f"""
Dado estos tickets:
{state['analysis']}

Asigna prioridad (Alta, Media, Baja) a cada ticket.

Responde SOLO en JSON válido sin markdown.
Formato:
[
  {{"id": "...", "prioridad": "..."}}
]
"""

    response = llm.invoke(prompt)

    try:
        clean = response.content.replace("```json", "").replace("```", "")
        state["prioritized"] = json.loads(clean)
    except:
        state["prioritized"] = response.content

    print("⚖️ PRIORITIZED:", state["prioritized"])

    return state