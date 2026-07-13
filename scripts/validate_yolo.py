import argparse
import json
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate YOLO and export observed metrics")
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("configs/detection/dataset.yaml"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/detection/validation"))
    parser.add_argument("--device", default="0")
    parser.add_argument("--split", choices=["train", "val", "test"], default="val")
    args = parser.parse_args()
    if not args.weights.is_file():
        raise SystemExit(f"Weights not found: {args.weights}")
    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise SystemExit("Ultralytics/PyTorch is not installed") from error
    args.output.mkdir(parents=True, exist_ok=True)
    result = YOLO(str(args.weights)).val(
        data=str(args.data),
        device=args.device,
        plots=True,
        project=str(args.output),
        name=args.split,
        exist_ok=True,
        split=args.split,
    )
    save_dir = args.output / args.split
    names = result.names
    maps = result.box.maps.tolist()
    per_class = [
        {"class_id": class_id, "class_name": names[class_id], "map50_95": float(value)}
        for class_id, value in enumerate(maps)
    ]
    summary: dict[str, Any] = {
        "metrics": {key: float(value) for key, value in result.results_dict.items()},
        "split": args.split,
        "per_class": per_class,
        "confusion_matrix": str(save_dir / "confusion_matrix.png"),
        "pr_curve": str(save_dir / "PR_curve.png"),
    }
    output_path = args.output / "validation-summary.json"
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
