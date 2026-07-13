"use client";

import {
  type ChangeEvent,
  type DragEvent,
  forwardRef,
  type InputHTMLAttributes,
  useRef,
  useState
} from "react";
import { DataTable } from "@/components/DataTable";
import { Badge, ErrorPanel, PageHeader, SectionTitle, StatCard, StatusBadge } from "@/components/ProductUI";
import { uploadPredict } from "@/lib/api";
import { formatConfidence, formatDefect, valueText } from "@/lib/format";
import type { InspectionResult } from "@/lib/types";

const MAX_BATCH_FILES = 50;
const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const ACCEPTED_EXTENSIONS = new Set(["jpg", "jpeg", "png", "webp"]);

type BatchStatus = "pending" | "running" | "completed" | "failed";
type ValidationStatus = "valid" | "invalid";

type DirectoryInputProps = InputHTMLAttributes<HTMLInputElement> & {
  webkitdirectory?: string;
};

type BatchRow = {
  id: string;
  file: File;
  previewUrl: string;
  relativePath?: string;
  validation: ValidationStatus;
  validationMessage: string;
  status: BatchStatus;
  result?: InspectionResult;
  error?: string;
};

const DirectoryInput = forwardRef<HTMLInputElement, DirectoryInputProps>(function DirectoryInput(props, ref) {
  return <input ref={ref} {...props} />;
});

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
    reader.onerror = () => reject(new Error("读取文件失败"));
    reader.readAsDataURL(file);
  });
}

function fileKey(file: File): string {
  return `${file.name}-${file.size}-${file.lastModified}`;
}

