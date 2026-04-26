// 🔥 FORMATEADOR GLOBAL (CLAVE)
function formatText(text) {
    if (!text) return "";

    return text
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") // negritas
        .replace(/### (.*?)/g, "<h4>$1</h4>")             // títulos
        .replace(/## (.*?)/g, "<h3>$1</h3>")
        .replace(/# (.*?)/g, "<h2>$1</h2>")
        .replace(/\n/g, "<br>");                         // saltos de línea
}

window.runMultiagent = async function () {

    const task = document.getElementById("multiagentTask").value;

    console.log("🚀 Ejecutando multiagente...");

    const plannerBox = document.getElementById("plannerResult");
    const researcherBox = document.getElementById("researcherResult");
    const analystBox = document.getElementById("analystResult");
    const decisionBox = document.getElementById("decisionResult");
    const writerBox = document.getElementById("writerResult");

    // loaders
    if (plannerBox) plannerBox.innerHTML = "⏳ Ejecutando...";
    if (researcherBox) researcherBox.innerHTML = "";
    if (analystBox) analystBox.innerHTML = "";
    if (decisionBox) decisionBox.innerHTML = "";
    if (writerBox) writerBox.innerHTML = "";

    try {
        const response = await fetch("http://127.0.0.1:8000/multiagent/prioritize", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ task })
        });

        const data = await response.json();

        // 🧠 Planner
        if (plannerBox && data.plan) {
            plannerBox.innerHTML = `<div class="agent-text">${formatText(data.plan)}</div>`;
        }

        // 🔎 Researcher
        if (researcherBox && data.rules) {
            researcherBox.innerHTML = `<div class="agent-text">${formatText(data.rules)}</div>`;
        }

        // 📊 Analyst
        if (analystBox && Array.isArray(data.analysis)) {
            let html = "";
            data.analysis.forEach(t => {
                html += `<div class="card agent-text">${formatText(t.descripcion)}</div>`;
            });
            analystBox.innerHTML = html;
        }

        // ⚖️ Decision (ordenado)
        if (decisionBox && Array.isArray(data.prioritized)) {

            const prioridadOrden = {
                "ALTA": 1,
                "Alta": 1,
                "MEDIA": 2,
                "Media": 2,
                "BAJA": 3,
                "Baja": 3
            };

            const sorted = data.prioritized.sort((a, b) => {
                return prioridadOrden[a.prioridad] - prioridadOrden[b.prioridad];
            });

            let html = "";

            sorted.forEach(t => {
                html += `
                    <div class="card">
                        <strong>${t.id}</strong><br>
                        <span class="priority ${t.prioridad}">
                            ${t.prioridad}
                        </span>
                    </div>
                `;
            });

            decisionBox.innerHTML = html;
        }

        // ✍️ Writer
        if (writerBox && data.final) {
            writerBox.innerHTML =
                `<div class="report agent-text">${formatText(data.final)}</div>`;
        }

    } catch (error) {
        console.error(error);

        if (plannerBox) plannerBox.innerHTML = "❌ Error";
    }
};