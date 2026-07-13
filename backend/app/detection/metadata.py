import importlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def collect_experiment_metadata(
    config: dict[str, Any], metrics: dict[str, Any], best_model_path: str | None, duration: float
) -> dict[str, Any]:
    """Collect only observed runtime facts; missing values remain explicit."""

    try:
        git_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        git_commit = "unavailable"
    try:
        torch = importlib.import_module("torch")

        torch_version = torch.__version__
        cuda_build = torch.version.cuda
        cuda_available = torch.cuda.is_available()
        device_name = torch.cuda.get_device_name(0) if cuda_available else None
    except ImportError:
        torch_version = "not-installed"
        cuda_build = None
        cuda_available = False
        device_name = None
    return {
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "dataset_version": config.get("dataset_version", "unavailable"),
        "git_commit": git_commit,
        "python_version": sys.version,
        "platform": platform.platform(),
        "torch_version": torch_version,
        "cuda_build": cuda_build,
        "cuda_available": cuda_available,
        "device_name": device_name,
        "training_config": config,
        "best_model_path": best_model_path,
        "training_duration_seconds": round(duration, 3),
        "metrics": metrics,
    }


def write_metadata(metadata: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
