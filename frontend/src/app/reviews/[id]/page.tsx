"use client";

import { use, useEffect, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { InspectionImage } from "@/components/InspectionImage";
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
import { fileUrl, getReview, reviewAction } from "@/lib/api";
import {
  boxText,
  formatArray,
  formatConfidence,
  formatDefect,
  formatList,
  formatMs,
  regionArea,
  regionRatio
} from "@/lib/format";
import type { ReviewDetail } from "@/lib/types";

type ReviewAction = "approve" | "correct" | "reject";

export default function ReviewDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [data, setData] = useState<ReviewDetail | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [reviewer, setReviewer] = useState("qa");
  const [comment, setComment] = useState("");
  const [label, setLabel] = useState("normal");
  const [pendingAction, setPendingAction] = useState<ReviewAction | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getReview(id)
      .then((next) => {
        setData(next);
        setLabel(String(next.original_prediction?.predicted_class ?? next.final_status ?? "normal"));
      })
      .catch((err: Error) => setError(err.message));
  }, [id]);

  async function submit(action: ReviewAction) {
    if (submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const body =
        action === "correct"
          ? {
              reviewer,
              review_comment: comment,
              corrected_label: label,
              feedback_type: "correction",
              corrected_prediction: { label, boxes: Array.isArray(data?.yolo_boxes) ? data.yolo_boxes : [] }
            }
          : { reviewer, review_comment: comment };
      const result = await reviewAction(id, action, body);
      setMessage(`操作已提交，当前状态：${result.status}`);
      setData(await getReview(id));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
      setPendingAction(null);
    }
  }

  if (error && !data) return <ErrorPanel message={error} />;
  if (!data) return <LoadingState />;

  const image = fileUrl(data.image_path);
  const heatmap = fileUrl(data.anomaly_heatmap);
  const yoloBoxes = Array.isArray(data.yolo_boxes) ? data.yolo_boxes : [];
  const reviewReasons = Array.isArray(data.review_reasons) ? data.review_reasons : [];
  const modelVersions = data.model_versions ?? {};
  const stepTimings = data.step_timings ?? {};
  const originalPrediction = data.original_prediction ?? {};
  const history = Array.isArray(data.history) ? data.history : [];
  const confidence = originalPrediction.confidence;
  const confirmTitle =
    pendingAction === "approve" ? "确认该样本为缺陷？" : pendingAction === "reject" ? "确认该样本为正常？" : "确认提交修正结果？";

  return (
    <div className="space-y-6">
      <PageHeader title="复核详情" description="核对原图、检测框、模型判断和复核原因后，提交人工确认结果沉淀为反馈样本。" />
      {message && <SuccessPanel message={message} />}
      {error && <ErrorPanel message={error} />}

      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <section className="card space-y-4">
          <SectionTitle title="原图与检测框" />
          <InspectionImage src={image} regions={yoloBoxes} />
          {heatmap && <img src={heatmap} alt="异常热力图" className="max-h-80 rounded-lg border border-slate-200 object-contain" />}
        </section>

        <section className="card">
          <SectionTitle title="模型判断" />
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
            <StatCard label="复核状态" value={<StatusBadge value={data.review_status} />} />
            <StatCard label="系统判定" value={<StatusBadge value={data.final_status} />} />
            <StatCard label="模型类别" value={formatDefect(originalPrediction.predicted_class)} />
            <StatCard label="置信度" value={formatConfidence(confidence)} tone="info" />
            <StatCard label="检测框数量" value={yoloBoxes.length} tone={yoloBoxes.length ? "danger" : "success"} />
            <StatCard label="检测耗时" value={formatMs(Object.values(stepTimings).reduce((sum, item) => sum + item, 0))} />
            <div className="sm:col-span-2 xl:col-span-1 2xl:col-span-2">
              <StatCard label="复核原因" value={formatList(reviewReasons)} tone={reviewReasons.length ? "warning" : "success"} />
            </div>
          </div>
        </section>
      </div>

      <section className="card">
        <SectionTitle title="缺陷区域明细" />
        <DataTable
          rows={yoloBoxes}
          emptyText="接口未返回检测框"
          columns={[
            { key: "index", header: "序号", render: (_row, index) => index + 1 },
            { key: "label", header: "类别", render: (row) => formatDefect(row.label ?? row.class_name ?? row.class) },
            { key: "confidence", header: "置信度", render: (row) => formatConfidence(row.confidence ?? row.score) },
            { key: "box", header: "坐标", render: (row) => boxText(row) },
            { key: "area", header: "面积", render: (row) => regionArea(row) },
            { key: "ratio", header: "长宽比", render: (row) => regionRatio(row) }
          ]}
        />
      </section>

      <section className="card space-y-4">
        <SectionTitle title="人工操作" />
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="label">复核人</label>
            <input className="input mt-1" value={reviewer} onChange={(event) => setReviewer(event.target.value)} />
          </div>
          <div>
            <label className="label">修正类别</label>
            <input className="input mt-1" value={label} onChange={(event) => setLabel(event.target.value)} placeholder="normal / scratches / crack" />
          </div>
          <div>
            <label className="label">当前版本</label>
            <div className="mt-2 text-sm text-slate-700">{formatArray(Object.values(modelVersions))}</div>
          </div>
          <div className="md:col-span-3">
            <label className="label">备注</label>
            <textarea className="input mt-1 min-h-24" value={comment} onChange={(event) => setComment(event.target.value)} placeholder="填写人工复核依据或修正说明" />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn" disabled={submitting} onClick={() => setPendingAction("approve")}>
            确认缺陷
          </button>
          <button className="btn-secondary" disabled={submitting} onClick={() => setPendingAction("reject")}>
            判定正常
          </button>
          <button className="btn-secondary" disabled={submitting || !label.trim()} onClick={() => setPendingAction("correct")}>
            修改类别并提交
          </button>
        </div>
      </section>

      <DeveloperDetails
        data={{
          boxes: yoloBoxes,
          quality: data.quality_result,
          decision: data.system_decision,
          timings: stepTimings,
          models: modelVersions,
          history
        }}
      />

      <ConfirmDialog
        open={pendingAction !== null}
        title={confirmTitle}
        description="提交后会写入复核结果，并可能进入反馈样本沉淀流程。"
        confirmText={submitting ? "提交中..." : "确认提交"}
        onCancel={() => setPendingAction(null)}
        onConfirm={() => pendingAction && void submit(pendingAction)}
      />
    </div>
  );
}
