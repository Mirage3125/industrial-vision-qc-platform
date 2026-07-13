export type ApiEnvelope<T> = {
  success: boolean;
  data: T;
  error: { code: string; message: string; details?: unknown } | null;
  request_id: string;
};

export type ModelVersion = {
  id: string;
  model_name: string;
  model_type: string;
  version: string;
  framework: string;
  model_path: string;
  active: boolean;
  metrics?: Record<string, unknown>;
};

export type BoundingBox = {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};

export type YoloRegion = {
  [key: string]: unknown;
  region_id?: number;
  class_name?: string;
  label?: string;
  class?: string;
  confidence?: number;
  score?: number;
  bounding_box?: BoundingBox;
  area?: number;
  aspect_ratio?: number;
  circularity?: number;
  anomaly_score?: number | null;
};

export type InspectionRecord = {
  id: string;
  image_path: string;
  final_status: string | null;
  predicted_class: string | null;
  confidence: number | null;
  anomaly_score: number | null;
  review_reasons?: string[] | null;
  station_id?: string | null;
  batch_id?: string | null;
  processing_time_ms?: number | null;
  created_at: string;
};

export type InspectionResult = {
  idempotent: boolean;
  inspection_id: string;
  review_id: string | null;
  image_path?: string;
  requires_review: boolean;
  review_reasons?: string[] | null;
  decision_rule_version: string;
  final_status: string;
  predicted_class: string | null;
  confidence: number | null;
  anomaly_score: number | null;
  quality_result?: Record<string, unknown>;
  yolo_result?: { regions?: YoloRegion[] | null };
  yolo_regions?: YoloRegion[] | null;
  anomaly_result?: Record<string, unknown>;
  step_timings?: Record<string, number> | null;
  model_versions?: Record<string, string | null> | null;
};

export type ReviewSummary = {
  id: string;
  inspection_id: string;
  review_status: string;
  review_reasons?: string[] | null;
  created_at: string;
};

export type ReviewDetail = {
  id: string;
  inspection_id: string;
  image_path: string;
  yolo_boxes?: YoloRegion[] | null;
  anomaly_heatmap?: string | null;
  quality_result?: Record<string, unknown> | null;
  original_prediction?: Record<string, unknown> | null;
  system_decision?: Record<string, unknown> | null;
  final_status: string;
  review_reasons?: string[] | null;
  model_versions?: Record<string, string | null> | null;
  step_timings?: Record<string, number> | null;
  review_status: string;
  corrected_prediction?: Record<string, unknown> | null;
  reviewer?: string | null;
  review_comment?: string | null;
  history?: Array<Record<string, unknown>> | null;
};

export type FeedbackSample = {
  id: string;
  inspection_id: string;
  image_path: string;
  original_label: string | null;
  corrected_label: string;
  feedback_type: string;
  export_status: string;
  dataset_version_id: string | null;
  created_at: string;
};

export type Overview = {
  demo_data: boolean;
  today_detection_count: number;
  defect_count: number;
  defect_rate: number;
  auto_pass_count: number;
  pending_review_count: number;
  reviewed_count: number;
  average_latency_ms: number;
  active_models?: ModelVersion[] | null;
  onnx_provider: string;
  class_distribution: Record<string, number>;
  recent_records?: InspectionRecord[] | null;
};
