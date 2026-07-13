import argparse
from pathlib import Path

from backend.app.detection import YoloPyTorchDetector


def main() -> None:
    parser = argparse.ArgumentParser(description="Run YOLO on one image or a directory")
    parser.add_argument("input", type=Path)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/detection/inference"))
    parser.add_argument("--device", default="0")
    parser.add_argument("--confidence", type=float, default=0.25)
    args = parser.parse_args()
    detector = YoloPyTorchDetector(args.weights, confidence=args.confidence, device=args.device)
    paths = (
        [args.input]
        if args.input.is_file()
        else sorted(
            path for path in args.input.rglob("*") if path.suffix.lower() in {".jpg", ".png"}
        )
    )
    for result in detector.predict_batch(paths, args.output):
        print(result.model_dump_json())


if __name__ == "__main__":
    main()
