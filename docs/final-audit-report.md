# Final Audit Report

## Audit Time

- Date: 2026-07-13
- Scope: GitHub release readiness, README/code consistency, model metric provenance, security/privacy, Git hygiene, Docker startup, Windows local startup, backend/frontend tests, and core quality-loop demo.
- Final status: `READY_WITH_LIMITATIONS`

## Severity Summary

### BLOCKER

- None found after verification.

### HIGH

- Fixed: `docs/project-plan.md` contained a local absolute repository path. It was replaced with a generic project-directory description.
- Fixed: `scripts/start-dev.ps1` could fail in Windows environments where the process environment contains both `Path` and `PATH`, and it could report success before services were actually reachable. The script now normalizes process PATH keys and waits for backend/frontend endpoints before reporting ready.

### MEDIUM

- Default `docker compose --env-file .env.docker up -d` failed on this workstation because an existing `factory-vision-quality-loop_postgres_data` volume kept an older PostgreSQL password. The README documents the workaround using a new Compose project name. A fresh project (`fvql-audit-20260713`) passed.
- README does not currently embed the saved screenshots directly. Screenshot files exist under `docs/images/`, but interview reviewers must browse the directory unless images are linked from README.
- `docs/project-plan.md` still contains historical stage-one notes such as "not a Git repository"; this is explainable as planning history but can confuse readers if treated as current state.

### LOW

- Frontend lint/build report six allowed `<img>` performance warnings.
- Direct `.ps1` execution is blocked by this workstation's PowerShell execution policy. Process-level `-ExecutionPolicy Bypass` was used for verification without changing global policy.

## Fixed Issues

- Removed the local absolute path from `docs/project-plan.md`.
- Updated `scripts/start-dev.ps1` to normalize duplicate process PATH keys.
- Updated `scripts/start-dev.ps1` to wait for `http://127.0.0.1:8000/api/v1/health` and `http://localhost:3000` before reporting ready, and to show log tails on startup failure.

## Unfixed Issues

- README screenshots are not embedded.
- Default Compose project can still fail if a stale local PostgreSQL volume has a different password. This is documented and not caused by the current images.
- CUDAExecutionProvider remains unavailable in the recorded ONNX report; TensorRT is not verified.

## Functionality Authenticity Check

| Item | Result |
| --- | --- |
| Data quality scanner | Present and covered by code/docs. |
| OpenCV classical baseline | Present in `backend/app/classical_vision/` and scripts. |
| YOLO11n model | Real model paths and reports exist locally under ignored `artifacts/`. |
| Anomaly detection | Real `padim_statistical` OpenCV/NumPy model exists for MVTec AD `metal_nut`. |
| ONNX CPU | Verified by reports and Docker hybrid inference using `CPUExecutionProvider`. |
| ONNX CUDA | Not verified; documented as unavailable. |
| Hybrid inference | Verified through Docker API using a real image; YOLO ONNX, anomaly detection, quality checks, and decision logic all returned real outputs. |
| Inspection persistence | Verified: `inspection_id` created by `/inspection/upload-predict`. |
| Review task creation | Verified: `review_id` created with `force_review=true`. |
| Manual correction | Verified: `/reviews/{id}/correct` returned `corrected`. |
| Original prediction retention | Verified by API design and review payload fields. |
| Feedback sample | Verified by feedback export sample count `1`. |
| Dataset version export | Verified: `audit-20260713-1324` created. |
| Duplicate export 409 | Verified: repeat export returned HTTP 409. |
| Model registry activate/rollback | Verified for detection and anomaly models. |
| Production simulator | Report exists at `artifacts/production-simulator/stage10-report.json`. |
| Docker | Fresh project build/up/health/core loop passed. |
| PostgreSQL persistence | Verified: dataset version remained after container restart. |
| GitHub Actions | `.github/workflows/ci.yml` matches backend/frontend checks and repository hygiene checks. |
| Frontend backend calls | Verified by source and live Docker/Windows endpoint checks. |

## Model And Metric Provenance

| Area | Audit Result |
| --- | --- |
| YOLO | README metrics are tied to `artifacts/datasets/neu-det/*.json` and `artifacts/detection/neu_det_baseline_test/validation-summary.json`. Model name is consistently YOLO11n in release-facing docs. |
| Anomaly detection | README describes `padim_statistical` as a custom PaDiM-style statistical detector, not a standard PaDiM reproduction. Metrics are tied to `artifacts/training/anomaly/padim_statistical_metal_nut/training-metadata.json` and `artifacts/anomaly_evaluation/padim_statistical_metal_nut/metrics.json`. |
| ONNX | CPU benchmark and PyTorch/ONNX consistency reports exist. CUDA is correctly marked unavailable because requested CUDA provider fell back to CPU. TensorRT is not claimed as complete. |
| Production simulator | HTTP latency is documented separately from ONNX single-model latency. |

## Security Check

