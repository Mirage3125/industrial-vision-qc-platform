# Factory Vision Quality Loop v1.0.0

Factory Vision Quality Loop is an industrial vision quality-loop application that combines known-defect detection, anomaly detection, human review, feedback sample export, model registry workflows and deployment verification.

## Core Features

- YOLO11n known-defect detection for NEU-DET surface defects.
- `padim_statistical` industrial anomaly detection for MVTec AD `metal_nut`.
- OpenCV image quality checks and classical vision baselines.
- Hybrid inference using quality checks, ONNX YOLO, anomaly detection and decision rules.
- Human review with original prediction retention.
- Feedback sample creation and dataset version export.
- Model registry with activation and rollback health checks.
- FastAPI backend and Next.js management UI.
- PostgreSQL and Docker Compose CPU deployment.
- Production-line HTTP simulation and GitHub Actions CI.

## Verified Results

Metrics are summarized from real local reports in `docs/reports/release-metrics-v1.0.0.json`.

### YOLO11n NEU-DET Test Metrics

| Metric | Result |
| --- | ---: |
| Precision | 0.71686 |
| Recall | 0.70027 |
| mAP@0.5 | 0.74662 |
| mAP@0.5:0.95 | 0.43375 |

### Anomaly Detection

| Metric | Result |
| --- | ---: |
| Category | `metal_nut` |
| Image-level AUROC | 0.73460 |
| Pixel-level AUROC | 0.44985 |
| Image-level F1 | 0.59701 |
| Pixel-level F1 | 0.11926 |
| Normal false positive rate | 0.04545 |
| Anomaly false negative rate | 0.56989 |
| Average inference time | 58.62 ms |

### ONNX Runtime

| Runtime | Batch | Avg latency | P95 latency | Throughput |
| --- | ---: | ---: | ---: | ---: |
| CPUExecutionProvider | 1 | 41.026 ms | 55.0858 ms | 24.3748 images/s |
| CPUExecutionProvider | 4 | 182.907 ms | 211.5462 ms | 21.8690 images/s |
| CUDAExecutionProvider | - | unavailable | unavailable | unavailable |

CUDA was requested during validation, but ONNX Runtime fell back to CPU. TensorRT is not verified.

### Release Verification

- Backend tests: `pytest` 35 passed.
- Backend static checks: `ruff`, `mypy` and `compileall` passed.
- Frontend checks: `lint`, `typecheck` and `build` passed with six known `<img>` performance warnings.
- Docker: fresh Compose project build, startup, health checks and core quality-loop flow passed.
- Core loop: image upload, hybrid inference, inspection persistence, review task, manual correction, feedback sample, dataset version export and duplicate export conflict were verified.

## Quick Start

```powershell
Copy-Item .env.docker.example .env.docker
docker compose --env-file .env.docker up -d --build
docker compose ps
```

Open:

- Frontend: `http://localhost:3000`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`
- Ready: `http://localhost:8000/api/v1/ready`

See [README.md](../README.md) for local Windows startup, model file paths and detailed documentation.

## Not Included In This Release

- Complete NEU-DET or MVTec AD datasets.
- Model weights or ONNX binaries.
- SQLite/PostgreSQL database files.
- Environment files, passwords, tokens or API keys.
- TensorRT, Docker GPU, industrial camera/PLC integration or production RBAC.

## Known Limitations

- Anomaly detection is only validated on MVTec AD `metal_nut`.
- ONNX CUDA is not verified in the current report.
- TensorRT is not implemented or validated.
- Review box editing is form/JSON based; graphical drag editing is not implemented.
- The system does not automatically retrain or automatically publish models.
