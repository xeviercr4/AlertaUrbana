from pathlib import Path
import requests

from rag.vector_store import VectorStore
from rag.generator import generate_answer

# 🔥 Inicializar vector store (se mantiene, pero no lo usamos directamente)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "rag_data"

vector_store = VectorStore(DATA_DIR)


def researcher_node(state):

    task = state.get("task", "").strip().lower()

    if not task:
        state["rules"] = "No se proporcionó una tarea válida."
        return state

    # 🧠 DETECCIÓN DE DOMINIO
    if "basura" in task or "residuos" in task or "desechos" in task:
        context = """
        normativa de manejo de residuos sólidos, recolección de basura,
        sanciones por mala disposición de residuos, horarios de recolección,
        obligaciones del ciudadano, multas por contaminación.
        """
    else:
        context = """
        normativa del servicio de agua potable, sanciones, multas,
        suspensión del servicio, reconexión, obligaciones del abonado.
        """

    # 🔥 QUERY FINAL
    query = f"""
    {context}
    Consulta del usuario: {task}
    """

    try:
        import requests

        response = requests.post(
            "http://127.0.0.1:8000/rag/query",
            json={"question": query}
        )

        if response.status_code != 200:
            state["rules"] = "Error consultando el sistema RAG."
            return state

        data = response.json()

        state["rules"] = data.get("answer", "Sin respuesta del RAG")

        return state

    except Exception as e:
        print("❌ ERROR:", e)
        state["rules"] = "Error conectando con el RAG."
        return state