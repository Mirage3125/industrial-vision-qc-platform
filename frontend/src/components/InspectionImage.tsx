"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { formatConfidence, formatDefect, normalizeBox } from "@/lib/format";
import type { BoxLike } from "@/lib/format";
import type { YoloRegion } from "@/lib/types";

type RenderedBox = {
  left: number;
  top: number;
  width: number;
  height: number;
};

function regionLabel(region: YoloRegion): string {
  return formatDefect(region.class_name ?? region.label ?? region.class);
}

function toRenderedBox(box: BoxLike, originalWidth: number, originalHeight: number, containerWidth: number, containerHeight: number): RenderedBox | null {
  if (!originalWidth || !originalHeight || !containerWidth || !containerHeight) return null;

  let x1 = box.x1 ?? box.x;
  let y1 = box.y1 ?? box.y;
  let x2 = box.x2;
  let y2 = box.y2;
  if (x1 === undefined || y1 === undefined) return null;
  if (x2 === undefined) x2 = x1 + (box.width ?? 0);
  if (y2 === undefined) y2 = y1 + (box.height ?? 0);

  const looksNormalized = Math.max(x1, y1, x2, y2) <= 1;
  if (looksNormalized) {
    x1 *= originalWidth;
    x2 *= originalWidth;
    y1 *= originalHeight;
    y2 *= originalHeight;
  }

  const imageScale = Math.min(containerWidth / originalWidth, containerHeight / originalHeight);
  const renderedWidth = originalWidth * imageScale;
  const renderedHeight = originalHeight * imageScale;
  const offsetX = (containerWidth - renderedWidth) / 2;
  const offsetY = (containerHeight - renderedHeight) / 2;

  const width = Math.max((x2 - x1) * imageScale, 0);
  const height = Math.max((y2 - y1) * imageScale, 0);
  if (!width || !height) return null;

  return {
    left: offsetX + x1 * imageScale,
    top: offsetY + y1 * imageScale,
    width,
    height
  };
}

export function InspectionImage({
  src,
  regions,
  alt = "检测图片"
}: {
  src: string | null;
  regions?: YoloRegion[] | null;
  alt?: string;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [showBoxes, setShowBoxes] = useState(true);
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const safeRegions = useMemo(() => (Array.isArray(regions) ? regions : []), [regions]);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;
    const update = () => {
      const rect = node.getBoundingClientRect();
      setContainerSize({ width: rect.width, height: rect.height });
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(node);
    window.addEventListener("resize", update);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", update);
    };
  }, [src]);

  const boxes = useMemo(
    () =>
      safeRegions
        .map((region, index) => {
          const box = normalizeBox(region as Record<string, unknown>);
          if (!box) return null;
          const rendered = toRenderedBox(box, naturalSize.width, naturalSize.height, containerSize.width, containerSize.height);
          if (!rendered) return null;
          return { region, rendered, key: region.region_id ?? index };
        })
        .filter((item): item is { region: YoloRegion; rendered: RenderedBox; key: number } => item !== null),
    [safeRegions, naturalSize, containerSize]
  );

  if (!src) {
    return (
      <div className="flex min-h-80 items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-500">
        暂无图片
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <label className="inline-flex items-center gap-2 text-sm text-slate-700">
        <input className="h-4 w-4 rounded border-slate-300" type="checkbox" checked={showBoxes} onChange={(event) => setShowBoxes(event.target.checked)} />
        显示检测框
      </label>
      <div ref={containerRef} className="relative h-[min(70vh,560px)] min-h-80 overflow-hidden rounded-lg border border-slate-200 bg-slate-100">
        <img
          src={src}
          alt={alt}
          className="absolute inset-0 h-full w-full object-contain"
          onLoad={(event) => {
            const image = event.currentTarget;
            setNaturalSize({ width: image.naturalWidth, height: image.naturalHeight });
          }}
        />
        {showBoxes && (
          <div className="pointer-events-none absolute inset-0">
            {boxes.map(({ region, rendered, key }) => (
              <div
                key={key}
                className="absolute border-2 border-red-500 shadow-[0_0_0_1px_rgba(255,255,255,0.95)]"
                style={{
                  left: rendered.left,
                  top: rendered.top,
                  width: rendered.width,
                  height: rendered.height
                }}
              >
                <span className="absolute left-0 top-0 -translate-y-full whitespace-nowrap rounded-t bg-red-600 px-2 py-1 text-xs font-medium text-white">
                  {regionLabel(region)} {formatConfidence(region.confidence ?? region.score)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
