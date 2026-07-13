import argparse
import json
from pathlib import Path

from backend.app.detection import convert_voc_directory, load_detection_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert VOC/XML annotations to YOLO text")
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    result = convert_voc_directory(
        args.images, args.annotations, args.output, load_detection_config(args.config)
    )
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    if not result.valid:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
