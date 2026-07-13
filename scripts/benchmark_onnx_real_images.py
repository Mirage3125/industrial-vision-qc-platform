from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import onnxruntime as ort


def read_images(image_dir: Path, image_size: int, limit: int) -> list[np.ndarray]:
    paths = sorted(
        path
        for path in image_dir.glob("*")
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
    )[:limit]
    if not paths:
        raise RuntimeError(f"No test images found in {image_dir}")
    tensors: list[np.ndarray] = []
    for path in paths:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"Failed to read image: {path}")
        image = cv2.resize(image, (image_size, image_size), interpolation=cv2.INTER_LINEAR)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = image.astype(np.float32) / 255.0
        tensors.append(np.transpose(image, (2, 0, 1)))
    return tensors


def query_gpu_memory_mib() -> float | None:
    try:
        output = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()[0]
        return float(output.strip())
    except (OSError, subprocess.CalledProcessError, IndexError, ValueError):
        return None


def make_batches(images: list[np.ndarray], batch_size: int, count: int) -> list[np.ndarray]:
    return [
        np.stack(
            [images[(index * batch_size + offset) % len(images)] for offset in range(batch_size)],
            axis=0,
        ).astype(np.float32, copy=False)
        for index in range(count)
    ]


def percentile(values: list[float], quantile: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=np.float64), quantile))


def benchmark_provider(
    model_path: Path,
    images: list[np.ndarray],
    provider: str,
    batch_size: int,
    warmup: int,
    iterations: int,
) -> dict[str, Any]:
    requested = (
        ["CPUExecutionProvider"]
        if provider == "CPUExecutionProvider"
        else ["CUDAExecutionProvider", "CPUExecutionProvider"]
    )
    session_started = time.perf_counter()
    session = ort.InferenceSession(str(model_path), providers=requested)
    session_initialization_ms = (time.perf_counter() - session_started) * 1000
    session_providers = session.get_providers()
    if not session_providers or session_providers[0] != provider:
        raise RuntimeError(
            f"{provider} requested but active providers are {session_providers}. "
            "Silent fallback is not allowed."
        )

    input_name = session.get_inputs()[0].name
    warmup_batches = make_batches(images, batch_size, warmup + 1)
    measured_batches = make_batches(images, batch_size, iterations)
    gpu_before = query_gpu_memory_mib()

    first_started = time.perf_counter()
    session.run(None, {input_name: warmup_batches[0]})
    first_inference_ms = (time.perf_counter() - first_started) * 1000

    for batch in warmup_batches[1:]:
        session.run(None, {input_name: batch})

    latencies: list[float] = []
    for batch in measured_batches:
        started = time.perf_counter()
        session.run(None, {input_name: batch})
        latencies.append((time.perf_counter() - started) * 1000)

    gpu_after = query_gpu_memory_mib()
    average = statistics.fmean(latencies)
    return {
        "provider": provider,
        "session_providers": session_providers,
        "batch_size": batch_size,
        "session_initialization_ms": round(session_initialization_ms, 4),
        "first_inference_ms": round(first_inference_ms, 4),
        "warmup_iterations": warmup,
        "measured_iterations": iterations,
        "average_latency_ms": round(average, 4),
        "p50_latency_ms": round(percentile(latencies, 50), 4),
        "p95_latency_ms": round(percentile(latencies, 95), 4),
        "p99_latency_ms": round(percentile(latencies, 99), 4),
        "fps": round(1000 / average, 4) if batch_size == 1 else None,
        "throughput_images_per_second": round(batch_size * 1000 / average, 4),
        "gpu_memory_before_mib": gpu_before,
        "gpu_memory_after_mib": gpu_after,
        "gpu_memory_delta_mib": (
            round(gpu_after - gpu_before, 3)
            if gpu_before is not None and gpu_after is not None
            else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark ONNX Runtime on real images")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--image-limit", type=int, default=32)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--iterations", type=int, default=60)
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[1, 4])
    args = parser.parse_args()

    images = read_images(args.image_dir, args.image_size, args.image_limit)
    results: list[dict[str, Any]] = []
    for batch_size in args.batch_sizes:
        results.append(
            benchmark_provider(
                args.model,
                images,
                "CPUExecutionProvider",
                batch_size,
                args.warmup,
                args.iterations,
            )
        )
        results.append(
            benchmark_provider(
                args.model,
                images,
                "CUDAExecutionProvider",
                batch_size,
                args.warmup,
                args.iterations,
            )
        )

    by_key = {(row["provider"], row["batch_size"]): row for row in results}
    speedups: dict[str, dict[str, float]] = {}
    for batch_size in args.batch_sizes:
        cpu = by_key[("CPUExecutionProvider", batch_size)]
        cuda = by_key[("CUDAExecutionProvider", batch_size)]
        speedups[str(batch_size)] = {
            "latency_speedup_cpu_ms_over_cuda_ms": round(
                cpu["average_latency_ms"] / cuda["average_latency_ms"], 4
            ),
            "throughput_speedup_cuda_over_cpu": round(
                cuda["throughput_images_per_second"] / cpu["throughput_images_per_second"], 4
            ),
        }

    report = {
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "model_path": str(args.model.resolve()),
        "model_size_mib": round(args.model.stat().st_size / 1024**2, 4),
        "image_dir": str(args.image_dir.resolve()),
        "image_count_used": len(images),
        "onnxruntime_version": ort.__version__,
        "available_providers": ort.get_available_providers(),
        "results": results,
        "speedups": speedups,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