- Tracked secret scan found no AWS/OpenAI/GitHub/Slack key patterns.
- `.env`, `.env.*`, `*.db`, logs, artifacts, data imports, model weights, `node_modules`, `.next`, caches, and temp outputs are ignored.
- A tracked local absolute path was found and fixed.
- `GET /api/v1/files?path=...` was tested:
  - `../.env`: 403
  - URL-encoded traversal: 403
  - Windows absolute path: 403
  - Linux absolute path: 403
  - `.env`: 403
  - `factory_vision.db`: 403
  - file outside allowed roots (`README.md`): 403
  - model weight extension (`best.pt`): 403
  - allowed uploaded PNG: 200
  - allowed JSON artifact: 200

## Large File And Git Hygiene

- `git check-ignore` confirms local `.env`, `.env.docker`, `factory_vision.db`, `yolo11n.pt`, `artifacts/`, `logs/`, `frontend/.next`, `frontend/node_modules`, `data/raw`, and `data/processed` are ignored.
- Current local large files include datasets, model weights, ONNX files, and evaluation images, but they are under ignored paths or ignored suffixes.
- `git rev-list --objects --all` found no historical Git object over 1 MiB.
- No `git add`, `git commit`, `git push`, or GitHub release action was performed.

## Docker Verification

- `docker compose --env-file .env.docker config`: passed.
- `docker compose --env-file .env.docker build`: passed.
- Default `docker compose --env-file .env.docker up -d`: failed due stale local PostgreSQL volume password.
- Fresh project `docker compose -p fvql-audit-20260713 --env-file .env.docker up -d`: passed.
- `docker compose ps`: PostgreSQL healthy, backend healthy, frontend running.
- `GET /api/v1/health`: 200.
- `GET /api/v1/ready`: 200 with database reachable.
- `GET /docs`: 200.
- `GET /` frontend: 200.
- Core loop: hybrid upload-predict, review correction, feedback export, duplicate export 409, model activate/rollback, and restart persistence all passed.
- Temporary audit Compose project and volume were removed after verification.

## Windows Local Verification

- `scripts/start-dev.ps1`: passed after HIGH fix.
- Backend health: 200.
- Backend ready: 200.
- Frontend: 200.
- `scripts/stop-dev.ps1`: stopped recorded backend/frontend PIDs.
- The script uses `npm.cmd`.
- No global PATH or PowerShell execution policy was modified.
- Port collision handling exists through `Get-NetTCPConnection` and reports owning PID.

## Backend Tests

- `python -m pytest`: 35 passed, 1 FastAPI/TestClient deprecation warning.
- `python -m ruff check .`: passed.
- `python -m mypy`: passed for 66 source files.
- `python -m compileall backend scripts`: passed.

## Frontend Tests

- `npm.cmd run lint`: passed with 6 `<img>` warnings.
- `npm.cmd run typecheck`: passed.
- `npm.cmd run build`: passed with the same 6 `<img>` warnings.

## Current Demo-Ready Features

- Dashboard and management UI.
- Single-image and batch inspection pages.
- Hybrid inference using image quality checks, ONNX YOLO CPU, anomaly detection, and decision rules.
- Inspection records persisted to database.
- Review queue and review detail.
- Manual correction and feedback sample creation.
- Dataset version export with duplicate-version conflict handling.
- Model registry, activation, and rollback health checks.
- Data quality reports and benchmark pages.
- Docker CPU deployment with PostgreSQL.
- Windows local dev startup.

## Current Non-Demo Or Limited Features

- CUDA ONNX provider is not validated.
- TensorRT is not implemented or validated.
- Docker GPU is not validated.
- No industrial camera, PLC, production RBAC, Prometheus/Grafana, MLflow, automatic training, automatic model publishing, or model canary rollout.
- Anomaly detection is only validated on MVTec AD `metal_nut`, with limited metrics.
- Review box editing is form/JSON-based rather than graphical drag editing.

## GitHub Release Checklist

- No unresolved BLOCKER: yes.
- No unresolved HIGH: yes.
- README startup commands verified with documented caveat for stale Docker volume: yes.
- Docker core loop verified in a fresh Compose project: yes.
- Windows local startup verified: yes.
- Backend tests passed: yes.
- Frontend build passed: yes.
- No tracked secrets found: yes.
- No complete datasets tracked: yes.
- No inappropriate tracked large files found: yes.
- No tracked personal absolute paths after fix: yes.
- Documentation generally matches implementation: yes, with MEDIUM notes.
- Screenshots exist: yes.
- Core demo can be completed: yes.

## Interview Demo Checklist

- First 30 seconds explain the problem: yes.
- Real model metrics visible in README: yes.
- System architecture visible in README/docs: yes.
- Human review and data loop explainable: yes.
- Quick start commands present: yes.
- Current limitations visible: yes.
- Excessive unsupported claims: no major issue found.
- Resume description should avoid CUDA/TensorRT/production-grade claims beyond verified evidence.

## Final Decision

`READY_WITH_LIMITATIONS`

The repository is suitable for GitHub publication and recruiter demo if the limitations above are kept visible. It should not be described as CUDA/TensorRT-ready, production-line-integrated, or fully production-grade.
