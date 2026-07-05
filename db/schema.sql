-- ============================================================================
-- Moodle Proctoring AI — first-time database install
-- ============================================================================
-- Target:    SQLite (single file, default: data/enrollments.db)
-- Apply:     sqlite3 data/enrollments.db < db/schema.sql
-- Idempotent: every statement uses IF NOT EXISTS, so re-running this file
--             will NOT create duplicate tables, indexes, or columns.
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- 1. Enrolled users (one row per student/staff who has registered a face)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id        TEXT PRIMARY KEY,
    enrolled_at    TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    embedding_dim  INTEGER NOT NULL,
    model_backend  TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- 2. Face reference embeddings (up to MAX_REFERENCES_PER_USER per user)
--    `embedding` is a raw float32 BLOB (2 KB for a 512-d vector).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS face_references (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL
                    REFERENCES users(user_id) ON DELETE CASCADE,
    added_at        TEXT NOT NULL,
    embedding       BLOB NOT NULL,
    face_w          INTEGER NOT NULL,
    face_h          INTEGER NOT NULL,
    face_confidence REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_face_refs_user
    ON face_references(user_id);

-- ---------------------------------------------------------------------------
-- 3. Verification audit log (one row per /verify/face call)
--    NEVER stores image bytes or embeddings — only the decision + score.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS verifications (
    id                  TEXT PRIMARY KEY,
    ts_utc              TEXT NOT NULL,
    user_id             TEXT,
    method              TEXT NOT NULL,
    match_score         REAL NOT NULL,
    threshold           REAL NOT NULL,
    matched             INTEGER NOT NULL,
    references_compared INTEGER NOT NULL,
    best_reference_id   TEXT,
    reason              TEXT,
    recognizer_backend  TEXT,
    detector_backend    TEXT,
    client_ip           TEXT,
    request_id          TEXT
);

CREATE INDEX IF NOT EXISTS idx_verifications_user_ts
    ON verifications(user_id, ts_utc);

CREATE INDEX IF NOT EXISTS idx_verifications_ts
    ON verifications(ts_utc);
