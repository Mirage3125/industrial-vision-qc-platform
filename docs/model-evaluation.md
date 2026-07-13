# Model Evaluation

## YOLO11n

评估来源：`artifacts/detection/neu_det_baseline_test/validation-summary.json`。

| 指标 | 数值 |
| --- | --- |
| Precision | 0.71686 |
| Recall | 0.70027 |
| mAP@0.5 | 0.74662 |
| mAP@0.5:0.95 | 0.43375 |
| fitness | 0.46503 |

独立测试集来自 `split_manifest.json`：180 张图片，测试集实例分布为 crazing 64、inclusion 111、patches 91、pitted_surface 44、rolled_in_scale 72、scratches 52。

各类别 `mAP@0.5:0.95`：

| 类别 | mAP@0.5:0.95 |
| --- | --- |
| crazing | 0.15075 |
| inclusion | 0.47021 |
| patches | 0.56986 |
| pitted_surface | 0.50764 |
| rolled_in_scale | 0.32347 |
| scratches | 0.58054 |

## 错误案例说明

`artifacts/detection/neu_det_baseline_errors/error-cases.json` 的每条记录是一张图片及其混合错误列表。`errors` 数组可能同时出现 `missed_detection` 和 `false_positive`，因此它不是单纯的错误图片数、误报实例数或漏检实例数。使用该文件时应明确按记录、图片或错误项分别统计。

## 异常检测

评估来源：`artifacts/anomaly_evaluation/padim_statistical_metal_nut/metrics.json`。

| 指标 | 数值 |
| --- | --- |
| algorithm | `padim_statistical` |
| category | `metal_nut` |
| sample_count | 115 |
| image_level_auroc | 0.73460 |
| pixel_level_auroc | 0.44985 |
| image_level_f1 | 0.59701 |
| pixel_level_f1 | 0.11926 |
| normal_false_positive_rate | 0.04545 |
| anomaly_false_negative_rate | 0.56989 |
| average_inference_time_ms | 58.62 |
| p95_inference_time_ms | 93.22 |

当前异常检测只验证一个类别，漏检率较高，应作为闭环组件和未知异常补充能力，而不是替代 YOLO。

## ONNX 一致性和 benchmark

`neu_det_onnx_consistency.json` 显示 PyTorch/ONNX 输出形状一致，raw outputs close 为 true，最大绝对差异 0.00198，检测框数量均为 3。

CPU benchmark：

| batch | 平均延迟 | p95 | 吞吐 |
| --- | --- | --- | --- |
| 1 | 41.026 ms | 55.0858 ms | 24.3748 images/s |
| 4 | 182.907 ms | 211.5462 ms | 21.869 images/s |

CUDA benchmark 当前为 unavailable：请求 `CUDAExecutionProvider`，实际 provider 为 `CPUExecutionProvider`，错误信息为 provider 加载失败并回落 CPU。

## 端到端延迟

`stage10-report.json` 是 HTTP hybrid 流程模拟：2 张图成功，均进入复核，平均响应 929.417 ms，p95 933.582 ms。该耗时包含 HTTP、图片读取、质量检查、YOLO、异常检测、决策和数据库写入，不能与 ONNX 单模型 benchmark 直接对比。
