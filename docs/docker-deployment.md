# Docker deployment

Stage 10 provides a CPU-only Docker Compose deployment with three services:

- `postgres`
- `backend`
- `frontend`

The backend image installs `onnxruntime` CPU, not `onnxruntime-gpu`, and does not
depend on host CUDA. Datasets, model files and artifacts are mounted as volumes
from the repository checkout:

- `./data:/app/data`
- `./artifacts:/app/artifacts`
- `./configs:/app/configs:ro`

Large datasets and model checkpoints are not copied into images.

## Run

```powershell
Copy-Item .env.docker.example .env.docker
docker compose --env-file .env.docker build
docker compose --env-file .env.docker up
```

Backend: `http://localhost:8000`
Frontend: `http://localhost:3000`

The backend command runs `alembic upgrade head` before starting Uvicorn, so
PostgreSQL is migrated on startup.

## GPU Docker status

GPU Docker/TensorRT is not part of the required Stage 10 CPU deployment. It has
not been verified in this environment. Do not treat Docker GPU acceleration as
completed unless Docker Desktop GPU support and CUDA provider sessions are
validated separately.
