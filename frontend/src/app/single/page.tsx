"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { DataTable } from "@/components/DataTable";
import { InspectionImage } from "@/components/InspectionImage";
import {
  Badge,
  DeveloperDetails,
  EmptyState,
  ErrorPanel,
  PageHeader,
  SectionTitle,
  StatCard,
  StatusBadge
} from "@/components/ProductUI";
import { fileUrl, uploadPredict } from "@/lib/api";
import {
  boxText,
  formatConfidence,
  formatDefect,
  formatList,
  formatMs,
  formatNumber,
  formatTaskType,
  regionArea,
  regionRatio,
  valueText
} from "@/lib/format";
import type { InspectionResult, YoloRegion } from "@/lib/types";

const modes = ["hybrid", "detection", "anomaly", "classical"];

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
    reader.onerror = () => reject(new Error("读取文件失败"));
    reader.readAsDataURL(file);
  });
}

function totalMs(timings?: Record<string, number> | null): number | null {
  const values = Object.values(timings ?? {}).filter((value) => Number.isFinite(value));
  return values.length ? values.reduce((sum, value) => sum + value, 0) : null;
}

export default function SinglePage() {
  const [file, setFile] = useState<File | null>(null);
  const [dimensions, setDimensions] = useState("");
  const [mode, setMode] = useState("hybrid");
  const [result, setResult] = useState<InspectionResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  function chooseFile(nextFile: File | null) {
    setFile(nextFile);
    setResult(null);
    setError("");
    setDimensions("");
    if (!nextFile) return;
    const url = URL.createObjectURL(nextFile);
    const image = new Image();
    image.onload = () => {
      setDimensions(`${image.naturalWidth} x ${image.naturalHeight}`);
      URL.revokeObjectURL(url);
    };
    image.src = url;
  }

  async function submit() {
    if (!file || loading) return;
    if (!/^image\//.test(file.type) || file.size > 10 * 1024 * 1024) {
      setError("仅支持 10MB 以内的图片文件。");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const content = await toBase64(file);
      const nextResult = await uploadPredict({
        filename: file.name,
        content_base64: content,
        inference_mode: mode,
        idempotency_key: `${file.name}-${file.size}-${file.lastModified}`
      });
      setResult(nextResult);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const regions: YoloRegion[] = Array.isArray(result?.yolo_result?.regions)
    ? result.yolo_result.regions
    : Array.isArray(result?.yolo_regions)
      ? result.yolo_regions
      : [];
  const reviewReasons = Array.isArray(result?.review_reasons) ? result.review_reasons : [];
  const imageSrc = fileUrl(result?.image_path) ?? preview;
  const heatmap = fileUrl(String(result?.anomaly_result?.heatmap_path ?? ""));
  const noDefect = result && result.final_status?.toUpperCase() === "NORMAL" && regions.length === 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="单图检测"
        description="上传图片后选择检测任务，系统将返回模型判定、缺陷区域、置信度和是否需要进入人工复核。"
      />
      {error && <ErrorPanel message={error} />}

      <section className="card">
        <SectionTitle title="检测流程" />
        <div className="grid gap-4 text-sm text-slate-600 md:grid-cols-5">
          {["上传图片", "选择检测任务", "开始检测", "查看检测结果", "进入复核闭环"].map((step, index) => (
            <div key={step} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div className="mb-2 flex h-7 w-7 items-center justify-center rounded-full bg-sky-600 text-xs font-semibold text-white">
                {index + 1}
              </div>
              {step}
            </div>
          ))}
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <section className="card">
          <SectionTitle title="图片上传" />
          <label
            className="flex min-h-80 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-6 text-center transition hover:border-sky-400 hover:bg-sky-50/40"
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              chooseFile(event.dataTransfer.files?.[0] ?? null);
            }}
          >
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
            />
            {preview ? (
              <img src={preview} alt="上传预览" className="max-h-72 rounded-lg object-contain" />
            ) : (
              <>
                <div className="text-base font-medium text-slate-800">拖拽图片到此处，或点击选择文件</div>
                <div className="mt-2 text-sm text-slate-500">支持 JPG、PNG、BMP、WEBP，单张不超过 10MB</div>
              </>
            )}
          </label>
          {file && (
            <div className="mt-4 grid gap-3 rounded-lg border border-slate-200 bg-white p-4 text-sm md:grid-cols-4">
              <div>
                <div className="label">文件名</div>
                <div className="mt-1 truncate text-slate-800" title={file.name}>
                  {file.name}
                </div>
              </div>
              <div>
                <div className="label">文件大小</div>
                <div className="mt-1 text-slate-800">{(file.size / 1024 / 1024).toFixed(2)} MB</div>
              </div>
              <div>
                <div className="label">图片尺寸</div>
                <div className="mt-1 text-slate-800">{valueText(dimensions)}</div>
              </div>
              <div className="flex items-end gap-2">
                <label className="btn-secondary cursor-pointer">
                  重新选择
                  <input type="file" accept="image/*" className="hidden" onChange={(event) => chooseFile(event.target.files?.[0] ?? null)} />
                </label>
                <button className="btn-secondary" type="button" onClick={() => chooseFile(null)}>
                  清除
                </button>
              </div>
            </div>
          )}
        </section>

        <section className="card">
          <SectionTitle title="检测任务" />
          <div className="space-y-4">
            <div>
              <label className="label">任务类型</label>
              <select className="input mt-1" value={mode} onChange={(event) => setMode(event.target.value)}>
                {modes.map((item) => (
                  <option key={item} value={item}>
                    {formatTaskType(item)}
                  </option>
                ))}
              </select>
            </div>
            <button className="btn w-full" disabled={!file || loading} onClick={() => void submit()}>
              {loading ? "检测中..." : "开始检测"}
            </button>
            {!file && <div className="text-sm text-slate-500">请先上传图片后再开始检测。</div>}
          </div>
        </section>
      </div>

      {result && (
        <section className="card space-y-5">
          <SectionTitle
            title="检测结果"
            extra={result.review_id ? <Link className="btn-secondary" href={`/reviews/${result.review_id}`}>进入人工复核</Link> : <Badge tone="success">无需复核</Badge>}
          />
          <div className="grid gap-6 xl:grid-cols-[1.35fr_0.9fr]">
            <div>
              <InspectionImage src={imageSrc} regions={regions} />
              {heatmap && <img src={heatmap} alt="异常热力图" className="mt-4 max-h-80 rounded-lg border border-slate-200 object-contain" />}
            </div>
            <div className="grid content-start gap-4 sm:grid-cols-2">
              <StatCard label="最终判定" value={<StatusBadge value={result.final_status} />} tone={result.final_status === "NORMAL" ? "success" : "danger"} />
              <StatCard label="缺陷类别" value={formatDefect(result.predicted_class)} />
              <StatCard label="综合置信度" value={formatConfidence(result.confidence)} tone="info" />
              <StatCard label="异常区域数量" value={regions.length} tone={regions.length ? "danger" : "success"} />
              <StatCard label="是否需要复核" value={result.requires_review ? "是" : "否"} tone={result.requires_review ? "warning" : "success"} />
              <StatCard label="检测耗时" value={formatMs(totalMs(result.step_timings))} />
              <div className="sm:col-span-2">
                <StatCard label="复核原因" value={formatList(reviewReasons)} tone={reviewReasons.length ? "warning" : "success"} />
              </div>
            </div>
          </div>

          {noDefect ? (
            <EmptyState title="未发现明显缺陷" description="模型判定为正常，且接口未返回可绘制的缺陷区域。" />
          ) : (
            <div>
              <SectionTitle title="缺陷明细" />
              <DataTable
                rows={regions}
                emptyText="接口未返回缺陷区域"
                columns={[
                  { key: "index", header: "序号", render: (_row, index) => index + 1 },
                  { key: "label", header: "类别", render: (row) => formatDefect(row.label ?? row.class_name ?? row.class) },
                  { key: "confidence", header: "置信度", render: (row) => formatConfidence(row.confidence ?? row.score) },
                  { key: "box", header: "坐标", render: (row) => boxText(row) },
                  { key: "area", header: "面积", render: (row) => regionArea(row) },
                  { key: "ratio", header: "长宽比", render: (row) => regionRatio(row) },
                  { key: "score", header: "异常分数", render: (row) => formatNumber(row.anomaly_score, 3) }
                ]}
              />
            </div>
          )}

          <DeveloperDetails
            data={{
              quality: result.quality_result,
              yolo_regions: result.yolo_result?.regions,
              anomaly: result.anomaly_result,
              timings: result.step_timings,
              models: result.model_versions
            }}
          />
        </section>
      )}
    </div>
  );
}
