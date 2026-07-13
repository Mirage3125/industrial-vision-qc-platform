# System Design

## 系统边界

系统边界是“图片质检闭环”：输入本地图片或上传图片，输出质量检查、已知缺陷检测、未知异常检测、规则决策、复核任务、反馈样本和数据集版本。系统不负责工业相机采集、PLC 控制、自动训练调度或自动模型上线。

## 模块职责

- `backend/app/api/*`：HTTP API 层，处理请求、响应和错误码。
- `backend/app/inspection`：混合推理、图片质量检查和决策规则。
- `backend/app/inference`：ONNX YOLO 推理和后处理。
- `backend/app/anomaly_detection`：`padim_statistical` 训练、预测、评估和可视化。
- `backend/app/models/domain.py`：SQLAlchemy 领域表。
- `frontend/src/app`：管理界面页面。
- `scripts/`：数据准备、训练、评估、注册、启动和生产线模拟。

## 数据流

1. 图片进入 `/api/v1/inspection/predict` 或 `/upload-predict`。
2. 图片质量检查先判断坏图、尺寸、曝光和模糊。
3. detection/hybrid 模式调用 ONNX YOLO。
4. anomaly/hybrid 模式调用 `padim_statistical`。
5. 决策规则综合质量问题、YOLO 置信度、高风险类别、异常分数和推理错误。
6. 如果需要复核，创建 `review_tasks`；否则保存终态记录。
7. 人工 correct 时生成 `feedback_samples`。
8. feedback export 生成新的数据集版本和 manifest。

## 数据库设计

核心表包括：

- `inspections`：图片路径、预测类型、最终状态、原始模型结果、决策结果、耗时和模型版本。
- `review_tasks`：原始预测、系统决策、人工修正、复核状态和复核人。
- `feedback_samples`：原始标签/框、修正标签/框、导出状态和来源模型版本。
- `dataset_versions`：版本号、样本数、类别分布和来源说明。
- `model_versions`：模型名、类型、版本、框架、路径、指标和 active 状态。
- `data_quality_reports`：数据质量扫描结果。
- `audit_logs`：关键操作审计。

## 模型加载

检测模型默认路径为 `artifacts/training/neu_det_baseline/weights/best.onnx`。异常检测默认路径为 `artifacts/training/anomaly/padim_statistical_metal_nut/model.npz`。模型激活前会检查文件存在；ONNX 检测模型会尝试创建 runtime session。

## 混合决策

`configs/inspection/hybrid.yaml` 中当前规则版本是 `stage8.hybrid.v1`。触发复核的情况包括推理失败、图片质量问题、YOLO 低置信度、YOLO 无框但异常分数高、YOLO 与异常检测冲突、高风险类别、未知异常和强制复核。

## 安全边界

文件上传限制常见图片扩展名和 10MB 大小。文件读取 API 应防止路径遍历，已有 `test_file_access_security.py`。当前没有生产级认证、授权和 RBAC。

## 技术取舍

项目用 ONNX Runtime CPU 作为可复现部署路径；GPU/CUDA 和 TensorRT 保留为后续优化项。异常检测采用轻量统计方案便于工程闭环演示，但效果低于成熟工业异常检测方案。
