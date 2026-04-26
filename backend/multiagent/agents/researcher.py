from pathlib import Path
import requests

from rag.vector_store import VectorStore
from rag.generator import generate_answer

# 🔥 Inicializar vector store (se mantiene, pero no lo usamos directamente)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "rag_data"

vector_store = VectorStore(DATA_DIR)


def researcher_node(state):

    # 🧠 1. Obtener la tarea del usuario
    task = state.get("task", "").strip()

    if not task:
        state["rules"] = "No se proporcionó una tarea válida."
        return state

    # 🔥 2. Query enriquecida (mejor contexto para el RAG)
    query = f"""
    normativa del servicio de agua potable, sanciones, multas,
    suspensión del servicio, reconexión, obligaciones del abonado.
    Consulta del usuario: {task}
    """

    try:
        # 🔎 3. LLAMAR AL RAG REAL (endpoint que ya funciona)
        response = requests.post(
            "http://127.0.0.1:8000/rag/query",
            json={"question": query}
        )

        # 🚨 4. Validar respuesta
        if response.status_code != 200:
            state["rules"] = "Error consultando el sistema RAG."
            print("❌ ERROR STATUS:", response.status_code)
            return state

        data = response.json()

        # 🧠 5. Extraer respuesta del RAG
        result = data.get("answer", "Sin respuesta del RAG")

        # 💾 6. Guardar resultado
        state["rules"] = result

        print("🔎 RULES:", result)

        return state

    except Exception as e:
        print("❌ ERROR RAG:", e)
        state["rules"] = "Error conectando con el RAG."
        return state