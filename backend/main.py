from datetime import datetime
from urllib import response
import uuid
from wsgiref import headers

from fastapi import FastAPI
from pydantic import BaseModel
from pyparsing import Optional
import requests

from fastapi import UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import json
import os

load_dotenv()

DB_FILE = "tickets.json"

app = FastAPI(title="SmartCity AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # permitir frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# CONFIGURACIÓN AZURE AI SERVICES
# ==============================
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_KEY = os.getenv("AZURE_KEY")

# =====================================
# MODELO DE REQUEST
# =====================================
class Reporte(BaseModel):
    texto: str
    imagen_url: str = None

# =====================================
# FUNCIONES IA
# =====================================
def analizar_sentimiento(texto: str):
    url = AZURE_ENDPOINT.rstrip("/") + "/text/analytics/v3.1/sentiment"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "documents": [
            {
                "id": "1",
                "language": "es",
                "text": texto
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(response.text)

    resultado = response.json()
    return resultado["documents"][0]["sentiment"]


def extraer_frases_clave(texto: str):
    url = AZURE_ENDPOINT.rstrip("/") + "/text/analytics/v3.1/keyPhrases"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "documents": [
            {
                "id": "1",
                "language": "es",
                "text": texto
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(response.text)

    resultado = response.json()
    return resultado["documents"][0]["keyPhrases"]


# =====================================
# LÓGICA SMART CITY
# =====================================
def clasificar_categoria(frases_clave):
    frases = " ".join(frases_clave).lower()
    if any(p in frases for p in ["basura", "residuos", "desechos"]):
        return "BASURA"
    elif any(p in frases for p in ["hueco", "bache", "carretera", "calle dañada"]):
        return "BACHE"
    elif any(p in frases for p in ["luz", "poste", "alumbrado", "iluminación"]):
        return "ALUMBRADO"
    elif any(p in frases for p in ["agua", "fuga", "tubería"]):
        return "AGUA"
    return "OTRO"

def analizar_imagen(url_imagen: str):
    vision_url = (
        AZURE_ENDPOINT.rstrip("/") +
        "/computervision/imageanalysis:analyze"
        "?api-version=2023-02-01-preview&features=tags"
    )
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "application/json"
    }
    body = {"url": url_imagen}

    response = requests.post(vision_url, headers=headers, json=body)
    if response.status_code != 200:
        return []

    resultado = response.json()
    if "tagsResult" not in resultado:
        return []

    return [
        tag["name"]
        for tag in resultado["tagsResult"]["values"]
    ]


def calcular_prioridad(categoria, sentimiento, texto):
    prioridad = "BAJA"

    if categoria in ["BACHE", "ALUMBRADO", "AGUA"]:
        prioridad = "MEDIA"
    if sentimiento == "negative":
        prioridad = "ALTA"

    texto = texto.lower()
    if any(p in texto for p in ["peligro", "accidente", "urgente", "riesgo"]):
        prioridad = "ALTA"
    return prioridad


def analizar_imagen_bytes(image_bytes):
    vision_url = (
        AZURE_ENDPOINT.rstrip("/") +
        "/computervision/imageanalysis:analyze?api-version=2024-02-01&features=tags"
    )
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "application/octet-stream"
    }
    response = requests.post(
        vision_url,
        headers=headers,
        data=image_bytes
    )
    print("STATUS VISION:", response.status_code)
    print("CONTENT TYPE:", response.headers.get("content-type"))

    if "application/json" not in response.headers.get("content-type", ""):
        print("⚠️ Azure devolvió algo que NO es JSON")
        print(response.content[:200])  # solo preview bytes
        return []

    if response.status_code != 200:
        print("ERROR AZURE:", response.text)
        return []

    resultado = response.json()
    if "tagsResult" not in resultado:
        return []

    return [
        tag["name"]
        for tag in resultado["tagsResult"]["values"]
    ]


def clasificar_por_tags(tags):
    tags_texto = " ".join(tags).lower()
    scores = {
        "BASURA": ["trash", "garbage", "waste", "litter"],
        "BACHE": ["pothole", "hole", "crack", "asphalt", "damage"],
        "AGUA": ["water", "pipe", "leak", "flood"]
    }
    resultado = {k:0 for k in scores}

    for categoria, palabras in scores.items():
        for palabra in palabras:
            if palabra in tags_texto:
                resultado[categoria] += 1

    mejor = max(resultado, key=resultado.get)
    return mejor if resultado[mejor] > 0 else None


def generar_ticket(categoria, prioridad, descripcion, tiene_imagen):
    ticket = {
        "ticket_id": f"SC-{uuid.uuid4().hex[:8].upper()}",
        "categoria": categoria,
        "prioridad": prioridad,
        "descripcion": descripcion,
        "estado": "ABIERTO",
        "evidencia_imagen": tiene_imagen,
        "fecha_creacion": datetime.now().isoformat()
    }
    return ticket


def cargar_tickets():
    if not os.path.exists(DB_FILE):
        return []

    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_ticket(ticket):
    tickets = cargar_tickets()
    tickets.append(ticket)

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(tickets, f, indent=2, ensure_ascii=False)


# =====================================
# ENDPOINT PRINCIPAL
# =====================================
@app.post("/analizar")
async def analizar_reporte(
    texto: str = Form(...),
    imagen: UploadFile = File(None)
):   
    print("Texto recibido:", texto)

    # =====================
    # ANALISIS TEXTO
    # =====================
    sentimiento = analizar_sentimiento(texto)
    frases_clave = extraer_frases_clave(texto)
    categoria_texto = clasificar_categoria(frases_clave)
    categoria_imagen = None

    # =====================
    # ANALISIS IMAGEN (opcional)
    # =====================
    categoria_imagen = None
    if imagen:
        contenido = await imagen.read()
        print("Imagen recibida:", len(contenido), "bytes")
        tags = analizar_imagen_bytes(contenido)
        categoria_imagen = clasificar_por_tags(tags)

    # =====================
    # DECISION FINAL
    # =====================
    categoria_final = categoria_imagen or categoria_texto
    prioridad = calcular_prioridad(
        categoria_final,
        sentimiento,
        texto
    )
    # =====================
    # GENERAR TICKET
    # =====================
    ticket = generar_ticket(
        categoria_final,
        prioridad,
        texto,
        imagen is not None
    )
    guardar_ticket(ticket)
    return ticket

@app.get("/tickets")
def obtener_tickets():
    return cargar_tickets()