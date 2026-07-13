# Data Loop

## 进入人工复核的情况

图片质量问题、推理失败、低置信度、高风险缺陷、未知异常、YOLO 与异常检测冲突、强制复核都会创建 `review_tasks`。

## 原始预测如何保留

`inspections` 保存 `quality_result`、`yolo_result`、`anomaly_result`、`system_decision` 和 `step_timings`。`review_tasks.original_prediction` 保存复核开始时的完整原始预测，不会被人工修正覆盖。

## 人工修正如何保存

复核接口 `/api/v1/reviews/{id}/correct` 把人工结果写入 `review_tasks.corrected_prediction`。如果需要进入训练数据回流，会创建一条 `feedback_samples`，保存原始框、修正框、原始标签、修正标签和来源模型版本。

## feedback_sample 如何产生

只有 correct 操作会调用 `create_feedback_from_review`。approve 和 reject 不会生成反馈样本。

## 如何阻止重复导出

`/api/v1/feedback/export` 会先检查是否已存在相同 `dataset_version`。如果存在，返回 `DATASET_VERSION_EXISTS`，HTTP 状态码 409。导出目录已经存在时也返回 409。

## dataset_version 如何生成

导出时将 pending feedback samples 拷贝到 `output_root/dataset_version/images/train`，生成 YOLO label，并写入 `manifest.json`。同时数据库写入 `dataset_versions` 并把样本标记为 exported。

## 为什么不自动训练

自动训练和自动上线会扩大风险边界，需要人工确认数据质量、类别分布、评估结果和回滚策略。当前系统只负责生成可追踪数据集版本，后续训练由管理员手动触发。
