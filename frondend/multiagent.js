async function runMultiagent() {

    const task = document.getElementById("multiagentTask").value;
    const resultBox = document.getElementById("multiagentResult");

    resultBox.innerHTML = `<div class="loader">🤖 Procesando con agentes inteligentes...</div>`;

    try {
        const response = await fetch("http://127.0.0.1:8000/multiagent/prioritize", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ task })
        });

        const data = await response.json();

        let html = "<h2>📊 Prioridades</h2>";

        if (Array.isArray(data.prioritized)) {

            // 🔥 ORDEN PERSONALIZADO
            const prioridadOrden = {
                "ALTA": 1,
                "Alta": 1,
                "MEDIA": 2,
                "Media": 2,
                "BAJA": 3,
                "Baja": 3
            };

            // 🔥 SORT
            const sorted = data.prioritized.sort((a, b) => {
                return prioridadOrden[a.prioridad] - prioridadOrden[b.prioridad];
            });

            // 🔥 RENDER
            sorted.forEach(t => {
                html += `
                    <div class="card">
                        <h3>${t.id}</h3>
                        <span class="priority ${t.prioridad}">
                            ${t.prioridad}
                        </span>
                    </div>
                `;
            });
        }

        html += `
            <div class="report">
                <h2>📝 Reporte</h2>
                <p>${data.final.replace(/\n/g, "<br>")}</p>
            </div>
        `;

        resultBox.innerHTML = html;

    } catch (error) {
        resultBox.innerHTML = "❌ Error ejecutando multiagente";
        console.error(error);
    }
}