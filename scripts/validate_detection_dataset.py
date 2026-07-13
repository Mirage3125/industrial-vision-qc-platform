import argparse
import json
from pathlib import Path

from backend.app.detection import load_detection_config, validate_yolo_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate YOLO labels and split leakage")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate_yolo_dataset(args.dataset, load_detection_config(args.config))
    payload = json.dumps(result.as_dict(), ensure_ascii=False, indent=2)
    print(payload)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    if not result.valid:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
