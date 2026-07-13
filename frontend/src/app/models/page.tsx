"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/DataTable";
import {
  ConfirmDialog,
  DeveloperDetails,
  ErrorPanel,
  LoadingState,
  PageHeader,
  SectionTitle,
  StatCard,
  StatusBadge,
  SuccessPanel
} from "@/components/ProductUI";
import { activateModel, getModels } from "@/lib/api";
import { formatNumber, valueText } from "@/lib/format";
import type { ModelVersion } from "@/lib/types";

type PendingOp = { id: string; action: "activate" | "rollback"; label: string } | null;

function metricText(metrics: Record<string, unknown> | undefined): string {
  if (!metrics || !Object.keys(metrics).length) return "—";
  return Object.entries(metrics)
    .slice(0, 3)
    .map(([key, value]) => `${key.replaceAll("_", " ")}: ${typeof value === "number" ? formatNumber(value, 3) : valueText(value)}`)
    .join(" / ");
}

export default function ModelsPage() {
  const [rows, setRows] = useState<ModelVersion[] | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState<PendingOp>(null);
  const [submitting, setSubmitting] = useState(false);

  async function refresh() {
    setRows((await getModels()).models);
  }

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const data = await getModels();
        if (active) setRows(data.models);
      } catch (err) {
        if (active) setError((err as Error).message);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, []);

  async function op() {
    if (!pending || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      await activateModel(pending.id, pending.action);
      await refresh();
      setMessage(`${pending.label}操作已完成。`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
      setPending(null);
    }
  }

  if (error && !rows) return <ErrorPanel message={error} />;
  if (!rows) return <LoadingState />;

  const activeCount = rows.filter((row) => row.active).length;

  return (
    <div className="space-y-6">
      <PageHeader title="模型版本" description="管理生产检测链路中的模型版本、框架、指标和当前启用状态。" />
      {message && <SuccessPanel message={message} />}
      {error && <ErrorPanel message={error} />}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="模型版本数" value={rows.length} />
        <StatCard label="当前启用" value={activeCount} tone={activeCount ? "success" : "warning"} />
        <StatCard label="模型类型" value={new Set(rows.map((row) => row.model_type)).size} />
      </div>
      <section className="card">
        <SectionTitle title="版本列表" />
        <DataTable
          rows={rows}
          getRowKey={(row) => row.id}
          emptyText="暂无模型版本"
          columns={[
            { key: "type", header: "类型", render: (r) => valueText(r.model_type) },
            { key: "name", header: "名称", render: (r) => valueText(r.model_name) },
            { key: "version", header: "版本", render: (r) => valueText(r.version) },
            { key: "framework", header: "框架", render: (r) => valueText(r.framework) },
            { key: "metrics", header: "指标", render: (r) => metricText(r.metrics) },
            { key: "active", header: "状态", render: (r) => <StatusBadge value={r.active ? "active" : "inactive"} /> },
            {
              key: "ops",
              header: "操作",
              render: (r) => (
                <div className="flex gap-2">
                  <button className="btn-secondary" disabled={submitting || r.active} onClick={() => setPending({ id: r.id, action: "activate", label: "激活" })}>
                    激活
                  </button>
                  <button className="btn-secondary" disabled={submitting} onClick={() => setPending({ id: r.id, action: "rollback", label: "回滚" })}>
                    回滚
                  </button>
                </div>
              )
            }
          ]}
        />
      </section>
      <DeveloperDetails data={rows.map((row) => ({ id: row.id, path: row.model_path, metrics: row.metrics }))} title="内部路径与完整指标" />
      <ConfirmDialog
        open={pending !== null}
        title={`确认${pending?.label ?? ""}模型版本？`}
        description="该操作会改变生产检测链路使用的模型版本，请确认当前版本符合预期。"
        confirmText={submitting ? "提交中..." : "确认"}
        onCancel={() => setPending(null)}
        onConfirm={() => void op()}
      />
    </div>
  );
}
