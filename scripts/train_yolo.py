import argparse
import time
from pathlib import Path
from typing import Any

from backend.app.detection.config import load_detection_config, load_yaml
from backend.app.detection.dataset import validate_yolo_dataset
from backend.app.detection.metadata import collect_experiment_metadata, write_metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a reproducible Ultralytics YOLO model")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--dataset-config", type=Path, default=Path("configs/detection/neu-det.yaml")
    )
    args = parser.parse_args()
    train_config = load_yaml(args.config)
    dataset_config = load_detection_config(args.dataset_config)
    dataset_root = dataset_config.dataset_root
    if not dataset_root.is_dir():
        raise SystemExit(f"Dataset not found: {dataset_root}. Follow data/README.md first.")
    validation = validate_yolo_dataset(dataset_root, dataset_config)
    print(f"Images: {validation.image_count}")
    print(f"Class distribution: {dict(validation.class_distribution)}")
    if not validation.valid:
        raise SystemExit(f"Dataset validation failed: {validation.errors[:10]}")
    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise SystemExit(
            "Ultralytics/PyTorch is not installed. Install a confirmed CUDA-compatible "
            "PyTorch build first; this script will not alter PyTorch automatically."
        ) from error

    model_name = str(train_config.pop("model"))
    metadata_path = Path(str(train_config.pop("metadata_path")))
    train_config["seed"] = int(train_config.get("seed", 42))
    started = time.perf_counter()
    try:
        result = YOLO(model_name).train(**train_config)
    except RuntimeError as error:
        if "out of memory" in str(error).lower():
            raise SystemExit(
                "CUDA OOM: reduce batch/imgsz or use batch=-1; resume from the last checkpoint."
            ) from error
        raise
    duration = time.perf_counter() - started
    metrics: dict[str, Any] = {
        key: float(value) for key, value in getattr(result, "results_dict", {}).items()
    }
    save_dir = Path(str(result.save_dir))
    best_path = save_dir / "weights" / "best.pt"
    metadata_config = dict(train_config)
    metadata_config["model"] = model_name
    metadata_config["dataset_version"] = dataset_config.dataset_version
    metadata = collect_experiment_metadata(metadata_config, metrics, str(best_path), duration)
    write_metadata(metadata, metadata_path)
    print(f"Best model: {best_path}")
    print(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    main()
