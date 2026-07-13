# Hybrid Inference

混合推理由 `InspectionPredictionService` 实现，配置来自 `configs/inspection/hybrid.yaml`。

## 支持模式

- `classical`：当前强制进入复核，状态为 `REVIEW_REQUIRED`。
- `detection`：只跑 YOLO ONNX，异常结果置空。
- `anomaly`：只跑异常检测。
- `hybrid`：同时跑图片质量、YOLO ONNX 和异常检测。

## 决策规则

会进入复核的情况：

- 图片损坏、尺寸过小、模糊、过曝或欠曝。
- YOLO 推理失败或异常检测推理失败。
- YOLO 有框但最高置信度低于 `yolo_low_confidence_threshold`。
- YOLO 无框但异常分数超过阈值。
- YOLO 有框且异常检测也认为异常，视为冲突或未知异常。
- 命中高风险类别 `scratches` 或 `pitted_surface`。
- `force_review=true`。

## 延迟口径

`step_timings` 保存 yolo、anomaly 和 total 的步骤耗时。生产线模拟报告中的约 929 ms 是端到端 HTTP 响应时间，不是 ONNX 单模型耗时。

## 限制

默认 YOLO provider 是 CPU。当前没有自动 CUDA fallback 成功判定，CUDA 必须看 ONNX Runtime session 的 actual provider。
