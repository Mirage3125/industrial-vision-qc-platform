# 数据目录

大型数据集不提交到 Git。阶段 5 默认使用 NEU-DET 钢材表面缺陷数据集，类别顺序为：

1. crazing
2. inclusion
3. patches
4. pitted_surface
5. rolled_in_scale
6. scratches

## 获取说明

NEU-DET 原始发布页可能随镜像变化，请从东北大学相关研究页面或可信学术数据镜像获取，并确认使用许可。下载后保留原始 VOC/XML 数据只读，不要将完整数据或训练权重提交到仓库。

期望的原始布局：

```text
data/neu-det-voc/
├── images/
│   ├── crazing_1.jpg
│   └── ...
└── annotations/
    ├── crazing_1.xml
    └── ...
```

转换后的 YOLO 布局：

```text
data/neu-det-yolo/
├── all/
│   ├── images/
│   └── labels/
├── train/
│   ├── images/
│   └── labels/
└── val/
    ├── images/
    └── labels/
```

## 准备流程

```powershell
python -m scripts.convert_voc_to_yolo `
  --images data/neu-det-voc/images `
  --annotations data/neu-det-voc/annotations `
  --output data/neu-det-yolo/all `
  --config configs/detection/neu-det.yaml

python -m scripts.split_detection_dataset `
  --source data/neu-det-yolo/all `
  --output data/neu-det-yolo `
  --val-ratio 0.2 `
  --seed 42

python -m scripts.validate_detection_dataset `
  --dataset data/neu-det-yolo `
  --config configs/detection/neu-det.yaml
```

转换脚本会检查 XML 尺寸、类别、空框和越界框；验证脚本会再次检查 YOLO 标签范围、类别分布、空标注和 train/val 内容哈希泄漏。
