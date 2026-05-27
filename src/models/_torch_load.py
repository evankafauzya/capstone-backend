"""
Safer ``torch.load`` wrapper.

``torch.load(..., weights_only=False)`` runs the full pickle protocol, which
means a maliciously crafted ``.pth`` can execute arbitrary Python at load
time. PyTorch 2.4+ supports ``weights_only=True`` -- it allows only a
strict allowlist of tensor/built-in types and refuses everything else.

Some of our checkpoints contain extra metadata (config dicts, label_to_name
dicts, optimizer state) that may include objects not on the allowlist. So
we try ``weights_only=True`` first; if it raises, we log a single warning
and fall back to the legacy behavior. This way we get the security
hardening for free on clean checkpoints and stay compatible with older
ones produced by the original training scripts.
"""
from __future__ import annotations

import logging
from typing import Any

import torch

logger = logging.getLogger(__name__)


def safe_torch_load(checkpoint_path: str, map_location: Any = "cpu") -> Any:
    try:
        return torch.load(
            checkpoint_path, map_location=map_location, weights_only=True,
        )
    except Exception as exc:
        logger.warning(
            "torch.load(weights_only=True) failed for %s (%s); "
            "falling back to weights_only=False. Only load files you trust.",
            checkpoint_path, type(exc).__name__,
        )
        return torch.load(
            checkpoint_path, map_location=map_location, weights_only=False,
        )
