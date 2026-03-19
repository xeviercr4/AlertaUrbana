"""
Pipeline RAG Avanzado
- Ingesta de documentos (PDF, DOCX, TXT)
- Chunking de texto
- Generación de embeddings (OpenAI)
- Almacenamiento vectorial (FAISS)
- Retrieval semántico
- Generación de respuestas (OpenAI GPT)
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
from openai import OpenAI

# ---------- configuración ----------
BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "documentos"
DOCS_DB = BASE_DIR / "documents.json"
FEEDBACK_DB = BASE_DIR / "feedback.json"
CHUNKS_DB = BASE_DIR / "chunks.json"

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
CHAT_MODEL = "gpt-4o-mini"

CHUNK_SIZE = 500       # caracteres por chunk
CHUNK_OVERLAP = 100    # solapamiento entre chunks

# ---------- cliente OpenAI ----------
_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


# =============================================
# CAPA DE PERSISTENCIA
# =============================================
def _load_json(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: list):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def cargar_documentos() -> list[dict]:
    return _load_json(DOCS_DB)


def guardar_documentos(docs: list[dict]):
    _save_json(DOCS_DB, docs)


def cargar_chunks() -> list[dict]:
    return _load_json(CHUNKS_DB)


def guardar_chunks(chunks: list[dict]):
    _save_json(CHUNKS_DB, chunks)


def cargar_feedback() -> list[dict]:
    return _load_json(FEEDBACK_DB)


def guardar_feedback(items: list[dict]):
    _save_json(FEEDBACK_DB, items)


# =============================================
# 1. INGESTA DE DOCUMENTOS
# =============================================
def extraer_texto_pdf(ruta: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(ruta))
    texto = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            texto += t + "\n"
    return texto.strip()


def extraer_texto_docx(ruta: Path) -> str:
    import docx
    doc = docx.Document(str(ruta))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extraer_texto_txt(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


def extraer_texto(ruta: Path) -> str:
    sufijo = ruta.suffix.lower()
    if sufijo == ".pdf":
        return extraer_texto_pdf(ruta)
    elif sufijo == ".docx":
        return extraer_texto_docx(ruta)
    elif sufijo == ".txt":
        return extraer_texto_txt(ruta)
    else:
        raise ValueError(f"Formato no soportado: {sufijo}")


# =============================================
# 2. CHUNKING
# =============================================
def crear_chunks(texto: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Divide el texto en fragmentos con solapamiento."""
    chunks = []
    inicio = 0
    while inicio < len(texto):
        fin = inicio + chunk_size
        chunk = texto[inicio:fin]
        if chunk.strip():
            chunks.append(chunk.strip())
        inicio += chunk_size - overlap
    return chunks


# =============================================
# 3. EMBEDDINGS
# =============================================
def obtener_embedding(texto: str) -> list[float]:
    response = get_client().embeddings.create(
        input=texto,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding


def obtener_embeddings_batch(textos: list[str]) -> list[list[float]]:
    """Genera embeddings en batch (máximo 2048 por llamada)."""
    all_embeddings = []
    batch_size = 100
    for i in range(0, len(textos), batch_size):
        batch = textos[i:i + batch_size]
        response = get_client().embeddings.create(
            input=batch,
            model=EMBEDDING_MODEL
        )
        all_embeddings.extend([d.embedding for d in response.data])
    return all_embeddings


# =============================================
# 4. INDEXACIÓN FAISS
# =============================================
def construir_indice(chunks: list[dict]) -> faiss.IndexFlatL2 | None:
    """Construye un índice FAISS a partir de los chunks almacenados."""
    if not chunks:
        return None
    embeddings = [c["embedding"] for c in chunks if "embedding" in c]
    if not embeddings:
        return None
    matrix = np.array(embeddings, dtype="float32")
    index = faiss.IndexFlatL2(EMBEDDING_DIM)
    index.add(matrix)
    return index


# =============================================
# 5. RETRIEVAL
# =============================================
def buscar_chunks_similares(pregunta: str, top_k: int = 5) -> list[dict]:
    """Busca los chunks más relevantes para una pregunta."""
    chunks = cargar_chunks()
    if not chunks:
        return []

    index = construir_indice(chunks)
    if index is None:
        return []

    query_emb = np.array([obtener_embedding(pregunta)], dtype="float32")
    k = min(top_k, index.ntotal)
    distances, indices = index.search(query_emb, k)

    resultados = []
    for i, idx in enumerate(indices[0]):
        if idx < len(chunks):
            resultado = {
                "texto": chunks[idx]["texto"],
                "documento": chunks[idx]["documento"],
                "doc_id": chunks[idx]["doc_id"],
                "chunk_index": chunks[idx]["chunk_index"],
                "score": float(distances[0][i])
            }
            resultados.append(resultado)
    return resultados


# =============================================
# 6. GENERACIÓN
# =============================================
def generar_respuesta(pregunta: str, contextos: list[dict]) -> dict:
    """Genera una respuesta usando el contexto recuperado."""
    contexto_texto = "\n\n---\n\n".join(
        f"[Fuente: {c['documento']}]\n{c['texto']}" for c in contextos
    )

    messages = [
        {
            "role": "system",
            "content": (
                "Eres un asistente experto que responde preguntas basándose "
                "únicamente en el contexto proporcionado. Si la información no "
                "está en el contexto, indica que no tienes suficiente información. "
                "Responde en español. Cita las fuentes cuando sea posible."
            )
        },
        {
            "role": "user",
            "content": (
                f"Contexto:\n{contexto_texto}\n\n"
                f"Pregunta: {pregunta}\n\n"
                "Responde basándote únicamente en el contexto proporcionado."
            )
        }
    ]

    response = get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=1000
    )

    return {
        "respuesta": response.choices[0].message.content,
        "modelo": CHAT_MODEL,
        "tokens_usados": response.usage.total_tokens if response.usage else None
    }


