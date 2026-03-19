"""Feedback storage and evaluation metrics for the RAG system."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("alertaurbana.rag.feedback")


class FeedbackStore:
    """
    Stores user feedback (like/dislike + optional comment) in a JSON file
    and computes simple evaluation metrics.
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._path = data_dir / "feedback.json"
        self._interactions_path = data_dir / "interactions.json"

    # ------------------------------------------------------------------
    # Feedback
    # ------------------------------------------------------------------

    def _load_feedback(self) -> list[dict]:
        if not self._path.exists():
            return []
        with open(self._path, encoding="utf-8") as f:
            return json.load(f)

    def save_feedback(
        self,
        interaction_id: str,
        vote: str,
        comment: str | None = None,
    ) -> dict:
        """Persist a feedback entry and return it."""
        if vote not in ("like", "dislike"):
            raise ValueError("vote must be 'like' or 'dislike'")

        feedback_list = self._load_feedback()
        entry = {
            "interaction_id": interaction_id,
            "vote": vote,
            "comment": comment,
            "recorded_at": datetime.now().isoformat(),
        }
        feedback_list.append(entry)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(feedback_list, f, ensure_ascii=False, indent=2)
        logger.info("Feedback saved: %s → %s", interaction_id, vote)
        return entry

    # ------------------------------------------------------------------
    # Interactions (question + answer log)
    # ------------------------------------------------------------------

    def _load_interactions(self) -> list[dict]:
        if not self._interactions_path.exists():
            return []
        with open(self._interactions_path, encoding="utf-8") as f:
            return json.load(f)

    def save_interaction(self, interaction: dict) -> None:
        """Persist a Q&A interaction."""
        interactions = self._load_interactions()
        interactions.append(interaction)
        with open(self._interactions_path, "w", encoding="utf-8") as f:
            json.dump(interactions, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self, total_chunks: int, total_documents: int) -> dict:
        """Compute and return evaluation metrics."""
        feedback_list = self._load_feedback()
        interactions = self._load_interactions()

        likes = sum(1 for f in feedback_list if f["vote"] == "like")
        dislikes = sum(1 for f in feedback_list if f["vote"] == "dislike")
        total_votes = likes + dislikes
        like_ratio = round(likes / total_votes, 2) if total_votes > 0 else 0.0

        return {
            "total_interactions": len(interactions),
            "total_likes": likes,
            "total_dislikes": dislikes,
            "like_ratio": like_ratio,
            "total_documents": total_documents,
            "total_chunks": total_chunks,
        }
