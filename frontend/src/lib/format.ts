import type { ModelVersion } from "@/lib/types";

export const EMPTY_TEXT = "—";

export type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

const statusMap: Record<string, { label: string; tone: BadgeTone }> = {
  NORMAL: { label: "正常", tone: "success" },
  normal: { label: "正常", tone: "success" },
  OK: { label: "正常", tone: "success" },
  DEFECT: { label: "缺陷", tone: "danger" },
  defect: { label: "缺陷", tone: "danger" },
  PENDING: { label: "待处理", tone: "warning" },
  pending: { label: "待处理", tone: "warning" },
  REVIEW: { label: "待复核", tone: "warning" },
  requires_review: { label: "待复核", tone: "warning" },
  reviewed: { label: "已复核", tone: "success" },
  COMPLETED: { label: "已完成", tone: "success" },
  completed: { label: "已完成", tone: "success" },
  approved: { label: "确认缺陷", tone: "success" },
  corrected: { label: "已修正", tone: "info" },
  rejected: { label: "判定正常", tone: "neutral" },
  exported: { label: "已导出", tone: "success" },
  not_exported: { label: "未导出", tone: "warning" },
  active: { label: "当前使用", tone: "success" },
  inactive: { label: "未启用", tone: "neutral" }
};

const taskTypeMap: Record<string, string> = {
  hybrid: "闭环综合检测",
  detection: "目标缺陷检测",
  classification: "缺陷分类",
  anomaly: "异常检测",
  classical: "传统视觉检测"
};

const defectMap: Record<string, string> = {
  normal: "正常",
  unknown: "未知",
  unknown_anomaly: "未知异常",
  scratches: "划伤",
  scratch: "划伤",
  crack: "裂纹",
  cracks: "裂纹",
  pit: "凹坑",
  pits: "凹坑",
  stain: "污渍",
  stains: "污渍",
  inclusion: "夹杂",
  defect: "缺陷"
};

export function valueText(value: unknown): string {
  if (value === null || value === undefined || value === "") return EMPTY_TEXT;
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : EMPTY_TEXT;
  if (typeof value === "boolean") return value ? "是" : "否";
  return String(value);
}

export function formatBoolean(value: unknown): string {
  return value === null || value === undefined ? EMPTY_TEXT : value ? "是" : "否";
}

export function formatDateTime(value: unknown): string {
  if (!value) return EMPTY_TEXT;
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return EMPTY_TEXT;
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  }).format(date);
}

export function formatConfidence(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return EMPTY_TEXT;
  const normalized = value <= 1 ? value * 100 : value;
  return `${normalized.toFixed(2)}%`;
}

export function formatNumber(value: unknown, digits = 2, suffix = ""): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return EMPTY_TEXT;
  return `${value.toFixed(digits)}${suffix}`;
}

export function formatMs(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return EMPTY_TEXT;
  return `${value.toFixed(value >= 100 ? 0 : 1)} ms`;
}

export function formatStatus(value: unknown): { label: string; tone: BadgeTone } {
  const key = valueText(value);
  if (key === EMPTY_TEXT) return { label: EMPTY_TEXT, tone: "neutral" };
  return statusMap[key] ?? { label: key.replaceAll("_", " "), tone: "neutral" };
}

export function formatTaskType(value: unknown): string {
  const key = valueText(value);
  return taskTypeMap[key] ?? key;
}

export function formatDefect(value: unknown): string {
  const key = valueText(value);
  if (key === EMPTY_TEXT) return EMPTY_TEXT;
  return defectMap[key] ?? key.replaceAll("_", " ");
}

export function formatArray(value: unknown, separator = "、", fallback = EMPTY_TEXT): string {
  if (!Array.isArray(value) || value.length === 0) return fallback;
  const normalized = value
    .filter((item) => item !== null && item !== undefined && item !== "")
    .map(String);
  return normalized.length ? normalized.join(separator) : fallback;
}

export function formatList(values: unknown): string {
  if (!Array.isArray(values) || values.length === 0) return EMPTY_TEXT;
  const normalized = values
    .filter((item) => item !== null && item !== undefined && item !== "")
    .map((item) => formatDefect(item));
  return normalized.length ? normalized.join("、") : EMPTY_TEXT;
}

export type BoxLike = {
  x1?: number;
  y1?: number;
  x2?: number;
  y2?: number;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  w?: number;
  h?: number;
};

