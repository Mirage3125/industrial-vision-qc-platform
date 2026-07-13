"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { DeveloperDetails, ErrorPanel, LoadingState, PageHeader, SectionTitle, StatCard, StatusBadge } from "@/components/ProductUI";
import { getDatasets } from "@/lib/api";
import { formatArray, formatDateTime, valueText } from "@/lib/format";

type DatasetVersion = Record<string, unknown>;

function distributionText(value: unknown): string {
  if (!value || typeof value !== "object" || Array.isArray(value)) return "—";
  return formatArray(
    Object.entries(value as Record<string, unknown>).map(([key, count]) => `${key}: ${count}`),
    " / "
  );
}

export default function DatasetsPage() {
  const [rows, setRows] = useState<DatasetVersion[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getDatasets()
      .then((data) => setRows(data.versions))
      .catch((err: Error) => setError(err.message));
  }, []);

  if (error) return <ErrorPanel message={error} />;
  if (!rows) return <LoadingState />;

  const current = rows[0];

  return (
    <div className="space-y-6">
      <PageHeader title="数据集版本" description="展示反馈样本沉淀后的数据集版本、样本量、类别分布和当前使用状态。" />
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="版本数量" value={rows.length} />
        <StatCard label="当前版本" value={valueText(current?.version ?? current?.id)} tone="info" />
        <StatCard label="样本量" value={valueText(current?.sample_count)} />
      </div>
      <section className="card">
        <SectionTitle title="版本列表" />
        <DataTable
          rows={rows}
          emptyText="暂无数据集版本"
          columns={[
            { key: "version", header: "版本号", render: (r) => valueText(r.version ?? r.id) },
            { key: "time", header: "创建时间", render: (r) => formatDateTime(r.created_at) },
            { key: "count", header: "样本量", render: (r) => valueText(r.sample_count) },
            { key: "dist", header: "类别分布", render: (r) => distributionText(r.class_distribution) },
            { key: "status", header: "状态", render: (r, index) => <StatusBadge value={index === 0 || r.active ? "active" : "inactive"} /> }
          ]}
        />
      </section>
      <DeveloperDetails data={rows} title="metadata 与内部路径" />
    </div>
  );
}
