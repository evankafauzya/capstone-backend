"""
Concurrency test for FaceEnrollmentStore.enroll().

enroll() takes a ``BEGIN IMMEDIATE`` write lock so the per-user reference-count
check and the inserts run as one atomic transaction. This test fires many
single-reference enrolls at the limit boundary *simultaneously* and asserts the
store never ends up holding more than MAX_REFERENCES_PER_USER -- i.e. the
check-then-insert cannot be raced past the limit.

Without the lock (plain autocommit) two or more concurrent enrolls could all
read the same pre-limit count, all pass the check, and jointly overshoot.
"""
from __future__ import annotations

import threading

import numpy as np
import pytest

from src.services.face_enrollment import (
    EnrollmentError,
    FaceEnrollmentStore,
    MAX_REFERENCES_PER_USER,
)


def _emb() -> np.ndarray:
    """A unit-norm 512-d embedding (values are irrelevant to this test)."""
    v = np.random.rand(512).astype(np.float32)
    return v / (float(np.linalg.norm(v)) or 1.0)


def _box() -> dict:
    return {"w": 100, "h": 100, "confidence": 0.9}


def test_concurrent_enroll_never_exceeds_limit(tmp_path):
    store = FaceEnrollmentStore(str(tmp_path / "enroll.db"), embedding_dim=512)
    user = "raceuser"

    # More concurrent one-reference enrolls than there are slots.
    attempts = MAX_REFERENCES_PER_USER + 6
    barrier = threading.Barrier(attempts)
    successes: list[int] = []
    failures: list[int] = []
    lock = threading.Lock()

    def worker() -> None:
        barrier.wait()  # release every thread at once to maximise contention
        try:
            store.enroll(user, [_emb()], [_box()], "test")
            with lock:
                successes.append(1)
        except EnrollmentError:
            with lock:
                failures.append(1)

    threads = [threading.Thread(target=worker) for _ in range(attempts)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # The invariant that matters: the store never holds more than the limit,
    # however the enrolls interleaved.
    assert store.count_references(user) == MAX_REFERENCES_PER_USER
    # And exactly the limit's worth succeeded; every extra attempt was rejected.
    assert len(successes) == MAX_REFERENCES_PER_USER
    assert len(failures) == attempts - MAX_REFERENCES_PER_USER


def test_sequential_enroll_up_to_limit_then_rejects(tmp_path):
    """The ordinary path is unchanged: fill to the limit, next enroll rejects."""
    store = FaceEnrollmentStore(str(tmp_path / "seq.db"), embedding_dim=512)
    user = "sequser"

    for _ in range(MAX_REFERENCES_PER_USER):
        store.enroll(user, [_emb()], [_box()], "test")
    assert store.count_references(user) == MAX_REFERENCES_PER_USER

    with pytest.raises(EnrollmentError):
        store.enroll(user, [_emb()], [_box()], "test")
    # The rejected enroll left the count untouched (atomic rollback).
    assert store.count_references(user) == MAX_REFERENCES_PER_USER
