# ONNX Deployment

## 部署原则

ONNX Runtime 是当前检测模型的部署路径。PyTorch 训练环境、ONNX CPU 环境和 ONNX GPU 环境要分开描述：

- PyTorch 训练环境用于训练和导出，不等同于 ONNX 部署环境。
- ONNX CPU 使用 `CPUExecutionProvider`。
- ONNX GPU 必须在独立环境中安装并实际创建 `CUDAExecutionProvider` session。
- 只看到 provider 名称或依赖安装成功，不等于 CUDA 推理成功。
- 如果请求 CUDA 但 actual provider 回落 CPU，必须记为失败或受限。

## 一致性报告

`artifacts/detection/neu_det_onnx_consistency.json`：

- same_shape：true
- raw_outputs_close：true
- max_absolute_difference：0.00198
- pytorch_detection_count：3
- onnx_detection_count：3
- atol/rtol：0.001

## CPU benchmark

`artifacts/benchmarks/neu_det_baseline/onnx-cpu.json`：

| batch | first inference | mean | p50 | p95 | p99 | throughput |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 38.724 ms | 41.026 ms | 38.8025 ms | 55.0858 ms | 60.2672 ms | 24.3748 images/s |
| 4 | 185.4141 ms | 182.907 ms | 179.0516 ms | 211.5462 ms | 228.7962 ms | 21.869 images/s |

模型大小：9.9432 MiB。

## CUDA benchmark

`artifacts/benchmarks/neu_det_baseline/onnx-cuda.json`：

- status：unavailable
- requested_provider：`CUDAExecutionProvider`
- actual_provider：`CPUExecutionProvider`
- error：Requested provider failed to load and ONNX Runtime fell back to CPU

当前不能声明 ONNX CUDA 已完成。

## TensorRT

TensorRT 未验证。当前仓库不能声明 TensorRT engine 构建、插件、CUDA/cuDNN 组合或 TensorRT 性能结果。

## 命令

```powershell
python -m scripts.export_yolo_onnx --weights artifacts/training/neu_det_baseline/weights/best.pt
python -m scripts.check_onnx_model --model artifacts/training/neu_det_baseline/weights/best.onnx
python -m scripts.check_yolo_consistency --weights artifacts/training/neu_det_baseline/weights/best.pt --onnx artifacts/training/neu_det_baseline/weights/best.onnx --image data/processed/neu-det-yolo/images/test/crazing_101.jpg
python -m scripts.benchmark_onnx --model artifacts/training/neu_det_baseline/weights/best.onnx --provider cpu --batch-sizes 1 4
python -m scripts.register_onnx_model --model artifacts/training/neu_det_baseline/weights/best.onnx --name neu-det-yolo11n --version neu-det-baseline --activate
```
