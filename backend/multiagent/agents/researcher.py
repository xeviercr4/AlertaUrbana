from pathlib import Path

from rag.vector_store import VectorStore
from rag.generator import generate_answer


# 🔥 Inicializar vector store (igual que tu RAG)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "rag_data"

vector_store = VectorStore(DATA_DIR)


def researcher_node(state):

    query = "criterios de priorización de incidentes municipales agua"

    # 🔎 1. Buscar chunks relevantes
    results = vector_store.search(query, top_k=3)

    # 🧠 2. Extraer textos
    chunks = [r["text"] for r in results]

    # 🧠 3. Generar respuesta con RAG
    result = generate_answer(query, chunks)

    state["rules"] = result

    print("🔎 RULES:", result)

    return state