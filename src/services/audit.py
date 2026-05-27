"""
Verification audit log.

Every call to ``/verify/face`` writes one row to the ``verifications`` table:
when it happened, who was checked, what score came back, whether it was a
match, which method (single-reference vs user_id mode), and which references
were compared. This is the trail an institution needs when an exam result
is disputed (BAN-PT, ABET, internal student affairs review).

Stored in the same SQLite DB as enrollments so backups capture both, but
in a separate table.

Schema::

    verifications(
        id TEXT PRIMARY KEY,         -- short uuid
        ts_utc TEXT NOT NULL,        -- ISO-8601 UTC timestamp
        user_id TEXT,                -- nullable: legacy single-reference mode
        method TEXT NOT NULL,        -- 'user_id' | 'reference_face' | 'no_face'
        match_score REAL NOT NULL,
        threshold REAL NOT NULL,
        matched INTEGER NOT NULL,    -- 0/1
        references_compared INTEGER NOT NULL,
        best_reference_id TEXT,
        reason TEXT,                 -- e.g. 'no_face_in_current_frame'
        recognizer_backend TEXT,
        detector_backend TEXT,
        client_ip TEXT,
        request_id TEXT
    )

Privacy notes:
  * No image bytes, no face crops, no embedding values are stored. Only the
    aggregate score, the reference id, and the decision.
  * ``client_ip`` is included because regulators usually want it; institutions
    that consider that PII can strip it via a future migration.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class VerificationAuditStore:
    """SQLite-backed audit log of every ``/verify/face`` call."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_lock = threading.Lock()
        self._initialize()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(
            self.db_path, isolation_level=None, check_same_thread=False,
        )
        try:
            yield conn
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._init_lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS verifications (
                    id TEXT PRIMARY KEY,
                    ts_utc TEXT NOT NULL,
                    user_id TEXT,
                    method TEXT NOT NULL,
                    match_score REAL NOT NULL,
                    threshold REAL NOT NULL,
                    matched INTEGER NOT NULL,
                    references_compared INTEGER NOT NULL,
                    best_reference_id TEXT,
                    reason TEXT,
                    recognizer_backend TEXT,
                    detector_backend TEXT,
                    client_ip TEXT,
                    request_id TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_verifications_user_ts
                    ON verifications(user_id, ts_utc);

                CREATE INDEX IF NOT EXISTS idx_verifications_ts
                    ON verifications(ts_utc);
                """
            )
        logger.info("VerificationAuditStore ready (db=%s)", self.db_path)

    # ------------------------------------------------------------------ writes
    def record(
        self,
        *,
        user_id: Optional[str],
        method: str,
        match_score: float,
        threshold: float,
        matched: bool,
        references_compared: int = 0,
        best_reference_id: Optional[str] = None,
        reason: Optional[str] = None,
        recognizer_backend: Optional[str] = None,
        detector_backend: Optional[str] = None,
        client_ip: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> str:
        """Insert one audit row. Returns the new row's ID."""
        audit_id = uuid.uuid4().hex[:12]
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO verifications
                  (id, ts_utc, user_id, method, match_score, threshold, matched,
                   references_compared, best_reference_id, reason,
                   recognizer_backend, detector_backend, client_ip, request_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id, _utcnow(), user_id, method,
                    float(match_score), float(threshold), 1 if matched else 0,
                    int(references_compared), best_reference_id, reason,
                    recognizer_backend, detector_backend, client_ip, request_id,
                ),
            )
        return audit_id

    # ------------------------------------------------------------------ reads
    def for_user(self, user_id: str, limit: int = 100) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, ts_utc, user_id, method, match_score, threshold,
                       matched, references_compared, best_reference_id,
                       reason, recognizer_backend, detector_backend, client_ip,
                       request_id
                FROM verifications
                WHERE user_id = ?
                ORDER BY ts_utc DESC
                LIMIT ?
                """,
                (user_id, int(limit)),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def recent(self, limit: int = 100) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, ts_utc, user_id, method, match_score, threshold,
                       matched, references_compared, best_reference_id,
                       reason, recognizer_backend, detector_backend, client_ip,
                       request_id
                FROM verifications ORDER BY ts_utc DESC LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]


def _row_to_dict(r: tuple) -> dict:
    return {
        "id": r[0],
        "ts_utc": r[1],
        "user_id": r[2],
        "method": r[3],
        "match_score": float(r[4]),
        "threshold": float(r[5]),
        "matched": bool(r[6]),
        "references_compared": int(r[7]),
        "best_reference_id": r[8],
        "reason": r[9],
        "recognizer_backend": r[10],
        "detector_backend": r[11],
        "client_ip": r[12],
        "request_id": r[13],
    }
