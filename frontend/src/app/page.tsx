"use client";

import { useEffect, useMemo, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { Badge, EmptyState, ErrorPanel, PageHeader, SectionTitle, StatCard, StatusBadge } from "@/components/ProductUI";
import { getDatasets, getOverview } from "@/lib/api";
import {
  formatConfidence,
  formatArray,
  formatDateTime,
  formatDefect,
  formatMs,
  formatNumber,
  modelDisplay,
  valueText
} from "@/lib/format";
import type { Overview } from "@/lib/types";

export default function DashboardPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [datasetVersion, setDatasetVersion] = useState<string>("—");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const [overview, datasets] = await Promise.all([getOverview(), getDatasets().catch(() => ({ versions: [] }))]);
        if (!active) return;
        setData(overview);
        const latest = datasets.versions[0];
        setDatasetVersion(valueText(latest?.version ?? latest?.id));
      } catch (err) {
        if (active) setError((err as Error).message);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, []);

  const classEntries = useMemo(() => {
    const entries = Object.entries(data?.class_distribution ?? {});
    const max = Math.max(...entries.map(([, count]) => count), 1);
    return entries.map(([name, count]) => ({ name, count, width: `${Math.max((count / max) * 100, 4)}%` }));
  }, [data]);

  if (error) return <ErrorPanel message={error} />;
  if (!data) {
    return (
      <div className="space-y-6">
        <PageHeader title="系统概览" description="正在加载质量闭环平台运行数据。" />
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <div key={index} className="h-28 animate-pulse rounded-lg bg-white" />
          ))}
        </div>
      </div>
    );
  }

  const activeModels = Array.isArray(data.active_models) ? data.active_models : [];
  const recentRecords = Array.isArray(data.recent_records) ? data.recent_records : [];
  const activeModel = activeModels[0];
  const defectTone = data.defect_rate > 0.1 ? "danger" : data.defect_rate > 0.03 ? "warning" : "success";
  const serviceTone = data.pending_review_count > 0 ? "warning" : "success";

  return (
    <div className="space-y-6">
      <PageHeader
        title="系统概览"
        description="覆盖缺陷检测、人工复核、反馈样本沉淀、数据集版本管理和模型迭代的质量闭环平台。"
        actions={data.demo_data ? <Badge tone="warning">演示数据</Badge> : <Badge tone="success">真实数据</Badge>}
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="今日检测数量" value={data.today_detection_count} hint="当天进入检测闭环的图片数" tone="info" />
        <StatCard label="缺陷数量" value={data.defect_count} hint="最终判定为缺陷的记录" tone={data.defect_count > 0 ? "danger" : "success"} />
        <StatCard label="缺陷率" value={formatConfidence(data.defect_rate)} hint="缺陷数 / 今日检测数" tone={defectTone} />
        <StatCard label="待人工复核" value={data.pending_review_count} hint="需要人工确认的样本" tone={serviceTone} />
        <StatCard label="当前模型版本" value={modelDisplay(activeModel)} hint={activeModel?.framework ?? "当前未启用模型"} />
        <StatCard label="当前数据集版本" value={datasetVersion} hint="来自数据集版本接口" />
        <StatCard label="平均检测耗时" value={formatMs(data.average_latency_ms)} hint="接口返回平均推理耗时" tone="info" />
        <StatCard label="服务运行状态" value="运行中" hint={`ONNX Provider：${valueText(data.onnx_provider)}`} tone="success" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_1.4fr]">
        <section className="card">
          <SectionTitle title="缺陷类型分布" />
          {classEntries.length ? (
            <div className="space-y-4">
              {classEntries.map((item) => (
                <div key={item.name}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-700">{formatDefect(item.name)}</span>
                    <span className="text-slate-500">{item.count}</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100">
                    <div className="h-2 rounded-full bg-sky-600" style={{ width: item.width }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="暂无缺陷分布" description="有真实检测记录后将展示缺陷类型占比。" />
          )}
        </section>

        <section className="card">
          <SectionTitle title="当前部署模型" />
          <DataTable
            rows={activeModels}
            emptyText="暂无启用模型"
            getRowKey={(row) => row.id}
            columns={[
              { key: "type", header: "类型", render: (m) => valueText(m.model_type) },
              { key: "name", header: "名称", render: (m) => valueText(m.model_name) },
              { key: "version", header: "版本", render: (m) => <Badge tone="info">{m.version}</Badge> },
              { key: "framework", header: "框架", render: (m) => valueText(m.framework) },
              { key: "active", header: "状态", render: (m) => <StatusBadge value={m.active ? "active" : "inactive"} /> }
            ]}
          />
        </section>
      </div>

      <section className="card">
        <SectionTitle title="最近检测记录" />
        <DataTable
          rows={recentRecords}
          emptyText="暂无检测记录"
          getRowKey={(row) => row.id}
          columns={[
            { key: "time", header: "检测时间", render: (r) => formatDateTime(r.created_at) },
            { key: "status", header: "最终判定", render: (r) => <StatusBadge value={r.final_status} /> },
            { key: "class", header: "缺陷类别", render: (r) => formatDefect(r.predicted_class) },
            { key: "confidence", header: "置信度", render: (r) => formatConfidence(r.confidence) },
            { key: "review", header: "复核原因", render: (r) => formatArray(r.review_reasons) },
            { key: "latency", header: "耗时", render: (r) => formatMs(r.processing_time_ms) },
            { key: "score", header: "异常分数", render: (r) => formatNumber(r.anomaly_score, 3) }
          ]}
        />
      </section>
    </div>
  );
}
