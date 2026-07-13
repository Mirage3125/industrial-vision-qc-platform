"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { DeveloperDetails, ErrorPanel, LoadingState, PageHeader, SectionTitle, StatCard, StatusBadge } from "@/components/ProductUI";
import { getQualityReports } from "@/lib/api";
import { formatDateTime, formatNumber, valueText } from "@/lib/format";

type QualityReport = Record<string, unknown>;

function objectOf(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function metric(report: QualityReport, key: string): unknown {
  const metrics = objectOf(report.metrics);
  const summary = objectOf(report.summary);
  const statistics = objectOf(report.statistics);
  const sizeStats = objectOf(report.image_size_statistics);
  const widthStats = objectOf(sizeStats.width);
  const heightStats = objectOf(sizeStats.height);
  const sources = [metrics, report, summary, statistics, sizeStats];

  if (key === "width") return metrics.width_mean ?? widthStats.mean ?? report.width;
  if (key === "height") return metrics.height_mean ?? heightStats.mean ?? report.height;
  if (key === "generated_at") return metrics.generated_at ?? report.created_at ?? report.generated_at;

  for (const source of sources) {
    if (source[key] !== undefined) return source[key];
  }
  return undefined;
}

function formatRange(report: QualityReport, prefix: "width" | "height"): string {
  const min = metric(report, `${prefix}_min`);
  const mean = metric(report, `${prefix}_mean`) ?? metric(report, prefix);
  const max = metric(report, `${prefix}_max`);
  if (min === undefined && mean === undefined && max === undefined) return "—";
  return `${valueText(min)} / ${valueText(mean)} / ${valueText(max)}`;
}

function issueFindingCount(report: QualityReport): string {
  return valueText(metric(report, "issue_finding_count") ?? metric(report, "issue_count"));
}

function problemImageCount(report: QualityReport): string {
  const value = metric(report, "problem_image_count");
  if (value !== null && value !== undefined) return valueText(value);
  const sampleCount = metric(report, "issue_sample_count");
  return sampleCount !== null && sampleCount !== undefined ? `样本 ${valueText(sampleCount)}` : "—";
}

export default function QualityPage() {
  const [rows, setRows] = useState<QualityReport[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getQualityReports()
      .then((data) => setRows(data.reports))
      .catch((err: Error) => setError(err.message));
  }, []);

  if (error) return <ErrorPanel message={error} />;
  if (!rows) return <LoadingState />;

  const latest = rows[0] ?? {};

  return (
    <div className="space-y-6">
      <PageHeader title="数据质量" description="将图片有效性、尺寸、模糊度和明暗比例转换为可阅读的数据质量报告。" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard label="总图片数" value={valueText(metric(latest, "total_images"))} />
        <StatCard label="有效图片数" value={valueText(metric(latest, "valid_images"))} tone="success" />
        <StatCard label="问题图片数" value={problemImageCount(latest)} tone="warning" />
        <StatCard label="问题发现数" value={issueFindingCount(latest)} tone="warning" />
        <StatCard label="模糊问题数" value={valueText(metric(latest, "blur_issue_count") ?? metric(latest, "blurry_count"))} />
      </div>
      <section className="card">
        <SectionTitle title="质量报告列表" />
        <DataTable
          rows={rows}
          emptyText="暂无数据质量报告"
          columns={[
            { key: "dataset", header: "数据集", render: (r) => valueText(r.dataset_path ?? r.dataset ?? r.path) },
            { key: "valid", header: "有效", render: (r) => <StatusBadge value={metric(r, "valid") === false ? "DEFECT" : "NORMAL"} /> },
            { key: "total", header: "总图片数", render: (r) => valueText(metric(r, "total_images")) },
            { key: "valid_images", header: "有效图片数", render: (r) => valueText(metric(r, "valid_images")) },
            { key: "problem_images", header: "问题图片数", render: (r) => problemImageCount(r) },
            { key: "issues", header: "问题发现数", render: (r) => issueFindingCount(r) },
            { key: "width", header: "宽度 min/mean/max", render: (r) => formatRange(r, "width") },
            { key: "height", header: "高度 min/mean/max", render: (r) => formatRange(r, "height") },
            { key: "blur", header: "模糊问题数", render: (r) => valueText(metric(r, "blur_issue_count") ?? metric(r, "blurry_count")) },
            { key: "bright", header: "亮区比例", render: (r) => formatNumber(metric(r, "bright_ratio"), 2) },
            { key: "dark", header: "暗区比例", render: (r) => formatNumber(metric(r, "dark_ratio"), 2) },
            { key: "time", header: "生成时间", render: (r) => formatDateTime(metric(r, "generated_at")) }
          ]}
        />
      </section>
      <DeveloperDetails data={rows} title="原始报告路径与内部详情" />
    </div>
  );
}
