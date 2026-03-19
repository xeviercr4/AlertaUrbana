"""FastAPI router exposing all RAG endpoints."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from .document_processor import process_document
from .feedback import FeedbackStore
from .generator import generate_answer
from .models import (
    FeedbackRequest,
    MetricsResponse,
    QueryRequest,
    QueryResponse,
    ChunkResult,
)
from .vector_store import VectorStore

logger = logging.getLogger("alertaurbana.rag")

# ---------------------------------------------------------------------------
# Paths – all RAG data lives inside backend/rag_data/
# ---------------------------------------------------------------------------
_BASE = Path(__file__).resolve().parent.parent  # backend/
RAG_DATA_DIR = _BASE / "rag_data"
DOCS_META_FILE = RAG_DATA_DIR / "documents.json"

# Singletons
_vector_store: VectorStore | None = None
_feedback_store: FeedbackStore | None = None

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}


def _get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(RAG_DATA_DIR / "vector_store")
    return _vector_store


def _get_feedback_store() -> FeedbackStore:
    global _feedback_store
    if _feedback_store is None:
        _feedback_store = FeedbackStore(RAG_DATA_DIR)
    return _feedback_store


# ---------------------------------------------------------------------------
# Document metadata helpers
# ---------------------------------------------------------------------------

def _load_doc_meta() -> list[dict]:
    RAG_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DOCS_META_FILE.exists():
        return []
    with open(DOCS_META_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_doc_meta(docs: list[dict]) -> None:
    RAG_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DOCS_META_FILE, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/upload", summary="Upload and index a document")
async def upload_document(file: UploadFile = File(...)):
    """
    Accept a PDF, DOCX, or TXT file, extract and chunk its text,
    generate embeddings, and store them in the FAISS vector store.
    """
    ext = Path(file.filename).suffix.lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        chunks = process_document(file_bytes, file.filename)
    except Exception as exc:
        logger.exception("Error processing document %s", file.filename)
        raise HTTPException(status_code=422, detail=str(exc))

    if not chunks:
        raise HTTPException(status_code=422, detail="No text could be extracted from the document.")

    doc_id = str(uuid.uuid4())
    vs = _get_vector_store()
    chunk_count = vs.add_document(doc_id, file.filename, chunks)

    meta = {
        "doc_id": doc_id,
        "filename": file.filename,
        "file_type": ext.upper(),
        "chunk_count": chunk_count,
        "uploaded_at": datetime.now().isoformat(),
    }
    docs = _load_doc_meta()
    docs.append(meta)
    _save_doc_meta(docs)

    logger.info("Document indexed: %s (%d chunks)", file.filename, chunk_count)
    return meta


@router.get("/documents", summary="List uploaded documents")
def list_documents():
    """Return metadata for all indexed documents."""
    return _load_doc_meta()


@router.delete("/documents/{doc_id}", summary="Delete a document from the index")
def delete_document(doc_id: str):
    """Remove a document and its embeddings from the vector store."""
    docs = _load_doc_meta()
    remaining = [d for d in docs if d["doc_id"] != doc_id]
    if len(remaining) == len(docs):
        raise HTTPException(status_code=404, detail="Document not found.")

    vs = _get_vector_store()
    vs.remove_document(doc_id)
    _save_doc_meta(remaining)
    return {"detail": "Document deleted successfully.", "doc_id": doc_id}


@router.post("/query", response_model=QueryResponse, summary="Query the RAG system")
def query_rag(req: QueryRequest):
    """
    Retrieve relevant document chunks for the question and generate
    an answer using the LLM.
    """
    vs = _get_vector_store()
    raw_chunks = vs.search(req.question, top_k=req.top_k)

    sources = [
        ChunkResult(
            doc_id=c["doc_id"],
            filename=c["filename"],
            chunk_index=c["chunk_index"],
            text=c["text"],
            score=c["score"],
        )
        for c in raw_chunks
    ]

    answer = generate_answer(req.question, raw_chunks)

    interaction_id = str(uuid.uuid4())
    interaction = {
        "interaction_id": interaction_id,
        "question": req.question,
        "answer": answer,
        "source_count": len(sources),
        "asked_at": datetime.now().isoformat(),
    }
    _get_feedback_store().save_interaction(interaction)

    return QueryResponse(
        interaction_id=interaction_id,
        question=req.question,
        answer=answer,
        sources=sources,
    )


@router.post("/feedback", summary="Submit feedback for a RAG response")
def submit_feedback(req: FeedbackRequest):
    """
    Record a like or dislike (with optional comment) for a specific
    RAG interaction.
    """
    try:
        entry = _get_feedback_store().save_feedback(
            interaction_id=req.interaction_id,
            vote=req.vote,
            comment=req.comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return entry


@router.get("/metrics", response_model=MetricsResponse, summary="Get evaluation metrics")
def get_metrics():
    """Return aggregated metrics: interaction counts, like/dislike ratios, etc."""
    vs = _get_vector_store()
    docs = _load_doc_meta()
    return _get_feedback_store().get_metrics(
        total_chunks=vs.total_chunks,
        total_documents=len(docs),
    )
