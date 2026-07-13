"use client";

import { useEffect, useMemo, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { ErrorPanel, LoadingState, PageHeader, StatusBadge } from "@/components/ProductUI";
import { fileUrl, getRecords } from "@/lib/api";
import { formatArray, formatConfidence, formatDateTime, formatDefect, formatList, formatMs, valueText } from "@/lib/format";
import type { InspectionRecord } from "@/lib/types";

export default function RecordsPage() {
  const [rows, setRows] = useState<InspectionRecord[] | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    getRecords()
      .then((data) => setRows(data.records))
      .catch((err: Error) => setError(err.message));
  }, []);

  const filtered = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    return (rows ?? []).filter((row) => {
      const matchesStatus = !status || row.final_status === status;
      const haystack = formatArray(
        [row.id, row.image_path, row.predicted_class, row.station_id, row.batch_id, formatArray(row.review_reasons, " ", "")],
        " ",
        ""
      ).toLowerCase();
      return matchesStatus && (!keyword || haystack.includes(keyword));
    });
  }, [query, rows, status]);

  if (error) return <ErrorPanel message={error} />;
  if (!rows) return <LoadingState />;

  return (
    <div className="space-y-6">
      <PageHeader title="检测记录" description="按时间追踪每张图片的检测结果、缺陷类别、置信度、复核原因和处理耗时。" />
      <section className="card grid gap-3 md:grid-cols-[1fr_220px_120px]">
        <input
          className="input"
          placeholder="搜索图片、类别、工位、批次或复核原因"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <select className="input" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">全部判定</option>
          <option value="NORMAL">正常</option>
          <option value="DEFECT">缺陷</option>
          <option value="REVIEW">待复核</option>
        </select>
        <button className="btn-secondary" type="button" onClick={() => { setQuery(""); setStatus(""); }}>
          重置
        </button>
      </section>
      <DataTable
        rows={filtered}
        emptyText="没有匹配的检测记录"
        getRowKey={(row) => row.id}
        columns={[
          {
            key: "image",
            header: "图片",
            render: (row) => {
              const src = fileUrl(row.image_path);
              return src ? <img src={src} alt="检测图片" className="h-14 w-20 rounded-md object-cover" /> : "—";
            }
          },
          { key: "time", header: "检测时间", render: (r) => formatDateTime(r.created_at) },
          { key: "status", header: "结果", render: (r) => <StatusBadge value={r.final_status} /> },
          { key: "class", header: "缺陷类别", render: (r) => formatDefect(r.predicted_class) },
          { key: "confidence", header: "置信度", render: (r) => formatConfidence(r.confidence) },
          { key: "review", header: "复核状态", render: (r) => (Array.isArray(r.review_reasons) && r.review_reasons.length ? <StatusBadge value="REVIEW" /> : <StatusBadge value="COMPLETED" />) },
          { key: "reason", header: "复核原因", render: (r) => formatList(r.review_reasons) },
          { key: "station", header: "工位", render: (r) => valueText(r.station_id) },
          { key: "batch", header: "批次", render: (r) => valueText(r.batch_id) },
          { key: "latency", header: "耗时", render: (r) => formatMs(r.processing_time_ms) }
        ]}
      />
    </div>
  );
}
