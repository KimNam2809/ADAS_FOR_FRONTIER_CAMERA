from __future__ import annotations
import os
import platform
import torch


def select_device(requested: str = "auto") -> str:
    """Return an Ultralytics-compatible device without assuming one vendor."""
    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "0"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def can_show_window() -> bool:
    if platform.system() in {"Windows", "Darwin"}:
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def describe_runtime(device: str) -> str:
    gpu = ""
    if torch.cuda.is_available():
        gpu = f", GPU={torch.cuda.get_device_name(0)}"
    return f"OS={platform.system()} {platform.machine()}, PyTorch={torch.__version__}, device={device}{gpu}"
