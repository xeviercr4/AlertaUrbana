import logging
from langchain_openai import ChatOpenAI

logger = logging.getLogger("alertaurbana.multiagent.planner")
llm = ChatOpenAI(model="gpt-4o-mini")

def planner_node(state):
    prompt = f"""
Divide la siguiente tarea en pasos claros y numerados.
Cada paso debe ser ejecutable por un agente especializado
(investigador, analista, redactor, verificador).

Tarea:
{state['task']}
"""
    response = llm.invoke(prompt)

    state["plan"] = response.content
    logger.info("PLAN generado (%d chars)", len(state["plan"]))

    return state