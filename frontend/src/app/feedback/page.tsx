"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { DeveloperDetails, ErrorPanel, LoadingState, PageHeader, SectionTitle, StatCard, StatusBadge, SuccessPanel } from "@/components/ProductUI";
import { exportFeedback, getFeedback } from "@/lib/api";
import { formatDateTime, formatDefect, valueText } from "@/lib/format";
import type { FeedbackSample } from "@/lib/types";

export default function FeedbackPage() {
  const [rows, setRows] = useState<FeedbackSample[] | null>(null);
  const [version, setVersion] = useState("feedback-manual-version");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function refresh() {
    setRows((await getFeedback()).samples);
  }

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const data = await getFeedback();
        if (active) setRows(data.samples);
      } catch (err) {
        if (active) setError((err as Error).message);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, []);

  async function runExport() {
    if (submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const result = await exportFeedback({ dataset_version: version, export_operator: "frontend" });
      setMessage(`导出完成，数据集版本：${valueText((result as { dataset_version?: unknown }).dataset_version ?? version)}`);
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  if (error && !rows) return <ErrorPanel message={error} />;
  if (!rows) return <LoadingState />;

  const exported = rows.filter((row) => row.export_status === "exported").length;

  return (
    <div className="space-y-6">
      <PageHeader title="反馈样本" description="汇总人工复核产生的纠正样本，用于导出新数据集版本并支撑模型迭代。" />
      {message && <SuccessPanel message={message} />}
      {error && <ErrorPanel message={error} />}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="反馈样本数" value={rows.length} />
        <StatCard label="已导出" value={exported} tone="success" />
        <StatCard label="未导出" value={rows.length - exported} tone={rows.length - exported ? "warning" : "success"} />
      </div>
      <section className="card grid gap-3 md:grid-cols-[1fr_160px]">
        <input className="input" value={version} onChange={(event) => setVersion(event.target.value)} placeholder="数据集版本号" />
        <button className="btn" disabled={submitting || !version.trim()} onClick={() => void runExport()}>
          {submitting ? "导出中..." : "导出版本"}
        </button>
      </section>
      <section className="card">
        <SectionTitle title="样本列表" />
        <DataTable
          rows={rows}
          emptyText="暂无反馈样本"
          getRowKey={(row) => row.id}
          columns={[
            { key: "status", header: "状态", render: (r) => <StatusBadge value={r.export_status} /> },
            { key: "type", header: "反馈类型", render: (r) => valueText(r.feedback_type) },
            { key: "orig", header: "原始标签", render: (r) => formatDefect(r.original_label) },
            { key: "corr", header: "修正标签", render: (r) => formatDefect(r.corrected_label) },
            { key: "dataset", header: "数据集版本", render: (r) => valueText(r.dataset_version_id) },
            { key: "time", header: "创建时间", render: (r) => formatDateTime(r.created_at) }
          ]}
        />
      </section>
      <DeveloperDetails data={rows.map((row) => ({ id: row.id, inspection_id: row.inspection_id, image_path: row.image_path }))} title="样本内部引用" />
    </div>
  );
}
