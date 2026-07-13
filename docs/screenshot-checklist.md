# Screenshot Checklist

当前阶段没有生成真实浏览器截图。禁止用伪造截图替代。完成本地启动后按以下清单截取真实页面，保存到 `docs/images/`。

| 文件名 | 页面 | 操作 | 应显示内容 |
| --- | --- | --- | --- |
| `dashboard.png` | `http://localhost:3000` | 打开首页 | 今日检测数、缺陷数、复核数、活跃模型 |
| `single-inspection.png` | `/single` | 上传或选择真实图片并运行 hybrid | 检测结果、复核原因、模型结果 |
| `batch-inspection.png` | `/batch` | 批量提交图片 | 批量状态和结果列表 |
| `anomaly-heatmap.png` | 单图或复核详情 | 选择异常检测结果 | 异常分数、热力图路径或预览 |
| `review-queue.png` | `/reviews` | 打开复核队列 | pending review 列表 |
| `review-detail.png` | `/reviews/{id}` | 打开复核详情 | 原始预测、修正表单、历史记录 |
| `feedback-pool.png` | `/feedback` | 复核 correct 后打开 | 反馈样本、原始标签、修正标签 |
| `dataset-versions.png` | `/datasets` | 导出或创建版本后打开 | 数据集版本列表 |
| `model-registry.png` | `/models` | 注册模型后打开 | 模型版本、路径、active 状态 |
| `benchmark.png` | `/benchmarks` | 打开 benchmark 页面 | CPU benchmark 和 CUDA unavailable |
| `data-quality.png` | `/quality` | 打开质量报告 | 图片数量、问题统计、报告路径 |
