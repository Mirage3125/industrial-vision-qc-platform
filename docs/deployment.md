# Deployment

## Docker Compose

当前 Docker 部署是 CPU/PostgreSQL 方案：

```powershell
Copy-Item .env.docker.example .env.docker
docker compose --env-file .env.docker up -d --build
docker compose ps
```

服务：

- `postgres`：PostgreSQL 16，带 `pg_isready` healthcheck。
- `backend`：FastAPI，启动时执行 Alembic 和 `scripts.register_runtime_models`。
- `frontend`：Next.js standalone。

Docker 会挂载 `data/`、`artifacts/` 和 `configs/`。数据集、模型权重和运行产物不复制进镜像，也不提交 Git。

如果本机已有旧的 PostgreSQL volume，修改 `.env.docker` 密码后可能出现 `password authentication failed`。本轮验证使用独立 project 名称 `fvql-stage11` 避免删除旧 volume。只有确认旧数据库不再需要时，才应清理对应 volume。

## Windows 本地模式

```powershell
conda env create -f environment.yml
conda activate factory-vision
Push-Location frontend
npm.cmd install
Pop-Location
Copy-Item .env.example .env
alembic upgrade head
python -m scripts.register_runtime_models
.\scripts\start-dev.ps1
```

停止：

```powershell
.\scripts\stop-dev.ps1
```

## 常用地址

- 前端：`http://localhost:3000`
- Swagger：`http://localhost:8000/docs`
- health：`http://localhost:8000/api/v1/health`
- ready：`http://localhost:8000/api/v1/ready`

## GPU 说明

`configs/environments/requirements-ort-gpu.txt` 是 ONNX GPU 独立环境依赖。当前真实报告显示 CUDA provider 未验证成功。TensorRT 和 Docker GPU 未完成。
