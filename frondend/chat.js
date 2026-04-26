function formatText(text) {
    if (!text) return "";
    return text
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/### (.*?)/g, "<h4>$1</h4>")
        .replace(/## (.*?)/g, "<h3>$1</h3>")
        .replace(/# (.*?)/g, "<h2>$1</h2>")
        .replace(/\n/g, "<br>");
}

const API_BASE = window.location.origin.startsWith("http")
    ? window.location.origin
    : "http://127.0.0.1:8000";

window.runChat = async function () {
    const task = document.getElementById("chatTask").value.trim();
    const statusBox = document.getElementById("chatStatus");
    const resultBox = document.getElementById("chatResult");
    const verifyBox = document.getElementById("chatVerification");

    if (!task) {
        statusBox.innerHTML = "⚠️ Escribí una solicitud primero.";
        return;
    }

    statusBox.innerHTML = "⏳ El sistema multiagente está trabajando (planner → researcher → analyst → decision → writer → verifier)...";
    resultBox.innerHTML = "<em>Procesando...</em>";
    verifyBox.innerHTML = "—";

    try {
        const response = await fetch(`${API_BASE}/multiagent/prioritize`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task })
        });

        const data = await response.json();

        statusBox.innerHTML = `✅ Listo (intentos del verificador: ${data.attempts || 1})`;
        resultBox.innerHTML = formatText(data.final || "Sin respuesta final.");

        const v = data.verification || {};
        const status = v.status || "—";
        const feedback = v.feedback || "Reporte aprobado sin observaciones.";
        verifyBox.innerHTML = `<strong>Estado:</strong> ${status}<br><strong>Feedback:</strong> ${formatText(feedback)}`;
    } catch (err) {
        console.error(err);
        statusBox.innerHTML = "❌ Error de conexión con el backend.";
        resultBox.innerHTML = "—";
    }
};
