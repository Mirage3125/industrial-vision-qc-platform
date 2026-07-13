import type {
  ApiEnvelope,
  FeedbackSample,
  InspectionRecord,
  InspectionResult,
  ModelVersion,
  Overview,
  ReviewDetail,
  ReviewSummary
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {})
      },
      cache: "no-store"
    });
  } catch {
    throw new Error(`无法连接后端服务：${API_BASE}。请确认后端已启动，且 CORS 已允许当前前端地址。`);
  }
  const payload = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || !payload.success) {
    const details = payload.error?.details;
    const detailText =
      details === null || details === undefined
        ? ""
        : typeof details === "string"
          ? details
          : `：${JSON.stringify(details)}`;
    throw new Error(`${payload.error?.message ?? `API request failed: ${response.status}`}${detailText}`);
  }
  return payload.data;
}

export function fileUrl(path?: string | null): string | null {
  if (!path) return null;
  if (/^https?:\/\//.test(path)) return path;
  const normalized = path.replace(/\\/g, "/");
  return `${API_BASE}/files?path=${encodeURIComponent(normalized)}`;
}

export async function getOverview(): Promise<Overview> {
  return request<Overview>("/dashboard/overview");
}

export async function getRecords(): Promise<{ records: InspectionRecord[] }> {
  return request<{ records: InspectionRecord[] }>("/inspection/records");
}

export async function uploadPredict(body: {
  filename: string;
  content_base64: string;
  inference_mode: string;
  model_version?: string;
  station_id?: string;
  batch_id?: string;
  idempotency_key?: string;
  force_review?: boolean;
}): Promise<InspectionResult> {
  return request<InspectionResult>("/inspection/upload-predict", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function getReviews(): Promise<{ reviews: ReviewSummary[] }> {
  return request<{ reviews: ReviewSummary[] }>("/reviews");
}

export async function getReview(id: string): Promise<ReviewDetail> {
  return request<ReviewDetail>(`/reviews/${id}`);
}

export async function reviewAction(
  id: string,
  action: "approve" | "correct" | "reject",
  body: Record<string, unknown>
): Promise<{ review_id: string; status: string }> {
  return request<{ review_id: string; status: string }>(`/reviews/${id}/${action}`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function getFeedback(): Promise<{ samples: FeedbackSample[] }> {
  return request<{ samples: FeedbackSample[] }>("/feedback");
}

export async function exportFeedback(body: {
  dataset_version: string;
  export_operator: string;
  output_root?: string;
}): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/feedback/export", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function getModels(): Promise<{ models: ModelVersion[] }> {
  return request<{ models: ModelVersion[] }>("/models");
}

export async function activateModel(id: string, action: "activate" | "rollback"): Promise<unknown> {
  return request(`/models/${id}/${action}`, {
    method: "POST",
    body: JSON.stringify({ operator: "frontend" })
  });
}

export async function getDatasets(): Promise<{ versions: Array<Record<string, unknown>> }> {
  return request<{ versions: Array<Record<string, unknown>> }>("/datasets/versions");
}

export async function getQualityReports(): Promise<{ reports: Array<Record<string, unknown>> }> {
  return request<{ reports: Array<Record<string, unknown>> }>("/quality/reports");
}

export async function getBenchmarks(): Promise<{ reports: Array<Record<string, unknown>> }> {
  return request<{ reports: Array<Record<string, unknown>> }>("/benchmarks");
}
