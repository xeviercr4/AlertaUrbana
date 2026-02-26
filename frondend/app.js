const API = "";

document.addEventListener("DOMContentLoaded", () => {

    console.log("JS CARGADO");

    /* =========================
       PREVIEW IMAGEN
    ========================= */
    const inputImagen = document.getElementById("imagen");
    const preview = document.getElementById("preview");

    inputImagen.addEventListener("change", (e) => {

        const file = e.target.files[0];

        if (file) {
            preview.src = URL.createObjectURL(file);
            preview.style.display = "block";
        }
    });

    /* =========================
       BOTON ENVIAR
    ========================= */
    document
        .getElementById("btnEnviar")
        .addEventListener("click", enviarReporte);

});


/* =========================
   ENVIAR REPORTE
========================= */

async function enviarReporte(event) {

    // ⭐ evita cualquier comportamiento default del navegador
    if (event) event.preventDefault();

    console.log("BOTON FUNCIONA");

    const texto = document.getElementById("texto").value;
    const imagenInput = document.getElementById("imagen");

    const formData = new FormData();
    formData.append("texto", texto);

    if (imagenInput.files.length > 0) {
        formData.append("imagen", imagenInput.files[0]);
    }

    try {

        const response = await fetch(API + "/analizar", {
            method: "POST",
            body: formData
        });

        const raw = await response.text();

        console.log("RESPUESTA BACKEND >>>");
        console.log(raw);

        let ticket;

        try {
            ticket = JSON.parse(raw);
        } catch(e){
            console.error("NO ES JSON VALIDO");
            return;
        }

        console.log("OBJETO FINAL:", ticket);

        mostrarTicket(ticket);

        // actualizar historial
        cargarTickets();

        // limpiar formulario (UX mejor)
        document.getElementById("texto").value = "";
        document.getElementById("imagen").value = "";
        document.getElementById("preview").style.display = "none";

    } catch (error) {
        console.error("Error enviando reporte:", error);
    }
}


/* =========================
   MOSTRAR TICKET
========================= */

function mostrarTicket(ticket) {

    console.log("MOSTRANDO TICKET:", ticket);

    const contenedor = document.getElementById("ticketResultado");

    contenedor.innerHTML = `
        <div class="ticket ${ticket.prioridad}">
            <h3>🎫 Ticket generado</h3>

            <p><b>ID:</b> ${ticket.ticket_id}</p>
            <p><b>Categoría:</b> ${ticket.categoria}</p>
            <p><b>Prioridad:</b> ${ticket.prioridad}</p>
            <p><b>Estado:</b> ${ticket.estado}</p>
            <p><b>Descripción:</b> ${ticket.descripcion}</p>
            <p><b>Fecha:</b> ${ticket.fecha_creacion}</p>
        </div>
    `;

    // ⭐ asegura que el usuario vea el ticket
    contenedor.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


/* =========================
   HISTORIAL
========================= */

async function cargarTickets() {

    try {

        const response = await fetch(API + "/tickets");
        const tickets = await response.json();

        let html = "";

        tickets.slice().reverse().forEach(t => {
            html += `
                <div class="card">
                    <b>${t.ticket_id}</b><br>
                    ${t.categoria} — Prioridad: ${t.prioridad}
                </div>
            `;
        });

        document.getElementById("historial").innerHTML = html;

    } catch (error) {
        console.error("Error cargando historial:", error);
    }
}