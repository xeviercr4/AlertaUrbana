"""FAISS-based vector store for RAG chunk embeddings."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
from openai import OpenAI

logger = logging.getLogger("alertaurbana.rag.vector_store")

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


def _get_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text."""
    client = _get_client()
    response = client.embeddings.create(input=text, model=EMBEDDING_MODEL)
    return response.data[0].embedding


class VectorStore:
    """
    Persistent FAISS vector store with associated chunk metadata.

    Storage layout (inside `data_dir`):
        index.faiss  – FAISS flat-L2 index
        chunks.json  – list of {doc_id, filename, chunk_index, text}
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = data_dir / "index.faiss"
        self._chunks_path = data_dir / "chunks.json"
        self._embeddings_path = data_dir / "embeddings.npy"
        self._index: Optional[faiss.Index] = None
        self._chunks: list[dict] = []
        self._embeddings: list[list[float]] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._index_path.exists():
            self._index = faiss.read_index(str(self._index_path))
            logger.info("Loaded FAISS index with %d vectors", self._index.ntotal)
        else:
            self._index = faiss.IndexFlatL2(EMBEDDING_DIM)

        if self._chunks_path.exists():
            with open(self._chunks_path, encoding="utf-8") as f:
                self._chunks = json.load(f)
        else:
            self._chunks = []

        # Load cached embeddings if available
        if self._embeddings_path.exists():
            arr = np.load(str(self._embeddings_path))
            self._embeddings = arr.tolist()

    def _save(self) -> None:
        faiss.write_index(self._index, str(self._index_path))
        with open(self._chunks_path, "w", encoding="utf-8") as f:
            json.dump(self._chunks, f, ensure_ascii=False, indent=2)
        if self._embeddings:
            np.save(str(self._embeddings_path), np.array(self._embeddings, dtype="float32"))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def total_chunks(self) -> int:
        return len(self._chunks)

    def add_document(self, doc_id: str, filename: str, chunks: list[str]) -> int:
        """
        Embed and index all chunks for a document.

        Returns the number of chunks added.
        """
        embeddings = []
        new_meta = []
        for i, chunk in enumerate(chunks):
            emb = get_embedding(chunk)
            embeddings.append(emb)
            new_meta.append(
                {
                    "doc_id": doc_id,
                    "filename": filename,
                    "chunk_index": i,
                    "text": chunk,
                }
            )

        matrix = np.array(embeddings, dtype="float32")
        self._index.add(matrix)
        self._chunks.extend(new_meta)
        self._embeddings.extend(embeddings)
        self._save()
        logger.info("Added %d chunks for doc %s", len(chunks), doc_id)
        return len(chunks)

    def remove_document(self, doc_id: str) -> None:
        """Remove all chunks belonging to doc_id and rebuild the index."""
        kept_indices = [i for i, c in enumerate(self._chunks) if c["doc_id"] != doc_id]
        if len(kept_indices) == len(self._chunks):
            return  # nothing to remove

        # Rebuild index and metadata from cached embeddings (no API calls needed)
        self._index = faiss.IndexFlatL2(EMBEDDING_DIM)
        remaining_chunks = [self._chunks[i] for i in kept_indices]
        remaining_embeddings = [self._embeddings[i] for i in kept_indices] if self._embeddings else []

        if remaining_embeddings:
            matrix = np.array(remaining_embeddings, dtype="float32")
            self._index.add(matrix)

        self._chunks = remaining_chunks
        self._embeddings = remaining_embeddings
        self._save()
        logger.info("Removed chunks for doc %s; %d chunks remain", doc_id, len(self._chunks))

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Retrieve the top-k most relevant chunks for a query.

        Returns list of chunk dicts augmented with 'score' (L2 distance).
        """
        if self._index.ntotal == 0:
            return []

        query_emb = np.array([get_embedding(query)], dtype="float32")
        k = min(top_k, self._index.ntotal)
        distances, indices = self._index.search(query_emb, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self._chunks):
                entry = self._chunks[idx].copy()
                entry["score"] = float(dist)
                results.append(entry)
        return results
