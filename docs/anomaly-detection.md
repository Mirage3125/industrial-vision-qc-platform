# Anomaly Detection

当前异常检测算法名为 `padim_statistical`。它使用 OpenCV/NumPy 提取 LAB 颜色和梯度特征，基于正常样本的均值/标准差计算异常分数，属于 PaDiM-style 统计异常检测，不是标准 PaDiM 论文完整复现。

## 真实报告

- 数据集 manifest：`artifacts/datasets/mvtec-ad/manifest.json`
- 训练元数据：`artifacts/training/anomaly/padim_statistical_metal_nut/training-metadata.json`
- 评估指标：`artifacts/anomaly_evaluation/padim_statistical_metal_nut/metrics.json`

## 数据

- 数据集：MVTec AD
- 类别：`metal_nut`
- train/good：220
- test/good：22
- test anomaly：bent 25, color 22, flip 23, scratch 23
- mask：93
- 图片尺寸：335 张 700x700

## 指标

| 指标 | 数值 |
| --- | --- |
| image-level AUROC | 0.73460 |
| pixel-level AUROC | 0.44985 |
| image-level F1 | 0.59701 |
| pixel-level F1 | 0.11926 |
| normal false positive rate | 0.04545 |
| anomaly false negative rate | 0.56989 |
| average inference time | 58.62 ms |
| p50 / p95 / p99 | 52.99 / 93.22 / 118.48 ms |

## 结论

该模块可作为未知异常补充和质量闭环演示组件，但当前效果有限，不能替代 YOLO，也不能宣传为成熟工业异常检测模型。后续可以在同一接口后增加 PatchCore、CNN feature PaDiM 或 EfficientAD。
