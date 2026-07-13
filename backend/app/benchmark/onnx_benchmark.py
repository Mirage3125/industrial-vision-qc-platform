from __future__ import annotations

import json
import statistics
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
import psutil


def percentile(values: list[float], quantile: float) -> float:
    return float(np.percentile(np.asarray(values), quantile))


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


def benchmark_onnx(
    model_path: Path, provider: str, batch_sizes: list[int], warmup: int, iterations: int
) -> dict[str, Any]:
    provider_names = {
        "cpu": ["CPUExecutionProvider"],
        "cuda": ["CUDAExecutionProvider", "CPUExecutionProvider"],
    }
    requested = provider_names[provider]
    session_started = time.perf_counter()
    session = ort.InferenceSession(str(model_path), providers=requested)
    session_initialization_ms = (time.perf_counter() - session_started) * 1000
    actual_provider = session.get_providers()[0]
    if actual_provider != requested[0]:
        return {
            "status": "unavailable",
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "model_path": str(model_path.resolve()),
            "model_size_mib": round(model_path.stat().st_size / 1024**2, 4),
            "requested_provider": requested[0],
            "actual_provider": actual_provider,
            "session_initialization_ms": round(session_initialization_ms, 4),
            "error": "Requested provider failed to load and ONNX Runtime fell back to CPU",
            "results": [],
        }
    input_meta = session.get_inputs()[0]
    process = psutil.Process()
    reports: list[dict[str, Any]] = []
    for batch_size in batch_sizes:
        shape = [batch_size]
        for dimension in input_meta.shape[1:]:
            shape.append(int(dimension) if isinstance(dimension, int) else 640)
        tensor = np.random.default_rng(42).random(shape, dtype=np.float32)
        gpu_before = query_gpu_memory_mib()
        memory_before = process.memory_info().rss / 1024**2
        first_started = time.perf_counter()
        session.run(None, {input_meta.name: tensor})
        first_inference_ms = (time.perf_counter() - first_started) * 1000
        for _ in range(warmup):
            session.run(None, {input_meta.name: tensor})
        latencies: list[float] = []
        for _ in range(iterations):
            started = time.perf_counter()
            session.run(None, {input_meta.name: tensor})
            latencies.append((time.perf_counter() - started) * 1000)
        memory_after = process.memory_info().rss / 1024**2
        gpu_after = query_gpu_memory_mib()
        average = statistics.fmean(latencies)
        reports.append(
            {
                "batch_size": batch_size,
                "first_inference_ms": round(first_inference_ms, 4),
                "warmup_iterations": warmup,
                "measured_iterations": iterations,
                "average_latency_ms": round(average, 4),
                "p50_latency_ms": round(percentile(latencies, 50), 4),
                "p95_latency_ms": round(percentile(latencies, 95), 4),
                "p99_latency_ms": round(percentile(latencies, 99), 4),
                "fps": round(1000 / average, 4) if batch_size == 1 else None,
                "throughput_images_per_second": round(batch_size * 1000 / average, 4),
                "process_memory_delta_mib": round(memory_after - memory_before, 3),
                "gpu_memory_before_mib": gpu_before,
                "gpu_memory_after_mib": gpu_after,
                "gpu_memory_delta_mib": (
                    round(gpu_after - gpu_before, 3)
                    if gpu_before is not None and gpu_after is not None
                    else None
                ),
            }
        )
    return {
        "status": "available",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "model_path": str(model_path.resolve()),
        "model_size_mib": round(model_path.stat().st_size / 1024**2, 4),
        "requested_provider": requested[0],
        "actual_provider": actual_provider,
        "session_initialization_ms": round(session_initialization_ms, 4),
        "results": reports,
    }


def write_benchmark_reports(
    report: dict[str, Any], output_dir: Path, name: str
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = output_dir / f"{name}.json", output_dir / f"{name}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = "\n".join(
        "| {batch_size} | {first_inference_ms} | {average_latency_ms} | {p50_latency_ms} | "
        "{p95_latency_ms} | {p99_latency_ms} | {fps} | {throughput_images_per_second} |".format(
            **row
        )
        for row in report["results"]
    )
    markdown = f"""# ONNX Runtime Benchmark

- Model: `{report['model_path']}`
- Model size: {report['model_size_mib']} MiB
- Requested provider: {report['requested_provider']}
- Actual provider: {report['actual_provider']}
- Session initialization: {report['session_initialization_ms']} ms
- Status: {report['status']}
- Error: {report.get('error')}

| Batch | First ms | Mean ms | P50 ms | P95 ms | P99 ms | FPS | Throughput img/s |
|---:|---:|---:|---:|---:|---:|---:|---:|
{rows}

Cold session initialization and first inference are reported separately.
Timed latency excludes warmup.
"""
    markdown_path.write_text(markdown, encoding="utf-8")
    return json_path, markdown_path
