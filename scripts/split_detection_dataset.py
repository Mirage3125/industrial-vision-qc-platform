import argparse
import json
from pathlib import Path

from backend.app.detection import split_yolo_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a deterministic YOLO train/val split")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    counts = split_yolo_dataset(args.source, args.output, args.val_ratio, args.seed)
    print(json.dumps({"seed": args.seed, "counts": counts}, indent=2))


if __name__ == "__main__":
    main()