export function toNumber(value: unknown): number | null {
  const numberValue = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function normalizeBoxRecord(value: Record<string, unknown>): BoxLike | null {
  const x1 = toNumber(value.x1 ?? value.left ?? value.xmin);
  const y1 = toNumber(value.y1 ?? value.top ?? value.ymin);
  const x2 = toNumber(value.x2 ?? value.right ?? value.xmax);
  const y2 = toNumber(value.y2 ?? value.bottom ?? value.ymax);
  if (x1 !== null && y1 !== null && x2 !== null && y2 !== null) return { x1, y1, x2, y2 };

  const x = toNumber(value.x);
  const y = toNumber(value.y);
  const width = toNumber(value.width ?? value.w);
  const height = toNumber(value.height ?? value.h);
  if (x !== null && y !== null && width !== null && height !== null) return { x, y, width, height };

  return null;
}

function normalizeBoxArray(value: unknown, mode: "xyxy" | "xywh" = "xyxy"): BoxLike | null {
  if (!Array.isArray(value) || value.length < 4) return null;
  const [a, b, c, d] = value.map(toNumber);
  if (a === null || b === null || c === null || d === null) return null;
  return mode === "xywh" ? { x: a, y: b, width: c, height: d } : { x1: a, y1: b, x2: c, y2: d };
}

function formatCoordinate(value: unknown): string {
  const numberValue = toNumber(value);
  if (numberValue === null) return EMPTY_TEXT;
  return Number.isInteger(numberValue) ? String(numberValue) : numberValue.toFixed(1);
}

export function normalizeBox(region: Record<string, unknown>): BoxLike | null {
  const boundingBox = asRecord(region.bounding_box);
  if (boundingBox) {
    const box = normalizeBoxRecord(boundingBox);
    if (box) return box;
  }

  const direct = normalizeBoxRecord(region);
  if (direct) return direct;

  for (const key of ["bbox", "box", "bndbox", "coordinates"]) {
    const nested = asRecord(region[key]);
    if (nested) {
      const box = normalizeBoxRecord(nested);
      if (box) return box;
    }
  }

  return (
    normalizeBoxArray(region.xyxy) ??
    normalizeBoxArray(region.bounding_box) ??
    normalizeBoxArray(region.bbox) ??
    normalizeBoxArray(region.box) ??
    normalizeBoxArray(region.xywh, "xywh") ??
    normalizeBoxArray(region.coordinates)
  );
}

export function boxText(region: Record<string, unknown>): string {
  const box = normalizeBox(region);
  if (!box) return EMPTY_TEXT;
  if (box.x1 !== undefined) {
    return `(${formatCoordinate(box.x1)}, ${formatCoordinate(box.y1)}) → (${formatCoordinate(box.x2)}, ${formatCoordinate(box.y2)})`;
  }
  return `x ${formatCoordinate(box.x)}, y ${formatCoordinate(box.y)}, w ${formatCoordinate(box.width)}, h ${formatCoordinate(box.height)}`;
}

export function regionArea(region: Record<string, unknown>): string {
  const directArea = toNumber(region.area);
  if (directArea !== null) return formatNumber(directArea, Number.isInteger(directArea) ? 0 : 2);

  const box = normalizeBox(region);
  if (!box) return EMPTY_TEXT;
  const width = box.width ?? ((box.x2 ?? 0) - (box.x1 ?? 0));
  const height = box.height ?? ((box.y2 ?? 0) - (box.y1 ?? 0));
  if (width <= 0 || height <= 0) return EMPTY_TEXT;
  const area = width * height;
  return formatNumber(area, Number.isInteger(area) ? 0 : 2);
}

export function regionRatio(region: Record<string, unknown>): string {
  const directRatio = toNumber(region.aspect_ratio);
  if (directRatio !== null) return formatNumber(directRatio, 2);

  const box = normalizeBox(region);
  if (!box) return EMPTY_TEXT;
  const width = box.width ?? ((box.x2 ?? 0) - (box.x1 ?? 0));
  const height = box.height ?? ((box.y2 ?? 0) - (box.y1 ?? 0));
  if (width <= 0 || height <= 0) return EMPTY_TEXT;
  return formatNumber(width / height, 2);
}

export function modelDisplay(model?: ModelVersion | null): string {
  if (!model) return EMPTY_TEXT;
  return `${model.model_name} / ${model.version}`;
}

export function compactJson(value: unknown): string {
  if (value === null || value === undefined) return EMPTY_TEXT;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