function makeBatchId(): string {
  const now = new Date();
  const date = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}`;
  const sequence = String(Math.floor((Date.now() / 1000) % 1000)).padStart(3, "0");
  return `BATCH-${date}-${sequence}`;
}

function hashText(value: string): string {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash.toString(36);
}

function idempotencyKey(batchId: string, row: BatchRow, index: number): string {
  return `${batchId}-${String(index + 1).padStart(3, "0")}-${hashText(row.id)}`;
}

function fileSizeText(file: File): string {
  return `${(file.size / 1024 / 1024).toFixed(2)} MB`;
}

function fileExtension(file: File): string {
  const name = file.name.toLowerCase();
  const index = name.lastIndexOf(".");
  return index >= 0 ? name.slice(index + 1) : "";
}

function isHiddenPath(file: File): boolean {
  const path = file.webkitRelativePath || file.name;
  return path.split("/").some((part) => part.startsWith("."));
}

function isSupportedImage(file: File): boolean {
  return ACCEPTED_TYPES.has(file.type) || ACCEPTED_EXTENSIONS.has(fileExtension(file));
}

function rowStatusValue(status: BatchStatus): string {
  if (status === "completed") return "COMPLETED";
  if (status === "failed") return "DEFECT";
  return "PENDING";
}

function rowStatusLabel(status: BatchStatus): string {
  if (status === "pending") return "待处理";
  if (status === "running") return "处理中";
  if (status === "completed") return "已完成";
  return "失败";
}

function createRow(file: File): BatchRow {
  const oversize = file.size > MAX_FILE_SIZE;
  return {
    id: fileKey(file),
    file,
    previewUrl: URL.createObjectURL(file),
    relativePath: file.webkitRelativePath || undefined,
    validation: oversize ? "invalid" : "valid",
    validationMessage: oversize ? `单文件不能超过 ${MAX_FILE_SIZE / 1024 / 1024} MB` : "可检测",
    status: "pending"
  };
}

export default function BatchPage() {
  const [rows, setRows] = useState<BatchRow[]>([]);
  const [running, setRunning] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const folderInputRef = useRef<HTMLInputElement | null>(null);
  const batchIdRef = useRef<string | null>(null);

  const validRows = rows.filter((row) => row.validation === "valid");
  const processed = validRows.filter((row) => row.status === "completed" || row.status === "failed").length;
  const completed = validRows.filter((row) => row.status === "completed").length;
  const failed = validRows.filter((row) => row.status === "failed").length;

  const batchId = validRows.length && batchIdRef.current ? batchIdRef.current : "—";

  function appendFiles(files: FileList | File[] | null, source: "files" | "folder" | "drop") {
    const incoming = Array.from(files ?? []);
    if (!incoming.length) return;

    let summary = "";
    setRows((current) => {
      const currentKeys = new Set(current.map((row) => row.id));
      const nextRows: BatchRow[] = [];
      let ignored = 0;
      let duplicated = 0;
      let limited = 0;

      for (const file of incoming) {
        if (isHiddenPath(file) || !isSupportedImage(file)) {
          ignored += 1;
          continue;
        }

        const key = fileKey(file);
        if (currentKeys.has(key) || nextRows.some((row) => row.id === key)) {
          duplicated += 1;
          continue;
        }

        if (current.length + nextRows.length >= MAX_BATCH_FILES) {
          limited += 1;
          continue;
        }

        nextRows.push(createRow(file));
      }

      const sourceText = source === "folder" ? "文件夹" : source === "drop" ? "拖拽" : "文件";
      const messages = [`通过${sourceText}追加 ${nextRows.length} 张图片`];
      if (ignored) messages.push(`已忽略 ${ignored} 个隐藏或非图片文件`);
      if (duplicated) messages.push(`已去重 ${duplicated} 个重复文件`);
      if (limited) messages.push(`已超出上限 ${MAX_BATCH_FILES} 张，忽略 ${limited} 个文件`);
      summary = messages.join("，");

      if (!batchIdRef.current && current.length + nextRows.length > 0) {
        batchIdRef.current = makeBatchId();
      }

      return [...current, ...nextRows];
    });

    setNotice(summary);
    setError("");
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    appendFiles(event.currentTarget.files, "files");
    event.currentTarget.value = "";
  }

  function handleFolderChange(event: ChangeEvent<HTMLInputElement>) {
    appendFiles(event.currentTarget.files, "folder");
    event.currentTarget.value = "";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);
    appendFiles(event.dataTransfer.files, "drop");
  }

  function removeRow(id: string) {
    setRows((current) => {
      const target = current.find((row) => row.id === id);
      if (target) URL.revokeObjectURL(target.previewUrl);
      const nextRows = current.filter((row) => row.id !== id);
      if (!nextRows.length) batchIdRef.current = null;
      return nextRows;
    });
  }

  async function run(indexes?: number[]) {
    if (running) return;
    const targets =
      indexes ??
      rows
        .map((row, index) => ({ row, index }))
        .filter(({ row }) => row.validation === "valid" && row.status !== "completed")
        .map(({ index }) => index);

    if (!targets.length) {
      setError("没有可提交的有效图片");
      return;
    }

    setRunning(true);
    setError("");
    setNotice("");

    for (const index of targets) {
      const row = rows[index];
      if (!row || row.validation !== "valid") continue;

      setRows((current) =>
        current.map((item) =>
          item.id === row.id ? { ...item, status: "running", error: undefined, result: undefined } : item
        )
      );

      try {
        const requestBatchId = batchIdRef.current ?? makeBatchId();
        batchIdRef.current = requestBatchId;
        const result = await uploadPredict({
          filename: row.file.name,
          content_base64: await toBase64(row.file),
          inference_mode: "hybrid",
          batch_id: requestBatchId,
          idempotency_key: idempotencyKey(requestBatchId, row, index)
        });
        setRows((current) =>
          current.map((item) => (item.id === row.id ? { ...item, status: "completed", result } : item))
        );
      } catch (err) {
        setRows((current) =>
          current.map((item) =>
            item.id === row.id ? { ...item, status: "failed", error: (err as Error).message } : item
          )
        );
      }
    }

    setRunning(false);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="批量检测"
        description="批量追加图片后逐张执行检测，单张失败不会中断整个批次，并展示每张图片的任务状态和结果摘要。"
      />

      {error && <ErrorPanel message={error} />}
      {notice && <div className="rounded-lg border border-sky-200 bg-sky-50 p-4 text-sm text-sky-700">{notice}</div>}

      <section className="card space-y-4">
        <SectionTitle title="上传图片队列" />
        <input
          ref={fileInputRef}
          className="hidden"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          onChange={handleFileChange}
        />
        <DirectoryInput
          ref={folderInputRef}
          className="hidden"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          webkitdirectory=""
          onChange={handleFolderChange}
        />

        <div
          className={`rounded-lg border border-dashed p-6 transition ${
            dragActive ? "border-sky-400 bg-sky-50" : "border-slate-300 bg-slate-50"
          }`}
          onDragOver={(event) => {
            event.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
        >
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="text-base font-semibold text-slate-950">拖入多张图片或选择批量来源</div>
              <div className="mt-1 text-sm text-slate-500">
                支持 JPG、JPEG、PNG、WEBP，单张不超过 {MAX_FILE_SIZE / 1024 / 1024} MB，单批最多 {MAX_BATCH_FILES} 张。
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <button className="btn-secondary" type="button" onClick={() => fileInputRef.current?.click()} disabled={running}>
                选择多张图片
              </button>
              <button className="btn-secondary" type="button" onClick={() => folderInputRef.current?.click()} disabled={running}>
                选择文件夹
              </button>
            </div>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-5">
          <StatCard label="批次编号" value={<span className="break-all text-base">{batchId}</span>} />
          <StatCard label="文件数量" value={rows.length} />
          <StatCard label="有效图片" value={validRows.length} tone="info" />
          <StatCard label="总进度" value={`${processed} / ${validRows.length}`} tone={running ? "warning" : "neutral"} />
          <StatCard label="失败" value={failed} tone={failed ? "danger" : "success"} />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button className="btn" disabled={!validRows.length || running} onClick={() => void run()}>
            {running ? `处理中 ${processed} / ${validRows.length}` : "提交批量检测"}
          </button>
          <span className="text-sm text-slate-500">已完成 {completed} 张，失败 {failed} 张。</span>
        </div>
      </section>

      <section className="card">
        <SectionTitle title="任务明细" />
        <DataTable
          rows={rows}
          emptyText="请先选择或拖入需要检测的图片"
          getRowKey={(row) => row.id}
          columns={[
            {
              key: "preview",
              header: "预览",
              render: (row) => (
                <img
                  className="h-14 w-20 rounded-md border border-slate-200 object-contain"
                  src={row.previewUrl}
                  alt={row.file.name}
                />
              )
            },
            {
              key: "file",
              header: "文件名",
              render: (row) => (
                <div>
                  <div className="max-w-sm truncate font-medium text-slate-800" title={row.relativePath ?? row.file.name}>
                    {row.relativePath ?? row.file.name}
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{fileSizeText(row.file)}</div>
                </div>
              )
            },
            {
              key: "validation",
              header: "校验",
              render: (row) => (
                <div className="space-y-1">
                  <Badge tone={row.validation === "valid" ? "success" : "danger"}>
                    {row.validation === "valid" ? "有效" : "不可用"}
                  </Badge>
                  <div className="text-xs text-slate-500">{row.validationMessage}</div>
                </div>
              )
            },
            {
              key: "status",
              header: "状态",
              render: (row) => (
                <div className="space-y-1">
                  <StatusBadge value={rowStatusValue(row.status)} />
                  <div className="text-xs text-slate-500">{rowStatusLabel(row.status)}</div>
                </div>
              )
            },
            { key: "result", header: "结果", render: (row) => (row.result ? <StatusBadge value={row.result.final_status} /> : valueText(row.error)) },
            { key: "class", header: "缺陷类别", render: (row) => formatDefect(row.result?.predicted_class) },
            { key: "confidence", header: "置信度", render: (row) => formatConfidence(row.result?.confidence) },
            {
              key: "ops",
              header: "操作",
              render: (row, index) => (
                <div className="flex flex-wrap gap-2">
                  <button
                    className="btn-secondary"
                    disabled={running || row.validation !== "valid" || row.status !== "failed"}
                    onClick={() => void run([index])}
                  >
                    重试
                  </button>
                  <button className="btn-secondary" disabled={running && row.status === "running"} onClick={() => removeRow(row.id)}>
                    移除
                  </button>
                </div>
              )
            }
          ]}
        />
      </section>
    </div>
  );
}
