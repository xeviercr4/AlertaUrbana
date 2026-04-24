def analyst_node(state):

    tickets = state["tickets"]

    analysis = []

    for t in tickets:
        analysis.append({
            "id": t.get("ticket_id"),  # 🔥 FIX
            "descripcion": t.get("descripcion"),
            "categoria": t.get("categoria"),
            "prioridad_original": t.get("prioridad")
        })

    state["analysis"] = analysis

    print("📊 ANALYSIS:", analysis)

    return state