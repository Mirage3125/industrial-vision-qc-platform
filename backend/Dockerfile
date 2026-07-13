FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY configs/environments/requirements-docker-cpu.txt /tmp/requirements-docker-cpu.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/requirements-docker-cpu.txt

COPY alembic.ini pyproject.toml ./
COPY backend ./backend
COPY scripts ./scripts

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python -m scripts.register_runtime_models && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
