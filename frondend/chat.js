const API = "";

document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("inputPregunta");
    const btn = document.getElementById("btnEnviar");

    btn.addEventListener("click", enviarPregunta);
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") enviarPregunta();
    });

    cargarMetricas();
});


async function enviarPregunta() {
    const input = document.getElementById("inputPregunta");
    const pregunta = input.value.trim();
    if (!pregunta) return;

    // Mostrar pregunta del usuario
    agregarMensaje(pregunta, "usuario");
    input.value = "";

    // Mostrar indicador de carga
    const loadingId = agregarMensaje("Buscando en documentos...", "sistema loading");

    try {
        const response = await fetch(API + "/rag/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pregunta, top_k: 5 })
        });

        const data = await response.json();

        // Remover indicador de carga
        document.getElementById(loadingId)?.remove();

        // Mostrar respuesta
        agregarRespuestaRAG(data);

    } catch (error) {
        document.getElementById(loadingId)?.remove();
        agregarMensaje("Error al conectar con el servidor.", "sistema error");
        console.error("Error:", error);
    }
}


function agregarMensaje(texto, clase) {
    const container = document.getElementById("chatMessages");
    const div = document.createElement("div");
    const id = "msg-" + Date.now() + Math.random().toString(36).slice(2, 6);
    div.id = id;
    div.className = "message " + clase;
    div.textContent = texto;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}


function agregarRespuestaRAG(data) {
    const container = document.getElementById("chatMessages");
    const div = document.createElement("div");
    div.className = "message asistente";

    // Respuesta principal
    const respuestaDiv = document.createElement("div");
    respuestaDiv.className = "respuesta-texto";
    respuestaDiv.textContent = data.respuesta;
    div.appendChild(respuestaDiv);

    // Fuentes
    if (data.fuentes && data.fuentes.length > 0) {
        const fuentesDiv = document.createElement("div");
        fuentesDiv.className = "fuentes";
        fuentesDiv.innerHTML = "<strong>Fuentes:</strong> " +
            data.fuentes.map(f => `<span class="fuente-tag">${f}</span>`).join(" ");
        div.appendChild(fuentesDiv);
    }

    // Feedback
    const feedbackDiv = document.createElement("div");
    feedbackDiv.className = "feedback-area";
    feedbackDiv.innerHTML = `
        <button class="btn-feedback btn-like" onclick="enviarFeedback('${data.interaction_id}', 'like', this)">
            +1 Util
        </button>
        <button class="btn-feedback btn-dislike" onclick="enviarFeedback('${data.interaction_id}', 'dislike', this)">
            -1 No util
        </button>
        <input type="text" class="input-comentario" placeholder="Comentario opcional..."
               onkeydown="if(event.key==='Enter') enviarComentario('${data.interaction_id}', this)">
    `;
    div.appendChild(feedbackDiv);

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}


async function enviarFeedback(interactionId, tipo, btn) {
    try {
        await fetch(API + "/rag/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                interaction_id: interactionId,
                tipo: tipo
            })
        });

        // Visual feedback
        const parent = btn.closest(".feedback-area");
        parent.querySelectorAll(".btn-feedback").forEach(b => b.disabled = true);

        if (tipo === "like") {
            btn.classList.add("selected");
            btn.textContent = "Gracias!";
        } else {
            btn.classList.add("selected");
            btn.textContent = "Registrado";
        }

        cargarMetricas();

    } catch (error) {
        console.error("Error enviando feedback:", error);
    }
}


async function enviarComentario(interactionId, input) {
    const comentario = input.value.trim();
    if (!comentario) return;

    try {
        await fetch(API + "/rag/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                interaction_id: interactionId,
                tipo: "comentario",
                comentario: comentario
            })
        });

        input.value = "";
        input.placeholder = "Comentario enviado!";
        input.disabled = true;

        cargarMetricas();

    } catch (error) {
        console.error("Error enviando comentario:", error);
    }
}


async function cargarMetricas() {
    try {
        const response = await fetch(API + "/rag/metricas");
        const data = await response.json();

        document.getElementById("metTotal").textContent = data.total_interacciones;
        document.getElementById("metLikes").textContent = data.likes;
        document.getElementById("metDislikes").textContent = data.dislikes;
        document.getElementById("metTasaLikes").textContent = data.tasa_likes + "%";

    } catch (error) {
        console.error("Error cargando metricas:", error);
    }
}
