# Limitations

- 检测框当前支持叠加显示和坐标表单/JSON 修改，未实现图形化拖拽编辑。
- 异常检测只验证 MVTec AD `metal_nut` 一个类别。
- `padim_statistical` 不是标准 PaDiM 论文完整复现。
- 异常检测效果有限：image-level AUROC 0.73460，异常漏检率 0.56989。
- ONNX CUDA provider 当前未验证成功，报告显示回落 CPU。
- TensorRT 未验证。
- Docker GPU 未验证。
- 未接入工业相机和 PLC。
- 未实现生产级 RBAC、审计策略和多租户权限。
- 未实现自动训练、自动上线和模型灰度发布。
- 当前监控能力有限，未接入 Prometheus/Grafana。
- 数据集和模型权重不提交 GitHub，需要本地准备或后续通过 Release/外部仓库分发。
