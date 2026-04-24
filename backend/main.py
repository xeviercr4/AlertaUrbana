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
import logging

# 🔥 NUEVO IMPORT MULTIAGENTE
from multiagent.graph import build_graph

logger = logging.getLogger("alertaurbana")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    logger.addHandler(_h)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DB_FILE = BASE_DIR / "tickets.json"
FRONTEND_DIR = BASE_DIR.parent / "frondend"

app = FastAPI(title="SmartCity AI API")

# 🔥 INICIALIZAR GRAPH (FUERA DE TODO)
graph = build_graph()

# RAG router
try:
    from backend.rag.router import router as rag_router
except ImportError:
    from rag.router import router as rag_router

app.include_router(rag_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_KEY = os.getenv("AZURE_KEY")

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


class Reporte(BaseModel):
    texto: str
    imagen_url: str = None


def analizar_sentimiento(texto: str):
    url = AZURE_ENDPOINT.rstrip("/") + "/text/analytics/v3.1/sentiment"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "documents": [
            {"id": "1", "language": "es", "text": texto}
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(response.text)
    return response.json()["documents"][0]["sentiment"]


def extraer_frases_clave(texto: str):
    url = AZURE_ENDPOINT.rstrip("/") + "/text/analytics/v3.1/keyPhrases"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "documents": [
            {"id": "1", "language": "es", "text": texto}
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(response.text)
    return response.json()["documents"][0]["keyPhrases"]


def clasificar_categoria(frases_clave):
    frases = " ".join(frases_clave).lower()
    if any(p in frases for p in ["basura"]):
        return "BASURA"
    elif any(p in frases for p in ["hueco", "bache"]):
        return "BACHE"
    elif any(p in frases for p in ["luz"]):
        return "ALUMBRADO"
    elif any(p in frases for p in ["agua", "fuga"]):
        return "AGUA"
    return "OTRO"


def calcular_prioridad(categoria, sentimiento, texto):
    prioridad = "BAJA"
    if categoria in ["BACHE", "ALUMBRADO", "AGUA"]:
        prioridad = "MEDIA"
    if sentimiento == "negative":
        prioridad = "ALTA"
    if any(p in texto.lower() for p in ["peligro", "urgente"]):
        prioridad = "ALTA"
    return prioridad


def generar_ticket(categoria, prioridad, descripcion, tiene_imagen):
    return {
        "ticket_id": f"SC-{uuid.uuid4().hex[:8].upper()}",
        "categoria": categoria,
        "prioridad": prioridad,
        "descripcion": descripcion,
        "estado": "ABIERTO",
        "evidencia_imagen": tiene_imagen,
        "fecha_creacion": datetime.now().isoformat()
    }


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


@app.post("/analizar")
def analizar_reporte(texto: str = Form(...), imagen: UploadFile = File(None)):
    sentimiento = analizar_sentimiento(texto)
    frases = extraer_frases_clave(texto)
    categoria = clasificar_categoria(frases)
    prioridad = calcular_prioridad(categoria, sentimiento, texto)

    ticket = generar_ticket(categoria, prioridad, texto, imagen is not None)
    guardar_ticket(ticket)

    return ticket


@app.get("/tickets")
def obtener_tickets():
    return cargar_tickets()


class BusquedaRequest(BaseModel):
    consulta: str


@app.post("/buscar")
def buscar_tickets(req: BusquedaRequest):
    return []


# 🔥 ============================
# 🔥 NUEVO ENDPOINT MULTIAGENTE
# 🔥 ============================
@app.post("/multiagent/prioritize")
def run_multiagent(request: dict):

    tickets = cargar_tickets()

    state = {
        "task": request["task"],
        "tickets": tickets
    }

    result = graph.invoke(state)

    return result


# FRONTEND
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")