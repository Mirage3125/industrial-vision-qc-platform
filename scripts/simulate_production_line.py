from __future__ import annotations

import argparse
import base64
import hashlib
import json
import statistics
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


@dataclass(frozen=True)
class ImageJob:
    path: Path
    idempotency_key: str


class ProgressStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.state: dict[str, Any] = {"processed": {}, "failures": {}}
        if path.is_file():
            self.state = json.loads(path.read_text(encoding="utf-8"))

    def is_done(self, key: str) -> bool:
        return key in self.state.get("processed", {})

    def record_success(self, key: str, payload: dict[str, Any]) -> None:
        with self.lock:
            self.state.setdefault("processed", {})[key] = payload
            self._write()

    def record_failure(self, key: str, payload: dict[str, Any]) -> None:
        with self.lock:
            self.state.setdefault("failures", {})[key] = payload
            self._write()

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)


def stable_key(path: Path, batch_id: str) -> str:
    stat = path.stat()
    raw = f"{batch_id}|{path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}".encode()
    return "sim-" + hashlib.sha256(raw).hexdigest()[:32]


def iter_images(input_dir: Path, batch_id: str) -> list[ImageJob]:
    images = sorted(path for path in input_dir.rglob("*") if path.suffix.lower() in IMAGE_SUFFIXES)
    return [ImageJob(path=path, idempotency_key=stable_key(path, batch_id)) for path in images]


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
    return round(ordered[index], 3)


def post_json(api_url: str, path: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        api_url.rstrip("/") + path,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def send_job(
    job: ImageJob,
    api_url: str,
    mode: str,
    station_id: str,
    batch_id: str,
    timeout: float,
    retries: int,
    backoff_seconds: float,
) -> dict[str, Any]:
    payload = {
        "filename": job.path.name,
        "content_base64": base64.b64encode(job.path.read_bytes()).decode("ascii"),
        "inference_mode": mode,
        "station_id": station_id,
        "batch_id": batch_id,
        "idempotency_key": job.idempotency_key,
    }
    started = time.perf_counter()
    attempt = 0
    while True:
        try:
            response = post_json(api_url, "/api/v1/inspection/upload-predict", payload, timeout)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
            if not response.get("success"):
                raise RuntimeError(json.dumps(response.get("error"), ensure_ascii=False))
            data = response["data"]
            return {
                "ok": True,
                "image_path": str(job.path),
                "idempotency_key": job.idempotency_key,
                "attempts": attempt + 1,
                "elapsed_ms": elapsed_ms,
                "inspection_id": data.get("inspection_id"),
                "review_id": data.get("review_id"),
                "final_status": data.get("final_status"),
                "requires_review": data.get("requires_review"),
                "idempotent": data.get("idempotent", False),
            }
        except (OSError, urllib.error.URLError, TimeoutError, RuntimeError) as error:
            if attempt >= retries:
                return {
                    "ok": False,
                    "image_path": str(job.path),
                    "idempotency_key": job.idempotency_key,
                    "attempts": attempt + 1,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                    "error": str(error),
                }
            sleep_seconds = backoff_seconds * (2**attempt)
            time.sleep(sleep_seconds)
            attempt += 1


def run_once(args: argparse.Namespace, progress: ProgressStore) -> list[dict[str, Any]]:
    jobs = [
        job
        for job in iter_images(args.input_dir, args.batch_id)
        if not progress.is_done(job.idempotency_key)
    ]
    if args.limit:
        jobs = jobs[: args.limit]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = []
        for job in jobs:
            futures.append(
                executor.submit(
                    send_job,
                    job,
                    args.api_url,
                    args.mode,
                    args.station_id,
                    args.batch_id,
                    args.timeout,
                    args.retries,
                    args.backoff,
                )
            )
            if args.interval > 0:
                time.sleep(args.interval)
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if result["ok"]:
                progress.record_success(str(result["idempotency_key"]), result)
            else:
                progress.record_failure(str(result["idempotency_key"]), result)
    return results


def summarize(
    results: list[dict[str, Any]], started_at: datetime, args: argparse.Namespace
) -> dict[str, Any]:
    latencies = [float(item["elapsed_ms"]) for item in results if item.get("ok")]
    success = [item for item in results if item.get("ok")]
    failures = [item for item in results if not item.get("ok")]
    report = {
        "started_at": started_at.isoformat().replace("+00:00", "Z"),
        "finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "input_dir": str(args.input_dir),
        "api_url": args.api_url,
        "mode": args.mode,
        "station_id": args.station_id,
        "batch_id": args.batch_id,
        "total_sent": len(results),
        "success_count": len(success),
        "failure_count": len(failures),
        "auto_pass_count": len([item for item in success if item.get("final_status") == "PASS"]),
        "review_required_count": len([item for item in success if item.get("requires_review")]),
        "idempotent_count": len([item for item in success if item.get("idempotent")]),
        "average_response_ms": round(statistics.mean(latencies), 3) if latencies else 0.0,
        "p95_response_ms": percentile(latencies, 0.95),
        "results": results,
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate a production line against FastAPI")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument(
        "--mode", choices=["classical", "detection", "anomaly", "hybrid"], default="hybrid"
    )
    parser.add_argument("--station-id", default="station-01")
    parser.add_argument("--batch-id", default="demo-batch-001")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--max-cycles", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--backoff", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--progress-path",
        type=Path,
        default=Path("artifacts/production-simulator/progress.json"),
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("artifacts/production-simulator/report.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input_dir.is_dir():
        raise SystemExit(f"input directory does not exist: {args.input_dir}")
    if args.concurrency < 1:
        raise SystemExit("--concurrency must be >= 1")
    started_at = datetime.now(UTC)
    progress = ProgressStore(args.progress_path)
    all_results: list[dict[str, Any]] = []
    cycle = 0
    try:
        while True:
            cycle += 1
            all_results.extend(run_once(args, progress))
            if not args.loop or cycle >= args.max_cycles:
                break
    except KeyboardInterrupt:
        print("Interrupted; progress has been saved.")
    report = summarize(all_results, started_at, args)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
