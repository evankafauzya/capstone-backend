"""
RetinaFace architecture + inference utilities.

Vendored from https://github.com/biubug6/Pytorch_Retinaface so the saved
checkpoint loads with ``strict=True`` and we can perform face detection
without depending on the original repo.

The checkpoint shipped under ``models_data/face_detection_model.pth`` was
trained with the ``mobilenet0.25`` config:

    {'name': 'mobilenet0.25',
     'min_sizes': [[16, 32], [64, 128], [256, 512]],
     'steps': [8, 16, 32], 'variance': [0.1, 0.2], 'clip': False,
     'in_channel': 32, 'out_channel': 64, 'num_classes': 2}
"""
from __future__ import annotations

from collections import OrderedDict
from itertools import product as _product
from math import ceil
from typing import Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models._utils as _utils


# ---------------------------------------------------------------------------
# Default config (matches the bundled checkpoint)
# ---------------------------------------------------------------------------
CFG_MNET = {
    "name": "mobilenet0.25",
    "min_sizes": [[16, 32], [64, 128], [256, 512]],
    "steps": [8, 16, 32],
    "variance": [0.1, 0.2],
    "clip": False,
    "in_channel": 32,
    "out_channel": 64,
    "return_layers": {"stage1": 1, "stage2": 2, "stage3": 3},
    "num_classes": 2,
}


# ---------------------------------------------------------------------------
# Backbone helpers
# ---------------------------------------------------------------------------
def _conv_bn(inp, oup, stride=1, leaky=0):
    return nn.Sequential(
        nn.Conv2d(inp, oup, 3, stride, 1, bias=False),
        nn.BatchNorm2d(oup),
        nn.LeakyReLU(negative_slope=leaky, inplace=True),
    )


def _conv_bn_no_relu(inp, oup, stride):
    return nn.Sequential(
        nn.Conv2d(inp, oup, 3, stride, 1, bias=False),
        nn.BatchNorm2d(oup),
    )


def _conv_bn1x1(inp, oup, stride, leaky=0):
    return nn.Sequential(
        nn.Conv2d(inp, oup, 1, stride, padding=0, bias=False),
        nn.BatchNorm2d(oup),
        nn.LeakyReLU(negative_slope=leaky, inplace=True),
    )


def _conv_dw(inp, oup, stride, leaky=0.1):
    return nn.Sequential(
        nn.Conv2d(inp, inp, 3, stride, 1, groups=inp, bias=False),
        nn.BatchNorm2d(inp),
        nn.LeakyReLU(negative_slope=leaky, inplace=True),
        nn.Conv2d(inp, oup, 1, 1, 0, bias=False),
        nn.BatchNorm2d(oup),
        nn.LeakyReLU(negative_slope=leaky, inplace=True),
    )


class MobileNetV1(nn.Module):
    def __init__(self):
        super().__init__()
        self.stage1 = nn.Sequential(
            _conv_bn(3, 8, 2, leaky=0.1),
            _conv_dw(8, 16, 1),
            _conv_dw(16, 32, 2),
            _conv_dw(32, 32, 1),
            _conv_dw(32, 64, 2),
            _conv_dw(64, 64, 1),
        )
        self.stage2 = nn.Sequential(
            _conv_dw(64, 128, 2),
            _conv_dw(128, 128, 1),
            _conv_dw(128, 128, 1),
            _conv_dw(128, 128, 1),
            _conv_dw(128, 128, 1),
            _conv_dw(128, 128, 1),
        )
        self.stage3 = nn.Sequential(
            _conv_dw(128, 256, 2),
            _conv_dw(256, 256, 1),
        )
        self.avg = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(256, 1000)

    def forward(self, x):
        x = self.stage1(x)
        x = self.stage2(x)
        x = self.stage3(x)
        x = self.avg(x)
        x = x.view(-1, 256)
        return self.fc(x)


