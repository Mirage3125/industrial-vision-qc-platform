# Current Project Status

本文件只记录当前仓库和本机 artifacts 中能核对到的事实。状态只使用 `VERIFIED`、`IMPLEMENTED_NOT_VERIFIED`、`LIMITED`、`NOT_IMPLEMENTED`。

## 状态清单

| 项目 | 状态 | 依据 |
| --- | --- | --- |
| FastAPI 后端 | IMPLEMENTED_NOT_VERIFIED | `backend/app/main.py` 已注册 health、detection、anomaly、inspection、reviews、feedback、models、dashboard、files API；本轮尚未完成启动验证 |
| 前端页面 | IMPLEMENTED_NOT_VERIFIED | `frontend/src/app` 包含 dashboard、single、batch、reviews、feedback、datasets、models、quality、benchmarks 等页面；本轮尚未完成浏览器截图 |
| 数据库表 | IMPLEMENTED_NOT_VERIFIED | Alembic 0001-0004 和 `backend/app/models/domain.py` 覆盖 inspections、review_tasks、feedback_samples、dataset_versions、model_versions、data_quality_reports、audit_logs |
| NEU-DET manifest | VERIFIED | `artifacts/datasets/neu-det/raw_manifest.json` 和 `split_manifest.json` |
| YOLO11n 训练结果 | VERIFIED | `artifacts/detection/neu_det_baseline_test/validation-summary.json` |
| YOLO 模型文件 | VERIFIED | 本机存在 `best.pt` 和 `best.onnx`，但在 `artifacts/` 下不提交 Git |
| 模型注册脚本 | IMPLEMENTED_NOT_VERIFIED | `scripts/register_runtime_models.py`、`backend/app/api/models.py` |
| PyTorch/ONNX 一致性 | VERIFIED | `artifacts/detection/neu_det_onnx_consistency.json` |
| ONNX CPU benchmark | VERIFIED | `artifacts/benchmarks/neu_det_baseline/onnx-cpu.json` |
| ONNX CUDA benchmark | LIMITED | `onnx-cuda.json` 显示 requested CUDA 但 actual CPU，状态 unavailable |
| 异常检测评估 | VERIFIED | `artifacts/anomaly_evaluation/padim_statistical_metal_nut/metrics.json` |
| 混合推理流程 | IMPLEMENTED_NOT_VERIFIED | `backend/app/inspection/service.py` 和 `configs/inspection/hybrid.yaml`；本轮未重新发起 API 预测 |
| 人工复核流程 | IMPLEMENTED_NOT_VERIFIED | `backend/app/api/reviews.py` 保存 approve/correct/reject |
| 数据回流流程 | IMPLEMENTED_NOT_VERIFIED | `backend/app/api/feedback.py` 导出反馈样本，重复 dataset version 返回 409 |
| 生产线模拟报告 | VERIFIED | `artifacts/production-simulator/stage10-report.json` |
| Docker Compose | IMPLEMENTED_NOT_VERIFIED | `docker-compose.yml` 存在 PostgreSQL、backend、frontend；本轮尚未完成 Docker 启动 |
| PostgreSQL | IMPLEMENTED_NOT_VERIFIED | Docker Compose 使用 PostgreSQL 16，ready 检查依赖数据库 |
| GitHub Actions | IMPLEMENTED_NOT_VERIFIED | `.github/workflows/ci.yml` 存在 |
| PowerShell 脚本 | IMPLEMENTED_NOT_VERIFIED | `scripts/start-dev.ps1`、`stop-dev.ps1`、`test-all.ps1` 存在 |
| 截图 | NOT_IMPLEMENTED | 未生成真实截图；已提供 `docs/screenshot-checklist.md` |

## README 可以声明

- 项目是工业视觉质检闭环系统，不是单一模型训练项目。
- YOLO11n 在 NEU-DET 独立测试集上的 Precision、Recall、mAP 指标来自 JSON 报告。
- 异常检测算法名是 `padim_statistical`，当前只验证 MVTec AD `metal_nut`。
- ONNX CPU benchmark 已有真实报告；CUDA provider 当前未验证通过。
- 人工复核会保留原始预测，人工修正另存，并可导出反馈数据集版本。
- Docker Compose 是 CPU/PostgreSQL 部署。

## README 禁止声明

- 不得声明 TensorRT 已完成。
- 不得声明 Docker GPU 已验证。
- 不得把 ONNX CUDA 回落 CPU 写成 CUDA 成功。
- 不得把 `padim_statistical` 写成完整 PaDiM 论文复现。
- 不得说系统会自动训练、自动上线或自动灰度发布模型。
- 不得把生产线 HTTP 模拟的约 929 ms 与 ONNX 单模型延迟直接比较。
