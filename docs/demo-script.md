# Demo Script

## 3 分钟演示

1. 用一句话说明企业痛点：单一模型不能覆盖未知缺陷，低置信度结果需要人工复核，人工修正需要回流。
2. 打开 dashboard，说明系统由图片质量、YOLO、异常检测、复核、反馈、数据集和模型注册组成。
3. 在单图页面上传或选择真实图片。
4. 展示 YOLO 检测框和类别置信度。
5. 展示异常检测分数和热力图路径，说明当前是 `padim_statistical`。
6. 展示混合决策：低置信度、高风险类别或未知异常会进入复核。
7. 进入人工复核队列，打开复核详情。
8. 修改结果，说明当前是坐标表单/JSON 修改，不是拖拽框编辑。
9. 查看反馈样本池。
10. 展示数据集版本和模型注册页面。
11. 总结价值：模型评估、人工复核、数据回流和版本追踪形成闭环。

## 8 分钟演示

在 3 分钟流程基础上增加：

- 数据质量报告：尺寸、模糊、曝光和标注检查。
- OpenCV 传统视觉基线：说明作为低成本对照和质量检查补充。
- YOLO11n 训练结果：NEU-DET 独立测试集 mAP@0.5 0.74662。
- ONNX 部署：PyTorch/ONNX 一致性通过，CPU batch=1 平均 41.026 ms。
- CUDA 限制：当前 CUDA provider 未验证成功，不能宣称 GPU 完成。
- Docker：展示 PostgreSQL、backend、frontend 三服务。
- 生产线模拟：解释 929.417 ms 是 HTTP 端到端响应。
- GitHub Actions：说明 CI 覆盖后端和前端检查。
- 项目限制：异常检测只验证 `metal_nut`，没有 TensorRT、工业相机、PLC 和自动上线。

## 故障预案

- 3000 端口占用：`.\scripts\start-dev.ps1 -FrontendPort 3001`，并确认 CORS 配置。
- 8000 端口占用：`.\scripts\start-dev.ps1 -BackendPort 8001 -ApiBaseUrl http://localhost:8001/api/v1`。
- Docker Desktop 未启动：先启动 Docker Desktop，再执行 `docker compose ps`。
- PostgreSQL 不健康：检查 `docker compose logs postgres` 和 `.env.docker` 密码。
- 模型卷未挂载：确认 `artifacts/training/.../best.onnx` 和异常检测 `model.npz` 是否存在。
- 图片文件无法访问：确认图片在允许目录内，路径没有被清理。
- ONNX CUDA Provider 不可用：切换 CPU，或在独立 GPU 环境中重新验证 provider。
- GPU 不可用：不要把 CPU fallback 当作 GPU 成功。
