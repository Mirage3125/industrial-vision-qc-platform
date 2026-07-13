"""Command-line inference for the OpenCV baseline."""

import argparse
from pathlib import Path

from backend.app.classical_vision import ClassicalVisionDetector, load_classical_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run classical defect detection")
    parser.add_argument("input", type=Path, help="Image file or directory")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/classical_vision/baseline.yaml"),
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/classical_vision"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_classical_config(args.config)
    detector = ClassicalVisionDetector(config)
    if args.input.is_file():
        results = [detector.predict(args.input, args.output)]
    elif args.input.is_dir():
        paths = sorted(
            path
            for path in args.input.rglob("*")
            if path.is_file() and path.suffix.lower() in config.batch_extensions
        )
        results = detector.predict_batch(paths, args.output)
    else:
        raise SystemExit(f"Input does not exist: {args.input}")
    for result in results:
        json_result = result.artifacts.get("json_result")
        print(
            f"{result.image_path}: defects={result.defect_count}, "
            f"latency_ms={result.processing_time_ms:.3f}, json={json_result}"
        )


if __name__ == "__main__":
    main()
