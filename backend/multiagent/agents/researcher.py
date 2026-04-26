import logging

try:
    from backend.rag.router import _get_vector_store
    from backend.rag.generator import generate_answer
except ImportError:
    from rag.router import _get_vector_store
    from rag.generator import generate_answer


logger = logging.getLogger("alertaurbana.multiagent.researcher")


def _domain_context(task: str) -> str:
    t = task.lower()
    if any(w in t for w in ["basura", "residuos", "desechos"]):
        return (
            "normativa de manejo de residuos sólidos, recolección de basura, "
            "sanciones por mala disposición, horarios, obligaciones del ciudadano."
        )
    if any(w in t for w in ["bache", "calle", "vía", "via"]):
        return (
            "normativa de mantenimiento vial, baches, señalización, "
            "responsabilidad municipal sobre infraestructura vial."
        )
    if any(w in t for w in ["luz", "alumbrado"]):
        return (
            "normativa de alumbrado público, mantenimiento eléctrico, "
            "tiempos de respuesta y prioridades por riesgo."
        )
    return (
        "normativa del servicio de agua potable, sanciones, multas, "
        "suspensión y reconexión, obligaciones del abonado."
    )


def researcher_node(state):
    task = state.get("task", "").strip()
    plan = state.get("plan", "").strip()

    if not task:
        state["rules"] = "No se proporcionó una tarea válida."
        return state

    context = _domain_context(task)
    query = (
        f"{context}\n"
        f"Tarea: {task}\n"
        f"Plan a seguir: {plan}"
    )

    try:
        # Reusa el mismo singleton de VectorStore que usa el router de RAG,
        # así los documentos subidos vía /rag/upload son visibles aquí.
        vs = _get_vector_store()
        results = vs.search(query, top_k=3)
        chunks = [r["text"] for r in results]

        if not chunks:
            state["rules"] = (
                "Sin documentos en el vector store. Aplicar criterios estándar: "
                "ALTA para riesgo a la vida o servicios esenciales (agua, alumbrado, "
                "peligros), MEDIA para infraestructura afectada, BAJA para incidentes "
                "estéticos o no urgentes."
            )
        else:
            state["rules"] = generate_answer(query, chunks)

        logger.info(
            "RULES generadas a partir de %d chunks (vector_store total=%d)",
            len(chunks), vs.total_chunks
        )
    except Exception as e:
        logger.exception("Error en researcher: %s", e)
        state["rules"] = "Error consultando el RAG; aplicar criterios estándar."

    return state
