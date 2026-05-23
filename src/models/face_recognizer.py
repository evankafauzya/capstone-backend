"""
Face recognizer — wraps the ArcFace backbone with face alignment and
cosine-similarity-based comparison / identification.

Pipeline:
  1. Crop the face from the BGR image (using a RetinaFace bbox + landmarks).
  2. Resize to ``img_size`` (default 112).
  3. Normalize with mean = std = 0.5 — exactly the recipe the training
     notebook used (``TF.normalize(t, mean=[0.5]*3, std=[0.5]*3)``).
  4. Forward through the backbone -> 512-d L2-normalized embedding.
  5. Compare with cosine similarity (which equals the dot product for
     L2-normalized vectors).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from .arcface import FaceEmbeddingNet, load_face_embedding_net
from .face_aligner import FaceAligner

logger = logging.getLogger(__name__)


def _crop_face(image_bgr: np.ndarray, face: dict) -> Optional[np.ndarray]:
    """Crop the face box from a BGR frame. Returns None on a bad box."""
    x, y, w, h = face["x"], face["y"], face["w"], face["h"]
    H, W = image_bgr.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(W, x + w), min(H, y + h)
    if x2 <= x1 or y2 <= y1:
        return None
    return image_bgr[y1:y2, x1:x2]


class FaceRecognizer:
    """Run the trained ArcFace backbone over face crops."""

    def __init__(
        self,
        checkpoint_path: str,
        device: Optional[torch.device] = None,
        match_threshold: float = 0.5,
        unknown_threshold: float = 0.5,
        enable_alignment: bool = True,
    ):
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.match_threshold = float(match_threshold)
        self.unknown_threshold = float(unknown_threshold)

        self.model, self.label_to_name, self.meta = load_face_embedding_net(
            checkpoint_path, self.device
        )
        self.img_size = self.meta["img_size"]
        self.embedding_dim = self.meta["embedding_dim"]

        # Face alignment is the single biggest accuracy improvement for
        # ArcFace. We try to align every crop; if MediaPipe FaceMesh cannot
        # find a face inside the crop we transparently fall back to a plain
        # resize so the API never breaks.
        self.aligner: Optional[FaceAligner] = None
        if enable_alignment:
            try:
                self.aligner = FaceAligner(output_size=self.img_size)
            except Exception:
                logger.exception(
                    "Failed to initialize FaceAligner — falling back to "
                    "unaligned crops. Verification accuracy will be lower."
                )
                self.aligner = None
        # Counters surfaced via /api/proctoring/system-info for diagnostics.
        self.alignment_stats = {"aligned": 0, "fallback": 0}

        # Class centers used for top-1 identification (optional — only present
        # if the checkpoint includes the ArcFace head weights).
        arc_w = self.meta.get("arc_head_weight")
        if arc_w is not None:
            with torch.no_grad():
                self.class_centers = F.normalize(arc_w.to(self.device), p=2, dim=1)
        else:
            self.class_centers = None

        logger.info(
            "FaceRecognizer ready (img_size=%d, embedding_dim=%d, identities=%d)",
            self.img_size, self.embedding_dim, len(self.label_to_name),
        )

    # ---- preprocessing ----------------------------------------------------
    def _preprocess(self, face_bgr: np.ndarray) -> torch.Tensor:
        aligned = None
        if self.aligner is not None:
            try:
                aligned = self.aligner.align(face_bgr)
            except Exception:
                logger.exception("Aligner crashed; falling back to plain resize.")
                aligned = None

        if aligned is not None:
            bgr = aligned
            self.alignment_stats["aligned"] += 1
        else:
            bgr = cv2.resize(
                face_bgr, (self.img_size, self.img_size),
                interpolation=cv2.INTER_LINEAR,
            )
            self.alignment_stats["fallback"] += 1

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        t = torch.from_numpy(rgb).float() / 255.0
        t = (t - 0.5) / 0.5
        t = t.permute(2, 0, 1).unsqueeze(0)
        return t.to(self.device)

    # ---- public API -------------------------------------------------------
    @torch.no_grad()
    def embed_face(self, face_bgr: np.ndarray) -> np.ndarray:
        """Return a single 512-d L2-normalized embedding for a face crop."""
        tensor = self._preprocess(face_bgr)
        emb = self.model(tensor)
        return emb.squeeze(0).cpu().numpy()

    @torch.no_grad()
    def embed_faces(self, faces_bgr: List[np.ndarray]) -> np.ndarray:
        """Batch version of embed_face. Returns shape [N, embedding_dim]."""
        if not faces_bgr:
            return np.zeros((0, self.embedding_dim), dtype=np.float32)
        batch = torch.cat([self._preprocess(f) for f in faces_bgr], dim=0)
        emb = self.model(batch)
        return emb.cpu().numpy()

    def cosine_similarity(self, emb_a: np.ndarray, emb_b: np.ndarray) -> float:
        a = np.asarray(emb_a, dtype=np.float32).reshape(-1)
        b = np.asarray(emb_b, dtype=np.float32).reshape(-1)
        denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
        return float(np.dot(a, b) / denom)

    def verify(
        self,
        face_a_bgr: np.ndarray,
        face_b_bgr: np.ndarray,
        threshold: Optional[float] = None,
    ) -> dict:
        """Compare two face crops. Returns a verification payload."""
        emb_a = self.embed_face(face_a_bgr)
        emb_b = self.embed_face(face_b_bgr)
        score = self.cosine_similarity(emb_a, emb_b)
        thresh = self.match_threshold if threshold is None else float(threshold)
        return {
            "is_match": score >= thresh,
            "match_score": score,
            "threshold_used": thresh,
        }

    @torch.no_grad()
    def identify(self, face_bgr: np.ndarray, threshold: Optional[float] = None) -> dict:
        """Top-1 identification against the trained class centers.

        Returns {"name": "...", "label": int|None, "score": float} where
        ``name`` is "Unknown" if the best score falls below ``unknown_threshold``.
        """
        if self.class_centers is None:
            return {"name": "Unknown", "label": None, "score": 0.0,
                    "reason": "no_arc_head_in_checkpoint"}

        tensor = self._preprocess(face_bgr)
        emb = self.model(tensor)
        scores = F.linear(emb, self.class_centers).squeeze(0)
        best_score, best_idx = scores.max(dim=0)
        score = float(best_score.item())
        label = int(best_idx.item())
        thresh = self.unknown_threshold if threshold is None else float(threshold)
        name = self.label_to_name.get(label, "Unknown") if score >= thresh else "Unknown"
        return {"name": name, "label": label if name != "Unknown" else None,
                "score": score, "threshold_used": thresh}
