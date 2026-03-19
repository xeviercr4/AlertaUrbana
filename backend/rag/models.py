"""Pydantic models for the RAG system."""
from pydantic import BaseModel
from typing import Optional


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


class FeedbackRequest(BaseModel):
    interaction_id: str
    vote: str  # "like" or "dislike"
    comment: Optional[str] = None


class DocumentMetadata(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    chunk_count: int
    uploaded_at: str


class ChunkResult(BaseModel):
    doc_id: str
    filename: str
    chunk_index: int
    text: str
    score: float


class QueryResponse(BaseModel):
    interaction_id: str
    question: str
    answer: str
    sources: list[ChunkResult]


class MetricsResponse(BaseModel):
    total_interactions: int
    total_likes: int
    total_dislikes: int
    like_ratio: float
    total_documents: int
    total_chunks: int
