import type { ReactNode } from "react";
import { compactJson, formatStatus, type BadgeTone } from "@/lib/format";

export function PageHeader({
  title,
  description,
  actions
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 border-b border-slate-200 pb-5 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <h2 className="text-2xl font-semibold tracking-normal text-slate-950">{title}</h2>
        {description && <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export function SectionTitle({ title, extra }: { title: string; extra?: ReactNode }) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <h3 className="text-base font-semibold text-slate-950">{title}</h3>
      {extra}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  tone = "neutral"
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: BadgeTone;
}) {
  const toneClass =
    tone === "success"
      ? "border-emerald-200 bg-emerald-50/60"
      : tone === "warning"
        ? "border-amber-200 bg-amber-50/70"
        : tone === "danger"
          ? "border-red-200 bg-red-50/70"
          : tone === "info"
            ? "border-sky-200 bg-sky-50/70"
            : "border-slate-200 bg-white";
  return (
    <div className={`rounded-lg border p-4 shadow-sm ${toneClass}`}>
      <div className="text-xs font-medium uppercase text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-slate-950">{value}</div>
      {hint && <div className="mt-2 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

export function StatusBadge({ value }: { value: unknown }) {
  const status = formatStatus(value);
  return <Badge tone={status.tone}>{status.label}</Badge>;
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: BadgeTone }) {
  const toneClass =
    tone === "success"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : tone === "warning"
        ? "border-amber-200 bg-amber-50 text-amber-800"
        : tone === "danger"
          ? "border-red-200 bg-red-50 text-red-700"
          : tone === "info"
            ? "border-sky-200 bg-sky-50 text-sky-700"
            : "border-slate-200 bg-slate-50 text-slate-700";
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium ${toneClass}`}>
      {children}
    </span>
  );
}

export function EmptyState({ title = "暂无数据", description }: { title?: string; description?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
      <div className="text-sm font-medium text-slate-700">{title}</div>
      {description && <div className="mt-2 text-sm text-slate-500">{description}</div>}
    </div>
  );
}

export function LoadingState({ text = "正在加载数据..." }: { text?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
      <div className="h-2 w-40 animate-pulse rounded bg-slate-200" />
      <div className="mt-4">{text}</div>
    </div>
  );
}

export function ErrorPanel({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      请求失败：{message || "服务暂不可用，请稍后重试。"}
    </div>
  );
}

export function SuccessPanel({ message }: { message: string }) {
  return <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{message}</div>;
}

export function DeveloperDetails({ data, title = "开发者详情" }: { data: unknown; title?: string }) {
  async function copy() {
    await navigator.clipboard.writeText(compactJson(data));
  }

  return (
    <details className="rounded-lg border border-slate-200 bg-slate-50">
      <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-slate-700">{title}</summary>
      <div className="border-t border-slate-200 p-4">
        <button className="btn-secondary mb-3" type="button" onClick={() => void copy()}>
          复制详情
        </button>
        <pre className="max-h-96 overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-5 text-slate-100">
          {compactJson(data)}
        </pre>
      </div>
    </details>
  );
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmText = "确认",
  onConfirm,
  onCancel
}: {
  open: boolean;
  title: string;
  description?: string;
  confirmText?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-4">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-5 shadow-xl">
        <h3 className="text-base font-semibold text-slate-950">{title}</h3>
        {description && <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button className="btn-secondary" type="button" onClick={onCancel}>
            取消
          </button>
          <button className="btn-danger" type="button" onClick={onConfirm}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
