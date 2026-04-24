from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

def verifier_node(state):

    prompt = f"""
Verifica que esta respuesta sea clara, coherente y completa:

{state['final']}
"""

    response = llm.invoke(prompt)

    state["final"] = response.content

    print("✅ VERIFIED:", state["final"])

    return state