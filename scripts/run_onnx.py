import argparse
from pathlib import Path

from backend.app.inference import OnnxYoloDetector


def main() -> None:
    parser = argparse.ArgumentParser(description="Run YOLO ONNX Runtime inference")
    parser.add_argument("input", type=Path)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--provider", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--classes", nargs="+", required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/onnx/inference"))
    args = parser.parse_args()
    detector = OnnxYoloDetector(args.model, args.classes, provider=args.provider)
    paths = [args.input] if args.input.is_file() else sorted(args.input.glob("*"))
    for result in detector.predict_batch(paths, args.output):
        print(result.model_dump_json())


if __name__ == "__main__":
    main()
