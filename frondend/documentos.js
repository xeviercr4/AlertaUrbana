const API = "";

document.addEventListener("DOMContentLoaded", () => {
    const uploadArea = document.getElementById("uploadArea");
    const inputArchivo = document.getElementById("inputArchivo");

    // Click para seleccionar archivo
    uploadArea.addEventListener("click", () => inputArchivo.click());

    // Drag & drop
    uploadArea.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadArea.classList.add("dragover");
    });

    uploadArea.addEventListener("dragleave", () => {
        uploadArea.classList.remove("dragover");
    });

    uploadArea.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadArea.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            subirArchivo(e.dataTransfer.files[0]);
        }
    });

    // Selección de archivo
    inputArchivo.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            subirArchivo(e.target.files[0]);
        }
    });

    cargarDocumentos();
});


async function subirArchivo(file) {
    const extensiones = [".pdf", ".docx", ".txt"];
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();

    if (!extensiones.includes(ext)) {
        alert("Formato no soportado. Use: PDF, DOCX o TXT");
        return;
    }

    // Mostrar progreso
    const progressDiv = document.getElementById("uploadProgress");
    const progressFill = document.getElementById("progressFill");
    const statusText = document.getElementById("uploadStatus");

    progressDiv.style.display = "block";
    progressFill.style.width = "30%";
    statusText.textContent = `Subiendo ${file.name}...`;

    const formData = new FormData();
    formData.append("archivo", file);

    try {
        progressFill.style.width = "60%";
        statusText.textContent = "Procesando y generando embeddings...";

        const response = await fetch(API + "/rag/documentos/subir", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Error al subir el documento");
        }

        const doc = await response.json();

        progressFill.style.width = "100%";
        statusText.textContent = `${doc.nombre} indexado (${doc.num_chunks} fragmentos)`;

        setTimeout(() => {
            progressDiv.style.display = "none";
            progressFill.style.width = "0%";
        }, 3000);

        // Recargar lista
        cargarDocumentos();

    } catch (error) {
        progressFill.style.width = "100%";
        progressFill.style.background = "#e74c3c";
        statusText.textContent = "Error: " + error.message;
        console.error("Error subiendo documento:", error);

        setTimeout(() => {
            progressDiv.style.display = "none";
            progressFill.style.width = "0%";
            progressFill.style.background = "";
        }, 4000);
    }
}


async function cargarDocumentos() {
    try {
        const response = await fetch(API + "/rag/documentos");
        const docs = await response.json();

        const container = document.getElementById("listaDocumentos");

        if (docs.length === 0) {
            container.innerHTML = '<p class="empty-state">No hay documentos cargados aun.</p>';
            actualizarStats(docs);
            return;
        }

        let html = "";
        docs.forEach(doc => {
            const tamano = (doc.tamano / 1024).toFixed(1);
            const fecha = new Date(doc.fecha_carga).toLocaleDateString("es-ES", {
                day: "2-digit", month: "short", year: "numeric",
                hour: "2-digit", minute: "2-digit"
            });

            html += `
                <div class="doc-card">
                    <div class="doc-info">
                        <div class="doc-icon">${iconoTipo(doc.tipo)}</div>
                        <div class="doc-details">
                            <strong>${doc.nombre}</strong>
                            <span class="doc-meta">
                                ${tamano} KB | ${doc.num_chunks} fragmentos | ${doc.caracteres.toLocaleString()} caracteres
                            </span>
                            <span class="doc-fecha">${fecha}</span>
                        </div>
                    </div>
                    <div class="doc-actions">
                        <span class="doc-estado ${doc.estado}">${doc.estado}</span>
                        <button class="btn-delete" onclick="eliminarDocumento('${doc.doc_id}', '${doc.nombre}')">
                            Eliminar
                        </button>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
        actualizarStats(docs);

    } catch (error) {
        console.error("Error cargando documentos:", error);
        document.getElementById("listaDocumentos").innerHTML =
            '<p class="empty-state">Error al cargar documentos.</p>';
    }
}


function iconoTipo(tipo) {
    const iconos = { ".pdf": "PDF", ".docx": "DOC", ".txt": "TXT" };
    return iconos[tipo] || "?";
}


function actualizarStats(docs) {
    document.getElementById("statDocs").textContent = docs.length;
    document.getElementById("statChunks").textContent =
        docs.reduce((sum, d) => sum + (d.num_chunks || 0), 0);
    document.getElementById("statCaracteres").textContent =
        docs.reduce((sum, d) => sum + (d.caracteres || 0), 0).toLocaleString();
}


async function eliminarDocumento(docId, nombre) {
    if (!confirm(`Eliminar "${nombre}"? Esta accion no se puede deshacer.`)) return;

    try {
        const response = await fetch(API + `/rag/documentos/${docId}`, {
            method: "DELETE"
        });

        if (!response.ok) {
            throw new Error("Error al eliminar");
        }

        cargarDocumentos();

    } catch (error) {
        console.error("Error eliminando documento:", error);
        alert("Error al eliminar el documento.");
    }
}
