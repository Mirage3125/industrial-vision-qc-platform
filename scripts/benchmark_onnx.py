import argparse
from pathlib import Path

from backend.app.benchmark import benchmark_onnx, write_benchmark_reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark ONNX Runtime after warmup")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--provider", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[1, 4])
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--output", type=Path, default=Path("artifacts/benchmarks"))
    args = parser.parse_args()
    report = benchmark_onnx(
        args.model, args.provider, args.batch_sizes, args.warmup, args.iterations
    )
    json_path, markdown_path = write_benchmark_reports(report, args.output, f"onnx-{args.provider}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {markdown_path}")
    if report["status"] != "available":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
