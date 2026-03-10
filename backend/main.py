from datetime import datetime
from urllib import response
import uuid
from wsgiref import headers

from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests

from dotenv import load_dotenv
import json
import os

import numpy as np
import faiss
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DB_FILE = BASE_DIR / "tickets.json"
FRONTEND_DIR = BASE_DIR.parent / "frondend"

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

# ==============================
# CONFIGURACIÓN OPENAI
# ==============================
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

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
    if any(p in frases for p in ["basura", "residuos", "desechos", "suciedad", "escombros", "desperdicios", "reciclaje", "contenedor"]):
        return "BASURA"
    elif any(p in frases for p in ["hueco", "bache", "calle dañada", "pavimento", "grieta", "hundimiento", "asfalto", "vía dañada"]):
        return "BACHE"
    elif any(p in frases for p in ["luz", "poste", "alumbrado", "iluminación", "lámpara", "bombilla", "oscuro", "oscuridad", "apagón", "cable eléctrico", "farola"]):
        return "ALUMBRADO"
    elif any(p in frases for p in ["agua", "fuga", "tubería", "inundación", "alcantarilla", "drenaje", "cloaca", "caño roto", "charco"]):
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
        data=image_bytes,
        timeout=15
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
        "BASURA": ["trash", "garbage", "waste", "litter", "debris", "junk", "dump", "dirty", "rubbish", "pollution"],
        "BACHE": ["pothole", "hole", "crack", "asphalt"],
        "ALUMBRADO": ["light", "lamp", "pole", "streetlight", "cables", "lighting", "bulb", "dark", "electricity", "wire", "night", "tower"],
        "AGUA": ["water", "pipe", "leak", "flood", "wet", "puddle", "drain", "sewer", "mud", "rain", "overflow"]
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
# FUNCIONES BÚSQUEDA SEMÁNTICA (FAISS)
# =====================================
def obtener_embedding(texto: str) -> list[float]:
    response = openai_client.embeddings.create(
        input=texto,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding


def extraer_filtros(consulta: str):
    """Extrae filtros estructurados de la consulta en lenguaje natural."""
    texto = consulta.lower()
    filtros = {}

    # Estado
    if any(p in texto for p in ["cerrado", "resuelto", "solucionado", "atendido", "reparado"]):
        filtros["estado"] = "CERRADO"
    elif any(p in texto for p in ["abierto", "pendiente", "sin resolver", "activo"]):
        filtros["estado"] = "ABIERTO"

    # Categoría
    if any(p in texto for p in ["bache", "hueco", "pavimento", "asfalto", "calle dañada"]):
        filtros["categoria"] = "BACHE"
    elif any(p in texto for p in ["basura", "desechos", "escombros", "residuos", "suciedad"]):
        filtros["categoria"] = "BASURA"
    elif any(p in texto for p in ["luz", "alumbrado", "poste", "farola", "lámpara", "cable eléctrico", "electricidad", "apagón"]):
        filtros["categoria"] = "ALUMBRADO"
    elif any(p in texto for p in ["agua", "fuga", "tubería", "inundación", "alcantarilla", "drenaje"]):
        filtros["categoria"] = "AGUA"

    # Prioridad
    if any(p in texto for p in ["urgente", "alta prioridad", "prioridad alta", "crítico", "grave"]):
        filtros["prioridad"] = "ALTA"
    elif any(p in texto for p in ["prioridad media", "media prioridad"]):
        filtros["prioridad"] = "MEDIA"
    elif any(p in texto for p in ["prioridad baja", "baja prioridad", "no urgente"]):
        filtros["prioridad"] = "BAJA"

    return filtros


def construir_indice_faiss(tickets: list[dict]):
    """Construye un índice FAISS a partir de una lista de tickets."""
    if not tickets:
        return None

    descripciones = [t["descripcion"] for t in tickets]
    embeddings = []
    for desc in descripciones:
        embeddings.append(obtener_embedding(desc))

    matrix = np.array(embeddings, dtype="float32")
    index = faiss.IndexFlatL2(EMBEDDING_DIM)
    index.add(matrix)
    return index


def buscar_tickets_similares(consulta: str, top_k: int = 3):
    todos = cargar_tickets()
    if not todos:
        return []

    # 1. Extraer filtros estructurados de la consulta
    filtros = extraer_filtros(consulta)

    # 2. Pre-filtrar tickets por atributos exactos
    filtrados = todos
    for campo, valor in filtros.items():
        filtrados = [t for t in filtrados if t.get(campo) == valor]

    # Si no quedan tickets tras filtrar, buscar en todos
    if not filtrados:
        filtrados = todos

    # 3. Construir índice FAISS solo con los tickets filtrados
    index = construir_indice_faiss(filtrados)
    if index is None:
        return []

    # 4. Búsqueda semántica sobre descripciones
    query_emb = np.array([obtener_embedding(consulta)], dtype="float32")
    k = min(top_k, index.ntotal)
    distances, indices = index.search(query_emb, k)

    resultados = []
    for i, idx in enumerate(indices[0]):
        if idx < len(filtrados):
            ticket = filtrados[idx].copy()
            ticket["score"] = float(distances[0][i])
            resultados.append(ticket)
    return resultados


# =====================================
# ENDPOINT PRINCIPAL
# =====================================
@app.post("/analizar")
def analizar_reporte(
    texto: str = Form(...),
    imagen: UploadFile = File(None)
):
    print("Texto recibido:", texto)

    sentimiento = analizar_sentimiento(texto)
    frases_clave = extraer_frases_clave(texto)
    categoria_texto = clasificar_categoria(frases_clave)

    categoria_imagen = None
    if imagen:
        contenido = imagen.file.read()
        print("Imagen recibida:", len(contenido), "bytes")
        tags = analizar_imagen_bytes(contenido)
        categoria_imagen = clasificar_por_tags(tags)

    categoria_final = categoria_imagen or categoria_texto

    prioridad = calcular_prioridad(
        categoria_final,
        sentimiento,
        texto
    )

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


class BusquedaRequest(BaseModel):
    consulta: str


@app.post("/buscar")
def buscar_tickets(req: BusquedaRequest):
    resultados = buscar_tickets_similares(req.consulta, top_k=3)
    return resultados


# Servir frontend estático (debe ir al final para no interceptar rutas API)
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")