# ---------------------------------------------------------------------------
# FPN + SSH
# ---------------------------------------------------------------------------
class FPN(nn.Module):
    def __init__(self, in_channels_list, out_channels):
        super().__init__()
        leaky = 0.1 if out_channels <= 64 else 0
        self.output1 = _conv_bn1x1(in_channels_list[0], out_channels, stride=1, leaky=leaky)
        self.output2 = _conv_bn1x1(in_channels_list[1], out_channels, stride=1, leaky=leaky)
        self.output3 = _conv_bn1x1(in_channels_list[2], out_channels, stride=1, leaky=leaky)

        self.merge1 = _conv_bn(out_channels, out_channels, leaky=leaky)
        self.merge2 = _conv_bn(out_channels, out_channels, leaky=leaky)

    def forward(self, inputs):
        inputs = list(inputs.values())
        output1 = self.output1(inputs[0])
        output2 = self.output2(inputs[1])
        output3 = self.output3(inputs[2])

        up3 = F.interpolate(output3, size=output2.shape[-2:], mode="nearest")
        output2 = self.merge2(output2 + up3)

        up2 = F.interpolate(output2, size=output1.shape[-2:], mode="nearest")
        output1 = self.merge1(output1 + up2)

        return [output1, output2, output3]


class SSH(nn.Module):
    def __init__(self, in_channel, out_channel):
        super().__init__()
        assert out_channel % 4 == 0
        leaky = 0.1 if out_channel <= 64 else 0

        self.conv3X3 = _conv_bn_no_relu(in_channel, out_channel // 2, stride=1)
        self.conv5X5_1 = _conv_bn(in_channel, out_channel // 4, stride=1, leaky=leaky)
        self.conv5X5_2 = _conv_bn_no_relu(out_channel // 4, out_channel // 4, stride=1)
        self.conv7X7_2 = _conv_bn(out_channel // 4, out_channel // 4, stride=1, leaky=leaky)
        self.conv7x7_3 = _conv_bn_no_relu(out_channel // 4, out_channel // 4, stride=1)

    def forward(self, x):
        c3x3 = self.conv3X3(x)
        c5x5_1 = self.conv5X5_1(x)
        c5x5 = self.conv5X5_2(c5x5_1)
        c7x7_2 = self.conv7X7_2(c5x5_1)
        c7x7 = self.conv7x7_3(c7x7_2)
        return F.relu(torch.cat([c3x3, c5x5, c7x7], dim=1))


# ---------------------------------------------------------------------------
# Heads
# ---------------------------------------------------------------------------
class ClassHead(nn.Module):
    def __init__(self, inchannels=512, num_anchors=3):
        super().__init__()
        self.conv1x1 = nn.Conv2d(inchannels, num_anchors * 2, 1, 1, 0)

    def forward(self, x):
        out = self.conv1x1(x).permute(0, 2, 3, 1).contiguous()
        return out.view(out.shape[0], -1, 2)


class BboxHead(nn.Module):
    def __init__(self, inchannels=512, num_anchors=3):
        super().__init__()
        self.conv1x1 = nn.Conv2d(inchannels, num_anchors * 4, 1, 1, 0)

    def forward(self, x):
        out = self.conv1x1(x).permute(0, 2, 3, 1).contiguous()
        return out.view(out.shape[0], -1, 4)


class LandmarkHead(nn.Module):
    def __init__(self, inchannels=512, num_anchors=3):
        super().__init__()
        self.conv1x1 = nn.Conv2d(inchannels, num_anchors * 10, 1, 1, 0)

    def forward(self, x):
        out = self.conv1x1(x).permute(0, 2, 3, 1).contiguous()
        return out.view(out.shape[0], -1, 10)


# ---------------------------------------------------------------------------
# RetinaFace
# ---------------------------------------------------------------------------
class RetinaFace(nn.Module):
    def __init__(self, cfg=None, phase="test"):
        super().__init__()
        cfg = cfg or CFG_MNET
        self.phase = phase

        if cfg["name"] == "mobilenet0.25":
            backbone = MobileNetV1()
        else:
            raise ValueError(f"Unsupported backbone: {cfg['name']}")

        self.body = _utils.IntermediateLayerGetter(backbone, cfg["return_layers"])

        in2 = cfg["in_channel"]
        in_channels_list = [in2 * 2, in2 * 4, in2 * 8]
        out_channels = cfg["out_channel"]

        self.fpn = FPN(in_channels_list, out_channels)
        self.ssh1 = SSH(out_channels, out_channels)
        self.ssh2 = SSH(out_channels, out_channels)
        self.ssh3 = SSH(out_channels, out_channels)

        self.ClassHead = nn.ModuleList([ClassHead(out_channels, 2) for _ in range(3)])
        self.BboxHead = nn.ModuleList([BboxHead(out_channels, 2) for _ in range(3)])
        self.LandmarkHead = nn.ModuleList([LandmarkHead(out_channels, 2) for _ in range(3)])

    def forward(self, x):
        out = self.body(x)
        fpn = self.fpn(out)
        features = [self.ssh1(fpn[0]), self.ssh2(fpn[1]), self.ssh3(fpn[2])]

        bbox = torch.cat([self.BboxHead[i](f) for i, f in enumerate(features)], dim=1)
        cls = torch.cat([self.ClassHead[i](f) for i, f in enumerate(features)], dim=1)
        ldm = torch.cat([self.LandmarkHead[i](f) for i, f in enumerate(features)], dim=1)

        if self.phase == "train":
            return bbox, cls, ldm
        return bbox, F.softmax(cls, dim=-1), ldm


# ---------------------------------------------------------------------------
# Priors / decode / NMS
# ---------------------------------------------------------------------------
class PriorBox:
    def __init__(self, cfg, image_size: Tuple[int, int]):
        self.min_sizes = cfg["min_sizes"]
        self.steps = cfg["steps"]
        self.clip = cfg["clip"]
        self.image_size = image_size
        self.feature_maps = [
            [ceil(image_size[0] / s), ceil(image_size[1] / s)] for s in self.steps
        ]

    def forward(self) -> torch.Tensor:
        anchors = []
        for k, f in enumerate(self.feature_maps):
            min_sizes = self.min_sizes[k]
            for i, j in _product(range(f[0]), range(f[1])):
                for min_size in min_sizes:
                    s_kx = min_size / self.image_size[1]
                    s_ky = min_size / self.image_size[0]
                    cx = (j + 0.5) * self.steps[k] / self.image_size[1]
                    cy = (i + 0.5) * self.steps[k] / self.image_size[0]
                    anchors.extend([cx, cy, s_kx, s_ky])

        out = torch.tensor(anchors).view(-1, 4)
        if self.clip:
            out.clamp_(max=1, min=0)
        return out


def decode_boxes(loc: torch.Tensor, priors: torch.Tensor, variances) -> torch.Tensor:
    boxes = torch.cat((
        priors[:, :2] + loc[:, :2] * variances[0] * priors[:, 2:],
        priors[:, 2:] * torch.exp(loc[:, 2:] * variances[1]),
    ), dim=1)
    boxes[:, :2] -= boxes[:, 2:] / 2
    boxes[:, 2:] += boxes[:, :2]
    return boxes


def decode_landms(pre: torch.Tensor, priors: torch.Tensor, variances) -> torch.Tensor:
    return torch.cat((
        priors[:, :2] + pre[:, 0:2] * variances[0] * priors[:, 2:],
        priors[:, :2] + pre[:, 2:4] * variances[0] * priors[:, 2:],
        priors[:, :2] + pre[:, 4:6] * variances[0] * priors[:, 2:],
        priors[:, :2] + pre[:, 6:8] * variances[0] * priors[:, 2:],
        priors[:, :2] + pre[:, 8:10] * variances[0] * priors[:, 2:],
    ), dim=1)


def py_cpu_nms(dets: np.ndarray, thresh: float):
    x1, y1, x2, y2, scores = dets[:, 0], dets[:, 1], dets[:, 2], dets[:, 3], dets[:, 4]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter)
        order = order[np.where(ovr <= thresh)[0] + 1]
    return keep


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------
def _strip_module_prefix(state_dict):
    """Remove the 'module.' prefix saved by DataParallel."""
    out = OrderedDict()
    for k, v in state_dict.items():
        out[k[7:] if k.startswith("module.") else k] = v
    return out


def load_retinaface(checkpoint_path: str, device: torch.device) -> Tuple[RetinaFace, dict]:
    """Build a RetinaFace and load weights with strict=True.

    Returns (model, cfg).
    """
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)

    if isinstance(ckpt, dict):
        cfg = ckpt.get("cfg") or CFG_MNET
        for key in ("model_state", "state_dict", "model_state_dict"):
            if key in ckpt:
                state_dict = ckpt[key]
                break
        else:
            state_dict = ckpt
    else:
        cfg = CFG_MNET
        state_dict = ckpt

    cfg = dict(cfg)
    cfg.setdefault("return_layers", CFG_MNET["return_layers"])

    model = RetinaFace(cfg=cfg, phase="test")
    model.load_state_dict(_strip_module_prefix(state_dict), strict=True)
    model.eval().to(device)
    return model, cfg
