"""
Face enrollment store — persists per-user ArcFace reference embeddings.

Backed by a single SQLite database file. Each user can have up to
``MAX_REFERENCES_PER_USER`` reference photos; the embeddings are stored as
raw float32 bytes (2 KB per 512-d embedding) for compactness.

Schema::

    users(
        user_id TEXT PRIMARY KEY,
        enrolled_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        embedding_dim INTEGER NOT NULL,
        model_backend TEXT NOT NULL
    )

    face_references(
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        added_at TEXT NOT NULL,
        embedding BLOB NOT NULL,
        face_w INTEGER NOT NULL,
        face_h INTEGER NOT NULL,
        face_confidence REAL NOT NULL
    )

Thread-safety: every public method opens a fresh connection in a context
manager, so SQLite's per-process serialization handles concurrent Flask
workers correctly.
"""
from __future__ import annotations

import logging
import os
import re
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

MAX_REFERENCES_PER_USER = 10
USER_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


class EnrollmentError(Exception):
    """Raised for user-facing enrollment problems (validation, limits)."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_user_id(user_id: str) -> str:
    if not isinstance(user_id, str) or not USER_ID_RE.match(user_id):
        raise EnrollmentError(
            "Invalid user_id: must be 1-64 chars of letters, digits, '_' or '-'."
        )
    return user_id


class FaceEnrollmentStore:
    """SQLite-backed store for ArcFace reference embeddings."""

    def __init__(self, db_path: str, embedding_dim: int = 512):
        self.db_path = db_path
        self.embedding_dim = int(embedding_dim)
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        # Reentrant lock — guards table creation against multi-worker races.
        self._init_lock = threading.Lock()
        self._initialize()

    # ---- internals --------------------------------------------------------
    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(
            self.db_path, isolation_level=None, check_same_thread=False
        )
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._init_lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    enrolled_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    embedding_dim INTEGER NOT NULL,
                    model_backend TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS face_references (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL
                        REFERENCES users(user_id) ON DELETE CASCADE,
                    added_at TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    face_w INTEGER NOT NULL,
                    face_h INTEGER NOT NULL,
                    face_confidence REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_face_refs_user
                    ON face_references(user_id);
                """
            )
        logger.info(
            "FaceEnrollmentStore ready (db=%s, embedding_dim=%d)",
            self.db_path, self.embedding_dim,
        )

    # ---- helpers ----------------------------------------------------------
    @staticmethod
    def _emb_to_blob(emb: np.ndarray) -> bytes:
        return np.asarray(emb, dtype=np.float32).tobytes()

    def _blob_to_emb(self, blob: bytes) -> np.ndarray:
        return np.frombuffer(blob, dtype=np.float32).reshape(self.embedding_dim)

    # ---- public API -------------------------------------------------------
    def count_references(self, user_id: str) -> int:
        validate_user_id(user_id)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM face_references WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return int(row[0]) if row else 0

    def get_user_info(self, user_id: str) -> Optional[dict]:
        """Metadata only — does NOT return embedding values."""
        validate_user_id(user_id)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT enrolled_at, updated_at, embedding_dim, model_backend
                FROM users WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            if row is None:
                return None
            refs = conn.execute(
                """
                SELECT id, added_at, face_w, face_h, face_confidence
                FROM face_references WHERE user_id = ? ORDER BY added_at
                """,
                (user_id,),
            ).fetchall()
        return {
            "user_id": user_id,
            "enrolled_at": row[0],
            "updated_at": row[1],
            "embedding_dim": int(row[2]),
            "model_backend": row[3],
            "reference_count": len(refs),
            "references": [
                {
                    "id": r[0],
                    "added_at": r[1],
                    "face_w": int(r[2]),
                    "face_h": int(r[3]),
                    "face_confidence": float(r[4]),
                }
                for r in refs
            ],
        }

    def get_embeddings(self, user_id: str) -> Tuple[List[str], np.ndarray]:
        """Return ``(reference_ids, embeddings)`` for a user.

        ``reference_ids`` is a list of the N reference row IDs; ``embeddings``
        is an ``[N, embedding_dim]`` float32 array aligned to it. Both are
        empty when the user has no enrolled references.
        """
        validate_user_id(user_id)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, embedding FROM face_references "
                "WHERE user_id = ? ORDER BY added_at",
                (user_id,),
            ).fetchall()
        if not rows:
            return [], np.zeros((0, self.embedding_dim), dtype=np.float32)
        ids = [r[0] for r in rows]
        embs = np.stack([self._blob_to_emb(r[1]) for r in rows], axis=0)
        return ids, embs

    def enroll(
        self,
        user_id: str,
        embeddings: List[np.ndarray],
        face_boxes: List[dict],
        model_backend: str,
    ) -> dict:
        """Append ``len(embeddings)`` reference photos for ``user_id``.

        Each ``face_boxes`` entry is a dict with ``w``, ``h``, ``confidence``
        (used purely for diagnostics later).

        Raises :class:`EnrollmentError` if adding would exceed the per-user
        limit.
        """
        validate_user_id(user_id)
        if len(embeddings) != len(face_boxes):
            raise EnrollmentError("embeddings and face_boxes must have the same length")
        for emb in embeddings:
            if emb.shape != (self.embedding_dim,):
                raise EnrollmentError(
                    f"Each embedding must have shape ({self.embedding_dim},); "
                    f"got {emb.shape}."
                )

        now = _utcnow()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT COUNT(*) FROM face_references WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]
            if existing + len(embeddings) > MAX_REFERENCES_PER_USER:
                raise EnrollmentError(
                    f"User '{user_id}' would exceed the limit of "
                    f"{MAX_REFERENCES_PER_USER} references "
                    f"(has {existing}, attempting to add {len(embeddings)})."
                )

            conn.execute(
                """
                INSERT INTO users (user_id, enrolled_at, updated_at,
                                   embedding_dim, model_backend)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    embedding_dim = excluded.embedding_dim,
                    model_backend = excluded.model_backend
                """,
                (user_id, now, now, self.embedding_dim, model_backend),
            )

            new_ids = []
            for emb, box in zip(embeddings, face_boxes):
                ref_id = uuid.uuid4().hex[:12]
                conn.execute(
                    """
                    INSERT INTO face_references
                        (id, user_id, added_at, embedding,
                         face_w, face_h, face_confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ref_id, user_id, now, self._emb_to_blob(emb),
                        int(box.get("w", 0)), int(box.get("h", 0)),
                        float(box.get("confidence", 0.0)),
                    ),
                )
                new_ids.append(ref_id)

        logger.info(
            "Enrolled %d reference(s) for user '%s' (total now %d)",
            len(embeddings), user_id, existing + len(embeddings),
        )
        return {
            "user_id": user_id,
            "added": new_ids,
            "added_count": len(new_ids),
            "total_references": existing + len(embeddings),
        }

    def delete_user(self, user_id: str) -> int:
        """Delete a user and all their references. Returns rows deleted."""
        validate_user_id(user_id)
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        logger.info("Deleted enrollment for user '%s' (rows=%d)", user_id, cur.rowcount)
        return cur.rowcount
