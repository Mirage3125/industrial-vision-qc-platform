# YOLO 已知缺陷检测

## 当前状态

已实现 NEU-DET VOC/XML 转 YOLO、确定性划分、标注检查、训练/验证/推理脚本、统一 Detector 适配器、错误案例导出、模型元数据和 FastAPI 接口。当前项目环境未安装 PyTorch/Ultralytics，且本地没有完整 NEU-DET，因此没有运行 YOLO epoch，也没有记录 mAP、Precision、Recall 或延迟指标。

## 显存策略

- 默认使用 `yolo11n.pt` 和 640 输入，不使用大模型或超大输入。
- 正式配置 `batch: -1`，由 Ultralytics 自动估算显存占用；smoke 配置固定 batch 2、320 输入和 CPU，优先验证链路。
- 支持 `resume`，OOM 时训练脚本会给出减小 batch/imgsz 的明确建议，不吞掉异常。
- RTX 4060 Laptop 8GB 的正式 batch 必须以真实运行结果为准。

## 指标与产物

Ultralytics 验证输出真实混淆矩阵、PR 曲线和逐类指标。验证脚本额外生成 `validation-summary.json`；错误案例脚本按漏检、误报或类别错误导出图片与 JSON 清单。只有真实执行后才能在文档或简历中引用具体数值。

## 运行顺序

先按 [数据说明](../data/README.md) 完成转换、划分和检查。确认输出无错误后：

```powershell
python -m scripts.train_yolo --config configs/detection/smoke.yaml
python -m scripts.validate_yolo --weights artifacts/detection/smoke/chain-check/weights/best.pt
python -m scripts.run_yolo path/to/image.jpg --weights path/to/best.pt
```

正式训练必须显式使用 `configs/detection/train.yaml`，不要把 smoke 结果当作正式指标。
