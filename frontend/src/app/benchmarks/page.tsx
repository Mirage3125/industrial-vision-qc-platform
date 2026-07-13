"use client";

import { useEffect, useMemo, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { DeveloperDetails, EmptyState, ErrorPanel, LoadingState, PageHeader, SectionTitle, StatCard } from "@/components/ProductUI";
import { getBenchmarks } from "@/lib/api";
import { formatDateTime, formatMs, formatNumber, valueText } from "@/lib/format";

type BenchmarkReport = Record<string, unknown>;

function objectOf(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function reportOf(row: BenchmarkReport): Record<string, unknown> {
  return objectOf(row.report).created_at !== undefined || objectOf(row.report).results !== undefined ? objectOf(row.report) : row;
}

function getMetric(row: BenchmarkReport, keys: string[]): unknown {
  const report = reportOf(row);
  const metrics = objectOf(row.metrics);
  const reportMetrics = objectOf(report.metrics);
  const summary = objectOf(report.summary);
  const statistics = objectOf(report.statistics);
  const latency = objectOf(report.latency);
  const percentiles = objectOf(report.percentiles);
  const throughput = objectOf(report.throughput);
  const sources = [metrics, reportMetrics, report, summary, statistics, latency, percentiles, throughput];

  for (const key of keys) {
    for (const source of sources) {
      if (source[key] !== undefined) return source[key];
    }
  }
  return undefined;
}

function formatRate(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return valueText(value);
  return formatNumber(value <= 1 ? value * 100 : value, 2, "%");
}

export default function BenchmarksPage() {
  const [rows, setRows] = useState<BenchmarkReport[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getBenchmarks()
      .then((data) => setRows(data.reports))
      .catch((err: Error) => setError(err.message));
  }, []);

  const latest = useMemo(() => rows?.[0], [rows]);

  if (error) return <ErrorPanel message={error} />;
  if (!rows) return <LoadingState />;

  return (
    <div className="space-y-6">
      <PageHeader title="性能评测" description="展示真实评测报告中的推理耗时、分位数、吞吐量、成功率和错误率。" />
      {latest ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
          <StatCard label="平均耗时" value={formatMs(getMetric(latest, ["average_latency_ms", "avg_ms", "mean_ms", "average_ms"]))} />
          <StatCard label="P50" value={formatMs(getMetric(latest, ["p50_latency_ms", "p50_ms", "latency_p50_ms", "p50", "50"]))} />
          <StatCard label="P95" value={formatMs(getMetric(latest, ["p95_latency_ms", "p95_ms", "latency_p95_ms", "p95", "95"]))} />
          <StatCard label="吞吐量" value={formatNumber(getMetric(latest, ["throughput_images_per_second", "throughput", "throughput_qps", "fps"]), 2, " /s")} />
          <StatCard label="成功率" value={formatRate(getMetric(latest, ["success_rate"]))} tone="success" />
          <StatCard label="错误率" value={formatRate(getMetric(latest, ["error_rate"]))} tone="warning" />
        </div>
      ) : (
        <EmptyState title="暂无性能评测数据" description="有真实 benchmark 报告后将展示指标卡和趋势。" />
      )}
      <section className="card">
        <SectionTitle title="评测报告列表" />
        <DataTable
          rows={rows}
          emptyText="暂无性能评测报告"
          columns={[
            { key: "name", header: "报告", render: (r) => valueText(r.name ?? r.path) },
            { key: "avg", header: "平均耗时", render: (r) => formatMs(getMetric(r, ["average_latency_ms", "avg_ms", "mean_ms", "average_ms"])) },
            { key: "p50", header: "P50", render: (r) => formatMs(getMetric(r, ["p50_latency_ms", "p50_ms", "latency_p50_ms", "p50", "50"])) },
            { key: "p95", header: "P95", render: (r) => formatMs(getMetric(r, ["p95_latency_ms", "p95_ms", "latency_p95_ms", "p95", "95"])) },
            { key: "throughput", header: "吞吐量", render: (r) => formatNumber(getMetric(r, ["throughput_images_per_second", "throughput", "throughput_qps", "fps"]), 2, " /s") },
            { key: "success", header: "成功率", render: (r) => formatRate(getMetric(r, ["success_rate"])) },
            { key: "error", header: "错误率", render: (r) => formatRate(getMetric(r, ["error_rate"])) },
            { key: "time", header: "生成时间", render: (r) => formatDateTime(getMetric(r, ["generated_at", "created_at"])) }
          ]}
        />
      </section>
      <DeveloperDetails data={rows} title="完整评测报告" />
    </div>
  );
}
