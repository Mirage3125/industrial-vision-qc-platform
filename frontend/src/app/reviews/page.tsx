"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { ErrorPanel, LoadingState, PageHeader, StatusBadge } from "@/components/ProductUI";
import { getReviews } from "@/lib/api";
import { formatArray, formatDateTime, formatList } from "@/lib/format";
import type { ReviewSummary } from "@/lib/types";

export default function ReviewsPage() {
  const [rows, setRows] = useState<ReviewSummary[] | null>(null);
  const [status, setStatus] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    getReviews()
      .then((data) => setRows(data.reviews))
      .catch((err: Error) => setError(err.message));
  }, []);

  const filtered = useMemo(
    () =>
      (rows ?? []).filter(
        (row) =>
          (!status || row.review_status === status) &&
          (!reason.trim() || formatArray(row.review_reasons, " ", "").toLowerCase().includes(reason.trim().toLowerCase()))
      ),
    [rows, status, reason]
  );

  if (error) return <ErrorPanel message={error} />;
  if (!rows) return <LoadingState />;

  return (
    <div className="space-y-6">
      <PageHeader title="人工复核" description="集中处理模型不确定、质量异常或业务规则要求人工确认的样本。" />
      <section className="card grid gap-3 md:grid-cols-[220px_1fr_120px]">
        <select className="input" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">全部状态</option>
          <option value="pending">待处理</option>
          <option value="approved">确认缺陷</option>
          <option value="corrected">已修正</option>
          <option value="rejected">判定正常</option>
        </select>
        <input className="input" placeholder="搜索复核原因" value={reason} onChange={(event) => setReason(event.target.value)} />
        <button className="btn-secondary" type="button" onClick={() => { setStatus(""); setReason(""); }}>
          重置
        </button>
      </section>
      <DataTable
        rows={filtered}
        emptyText="没有匹配的复核任务"
        getRowKey={(row) => row.id}
        columns={[
          {
            key: "id",
            header: "任务",
            render: (r) => (
              <Link className="font-medium text-sky-700 hover:text-sky-900" href={`/reviews/${r.id}`}>
                {r.id.slice(0, 8)}
              </Link>
            )
          },
          { key: "status", header: "状态", render: (r) => <StatusBadge value={r.review_status} /> },
          { key: "reason", header: "复核原因", render: (r) => formatList(r.review_reasons) },
          { key: "time", header: "创建时间", render: (r) => formatDateTime(r.created_at) },
          {
            key: "ops",
            header: "操作",
            render: (r) => (
              <Link className="btn-secondary" href={`/reviews/${r.id}`}>
                查看详情
              </Link>
            )
          }
        ]}
      />
    </div>
  );
}
