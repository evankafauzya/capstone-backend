"""
ArcFace face-recognition backbone — vendored from the original training
notebook (FaceRecog-VGG-ArcFace.ipynb).

The checkpoint shipped under ``models_data/face_recognition_model.pth`` was
produced with this exact module structure:

    features = nn.Sequential(*list(resnet50().children())[:-1])  # drops the FC head
    neck = nn.Sequential(
        nn.Flatten(),
        nn.BatchNorm1d(2048),
        nn.Linear(2048, embedding_dim, bias=False),
        nn.BatchNorm1d(embedding_dim),
    )
    forward(x) -> F.normalize(neck(features(x)), p=2, dim=1)
"""
from __future__ import annotations

import logging
from typing import Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models import resnet50

logger = logging.getLogger(__name__)


class FaceEmbeddingNet(nn.Module):
    """ResNet50 backbone + projection neck -> L2-normalized embedding."""

    def __init__(self, embedding_dim: int = 512):
        super().__init__()
        base = resnet50(weights=None)  # weights loaded from checkpoint
        self.features = nn.Sequential(*list(base.children())[:-1])
        self.neck = nn.Sequential(
            nn.Flatten(),
            nn.BatchNorm1d(2048),
            nn.Linear(2048, embedding_dim, bias=False),
            nn.BatchNorm1d(embedding_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.neck(x)
        return F.normalize(x, p=2, dim=1)


def load_face_embedding_net(
    checkpoint_path: str,
    device: torch.device,
) -> Tuple[FaceEmbeddingNet, dict, dict]:
    """
    Build a FaceEmbeddingNet, load weights with strict=True, and return:
      (model, label_to_name, meta)

    meta contains:
      - embedding_dim
      - img_size
      - num_classes (size of the ArcFace classifier head, if stored)
      - arc_head_weight (the class centers used for identification), if stored
      - best_val_acc
    """
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)

    if not isinstance(ckpt, dict):
        raise ValueError(
            f"Unexpected checkpoint format at {checkpoint_path}: {type(ckpt).__name__}"
        )

    cfg = ckpt.get("config") or {}
    embedding_dim = int(cfg.get("embedding_dim", 512))
    img_size = int(cfg.get("img_size", 112))

    backbone_sd = ckpt.get("backbone")
    if backbone_sd is None:
        raise KeyError(
            f"Checkpoint at {checkpoint_path} has no 'backbone' state_dict"
        )

    model = FaceEmbeddingNet(embedding_dim=embedding_dim)
    model.load_state_dict(backbone_sd, strict=True)
    model.eval().to(device)

    label_to_name = {int(k): v for k, v in (ckpt.get("label_to_name") or {}).items()}

    arc_head_sd = ckpt.get("arc_head") or {}
    arc_weight = arc_head_sd.get("weight")  # shape [num_classes, embedding_dim]

    meta = {
        "embedding_dim": embedding_dim,
        "img_size": img_size,
        "best_val_acc": float(ckpt.get("best_val_acc", 0.0)),
        "num_classes": int(arc_weight.shape[0]) if arc_weight is not None else 0,
        "arc_head_weight": arc_weight,
    }
    logger.info(
        "ArcFace backbone loaded (embedding_dim=%d, num_classes=%d, best_val_acc=%.2f%%)",
        embedding_dim, meta["num_classes"], meta["best_val_acc"] * 100.0,
    )
    return model, label_to_name, meta
