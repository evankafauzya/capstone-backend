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
from torchvision.models import efficientnet_b0, resnet50

from ._torch_load import safe_torch_load

logger = logging.getLogger(__name__)

# Map of supported backbones -> (factory function, feature dim after avgpool).
# Both backbones share the same ``features + avgpool`` slicing pattern: take
# everything except the final classification head, then feed through the neck.
_BACKBONES = {
    "resnet50":        (resnet50, 2048),
    "efficientnet_b0": (efficientnet_b0, 1280),
}


class FaceEmbeddingNet(nn.Module):
    """Backbone + projection neck -> L2-normalized embedding.

    Two backbones are supported, each with a slightly different ``features`` /
    ``neck`` layout that matches how the training notebooks were written:

    * ``resnet50``:        ``features = list(base.children())[:-1]`` (includes
      avgpool), and ``neck.0`` is just a Flatten.
    * ``efficientnet_b0``: ``features = base.features`` (no avgpool), and
      ``neck.0`` is a Sequential(AdaptiveAvgPool2d, Flatten) that reshapes
      the 4D feature map to 2D before the BN/Linear chain.

    Both end in: BN(feature_dim) -> Linear(feature_dim, embedding_dim) ->
    BN(embedding_dim) -> L2 normalize.
    """

    def __init__(self, embedding_dim: int = 512, backbone_arch: str = "resnet50"):
        super().__init__()
        if backbone_arch not in _BACKBONES:
            raise ValueError(
                f"Unsupported backbone_arch '{backbone_arch}'. "
                f"Choose one of {sorted(_BACKBONES)}."
            )
        factory, feature_dim = _BACKBONES[backbone_arch]
        base = factory(weights=None)  # weights loaded from checkpoint

        if backbone_arch == "resnet50":
            self.features = nn.Sequential(*list(base.children())[:-1])
            pool_then_flatten: nn.Module = nn.Flatten()
        elif backbone_arch == "efficientnet_b0":
            self.features = base.features
            pool_then_flatten = nn.Sequential(
                nn.AdaptiveAvgPool2d(1),
                nn.Flatten(),
            )
        else:
            raise AssertionError(f"unreachable: {backbone_arch}")

        self.backbone_arch = backbone_arch
        self.feature_dim = feature_dim
        self.neck = nn.Sequential(
            pool_then_flatten,
            nn.BatchNorm1d(feature_dim),
            nn.Linear(feature_dim, embedding_dim, bias=False),
            nn.BatchNorm1d(embedding_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.neck(x)
        return F.normalize(x, p=2, dim=1)


def _detect_backbone(backbone_sd: dict) -> str:
    """Infer which backbone produced this state_dict by looking at the neck.

    ``neck.2.weight`` is the projection Linear -- its second dim is the
    backbone's feature dim. 2048 = ResNet50, 1280 = EfficientNet-B0.
    """
    w = backbone_sd.get("neck.2.weight")
    if w is None:
        return "resnet50"  # legacy default
    in_features = int(w.shape[1])
    for name, (_factory, dim) in _BACKBONES.items():
        if dim == in_features:
            return name
    raise ValueError(
        f"Unrecognized projection input dim {in_features}. "
        f"Known: {[d for _, d in _BACKBONES.values()]}"
    )


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
    ckpt = safe_torch_load(checkpoint_path, map_location=device)

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

    backbone_arch = cfg.get("backbone") or _detect_backbone(backbone_sd)
    model = FaceEmbeddingNet(
        embedding_dim=embedding_dim, backbone_arch=backbone_arch,
    )
    model.load_state_dict(backbone_sd, strict=True)
    model.eval().to(device)

    label_to_name = {int(k): v for k, v in (ckpt.get("label_to_name") or {}).items()}

    arc_head_sd = ckpt.get("arc_head") or {}
    arc_weight = arc_head_sd.get("weight")  # shape [num_classes, embedding_dim]

    meta = {
        "embedding_dim": embedding_dim,
        "img_size": img_size,
        "best_val_acc": float(ckpt.get("best_val_acc") or 0.0),
        "num_classes": int(arc_weight.shape[0]) if arc_weight is not None else 0,
        "arc_head_weight": arc_weight,
        "backbone_arch": backbone_arch,
    }
    logger.info(
        "ArcFace backbone loaded (arch=%s, embedding_dim=%d, num_classes=%d, "
        "best_val_acc=%.2f%%)",
        backbone_arch, embedding_dim, meta["num_classes"],
        meta["best_val_acc"] * 100.0,
    )
    return model, label_to_name, meta
