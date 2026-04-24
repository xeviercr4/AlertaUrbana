from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

def planner_node(state):
    prompt = f"""
Divide la siguiente tarea en pasos claros:

{state['task']}
"""
    response = llm.invoke(prompt)

    state["plan"] = response.content
    print("🧠 PLAN:", state["plan"])

    return state