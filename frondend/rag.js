// ==============================
// 🌐 CONFIG
// ==============================
const API_BASE = "http://127.0.0.1:8000";

// ==============================
// 📑 TABS
// ==============================
function showTab(tabId, btn) {
    document.querySelectorAll(".tab-panel").forEach(tab => {
        tab.style.display = "none";
    });

    document.getElementById(tabId).style.display = "block";

    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
}

// ==============================
// 💬 CHAT RAG
// ==============================
async function sendQuestion() {
    const input = document.getElementById("question-input");
    const question = input.value.trim();
    if (!question) return;

    const chatBox = document.getElementById("chat-messages");

    appendMessage("user", question);
    input.value = "";

    appendMessage("bot", "⏳ Pensando...");

    try {
        const response = await fetch(`${API_BASE}/rag/query`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: question })
        });

        const data = await response.json();

        removeLastBotMessage();
        appendMessage("bot", data.answer || "Sin respuesta");

    } catch (error) {
        removeLastBotMessage();
        appendMessage("bot", "❌ Error al consultar RAG");
        console.error(error);
    }
}

// Enter + Ctrl
function handleChatKey(event) {
    if (event.key === "Enter" && event.ctrlKey) {
        sendQuestion();
    }
}

// ==============================
// 💬 UI CHAT HELPERS
// ==============================
function appendMessage(role, text) {
    const chatBox = document.getElementById("chat-messages");

    const div = document.createElement("div");
    div.className = `chat-msg ${role}`;
    div.textContent = text;

    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function removeLastBotMessage() {
    const chatBox = document.getElementById("chat-messages");
    const messages = chatBox.querySelectorAll(".chat-msg.bot");

    if (messages.length > 0) {
        messages[messages.length - 1].remove();
    }
}

// ==============================
// 📄 DOCUMENTOS (RAG)
// ==============================
async function uploadDocument() {
    const input = document.getElementById("doc-file-input");
    const file = input.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
        await fetch(`${API_BASE}/rag/upload`, {
            method: "POST",
            body: formData
        });

        alert("✅ Documento subido");
        loadDocuments();

    } catch (error) {
        alert("❌ Error al subir documento");
        console.error(error);
    }
}

async function loadDocuments() {
    const list = document.getElementById("doc-list");

    try {
        const res = await fetch(`${API_BASE}/rag/documents`);
        const docs = await res.json();

        if (!docs.length) {
            list.innerHTML = "<p>No hay documentos</p>";
            return;
        }

        list.innerHTML = docs.map(d => `
            <div class="card">
                📄 ${d.filename}
            </div>
        `).join("");

    } catch (error) {
        list.innerHTML = "❌ Error cargando documentos";
    }
}

// ==============================
// 📊 METRICS
// ==============================
async function loadMetrics() {
    const grid = document.getElementById("metrics-grid");

    try {
        const res = await fetch(`${API_BASE}/rag/metrics`);
        const data = await res.json();

        grid.innerHTML = `
            <div class="card">Consultas: ${data.total_queries}</div>
            <div class="card">Precisión: ${data.accuracy}</div>
        `;

    } catch (error) {
        grid.innerHTML = "❌ Error cargando métricas";
    }
}