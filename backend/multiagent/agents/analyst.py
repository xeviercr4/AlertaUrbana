from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyst_node(state):

    tickets = state.get("tickets", [])
    rules = state.get("rules", "")
    task = state.get("task", "")

    # 🔥 convertir tickets a texto
    tickets_text = "\n".join([
        f"{t.get('ticket_id')} - {t.get('descripcion')} (categoria: {t.get('categoria')})"
        for t in tickets
    ])

    prompt = f"""
Eres un analista municipal experto.

Tu tarea es analizar tickets de incidentes usando:
- la solicitud del usuario
- la normativa municipal (RAG)

NO inventes información.
USA SOLO los tickets proporcionados.

---

SOLICITUD DEL USUARIO:
{task}

---

CONTEXTO NORMATIVO:
{rules}

---

TICKETS:
{tickets_text}

---

INSTRUCCIONES:

1. Analiza cada ticket según el contexto
2. Determina:
   - nivel de riesgo: ALTO, MEDIO, BAJO
   - prioridad sugerida: ALTA, MEDIA, BAJA
3. Justifica cada decisión usando la normativa

---

RESPONDE SOLO EN JSON (sin texto adicional):

[
  {{
    "id": "...",
    "descripcion": "...",
    "riesgo": "...",
    "prioridad_sugerida": "...",
    "justificacion": "..."
  }}
]
"""

    response = client.chat.completions.create(
        model="gpt-5.4",
        messages=[
            {"role": "system", "content": "Eres un analista experto en gestión municipal."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_completion_tokens=900
    )

    content = response.choices[0].message.content.strip()

    try:
        analysis = json.loads(content)
    except:
        print("⚠️ Error parseando JSON del analyst")
        analysis = []

    state["analysis"] = analysis

    print("📊 ANALYSIS:", analysis)

    return state