# =============================================
# PIPELINE COMPLETO
# =============================================
def procesar_documento(ruta: Path, nombre_original: str) -> dict:
    """Pipeline completo: extraer texto -> chunking -> embeddings -> indexar."""
    # 1. Extraer texto
    texto = extraer_texto(ruta)
    if not texto.strip():
        raise ValueError("No se pudo extraer texto del documento.")

    # 2. Crear registro del documento
    doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
    doc = {
        "doc_id": doc_id,
        "nombre": nombre_original,
        "tipo": ruta.suffix.lower(),
        "tamano": os.path.getsize(ruta),
        "caracteres": len(texto),
        "fecha_carga": datetime.now().isoformat(),
        "estado": "procesando"
    }

    # 3. Chunking
    fragmentos = crear_chunks(texto)

    # 4. Embeddings
    textos_chunks = fragmentos
    embeddings = obtener_embeddings_batch(textos_chunks)

    # 5. Almacenar chunks con embeddings
    chunks_existentes = cargar_chunks()
    nuevos_chunks = []
    for i, (fragmento, embedding) in enumerate(zip(fragmentos, embeddings)):
        chunk = {
            "chunk_id": f"{doc_id}-{i:04d}",
            "doc_id": doc_id,
            "documento": nombre_original,
            "chunk_index": i,
            "texto": fragmento,
            "embedding": embedding
        }
        nuevos_chunks.append(chunk)

    chunks_existentes.extend(nuevos_chunks)
    guardar_chunks(chunks_existentes)

    # 6. Actualizar documento
    doc["num_chunks"] = len(fragmentos)
    doc["estado"] = "indexado"

    docs = cargar_documentos()
    docs.append(doc)
    guardar_documentos(docs)

    return doc


def consultar_rag(pregunta: str, top_k: int = 5) -> dict:
    """Pipeline completo de consulta RAG."""
    # 1. Retrieval
    contextos = buscar_chunks_similares(pregunta, top_k=top_k)

    if not contextos:
        return {
            "pregunta": pregunta,
            "respuesta": "No hay documentos indexados o no se encontró información relevante.",
            "fuentes": [],
            "interaction_id": f"INT-{uuid.uuid4().hex[:8].upper()}"
        }

    # 2. Generación
    resultado = generar_respuesta(pregunta, contextos)

    # 3. Extraer fuentes únicas
    fuentes = list({c["documento"] for c in contextos})

    interaction_id = f"INT-{uuid.uuid4().hex[:8].upper()}"

    return {
        "interaction_id": interaction_id,
        "pregunta": pregunta,
        "respuesta": resultado["respuesta"],
        "fuentes": fuentes,
        "contextos": [
            {"texto": c["texto"][:200] + "...", "documento": c["documento"], "score": c["score"]}
            for c in contextos
        ],
        "modelo": resultado["modelo"],
        "tokens_usados": resultado["tokens_usados"]
    }


# =============================================
# FEEDBACK
# =============================================
def registrar_feedback(interaction_id: str, tipo: str, comentario: str = "") -> dict:
    """Registra feedback (like/dislike/comentario) para una interacción."""
    fb = {
        "feedback_id": f"FB-{uuid.uuid4().hex[:8].upper()}",
        "interaction_id": interaction_id,
        "tipo": tipo,  # "like", "dislike", "comentario"
        "comentario": comentario,
        "fecha": datetime.now().isoformat()
    }
    items = cargar_feedback()
    items.append(fb)
    guardar_feedback(items)
    return fb


def obtener_metricas() -> dict:
    """Calcula métricas de calidad basadas en el feedback."""
    items = cargar_feedback()
    total = len(items)
    likes = sum(1 for f in items if f["tipo"] == "like")
    dislikes = sum(1 for f in items if f["tipo"] == "dislike")
    comentarios = sum(1 for f in items if f["tipo"] == "comentario")

    return {
        "total_interacciones": total,
        "likes": likes,
        "dislikes": dislikes,
        "comentarios": comentarios,
        "tasa_likes": round(likes / total * 100, 1) if total > 0 else 0,
        "tasa_dislikes": round(dislikes / total * 100, 1) if total > 0 else 0,
    }


def eliminar_documento(doc_id: str) -> bool:
    """Elimina un documento y sus chunks."""
    docs = cargar_documentos()
    doc = next((d for d in docs if d["doc_id"] == doc_id), None)
    if not doc:
        return False

    # Eliminar chunks asociados
    chunks = cargar_chunks()
    chunks = [c for c in chunks if c["doc_id"] != doc_id]
    guardar_chunks(chunks)

    # Eliminar documento
    docs = [d for d in docs if d["doc_id"] != doc_id]
    guardar_documentos(docs)

    # Eliminar archivo físico si existe
    archivo = DOCS_DIR / doc["nombre"]
    if archivo.exists():
        archivo.unlink()

    return True
