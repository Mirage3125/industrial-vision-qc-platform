import type { ReactNode } from "react";
import { EmptyState } from "@/components/ProductUI";

export function DataTable<T>({
  rows,
  columns,
  emptyText = "暂无数据",
  getRowKey
}: {
  rows: T[];
  columns: Array<{ key: string; header: string; render: (row: T, index: number) => ReactNode; className?: string }>;
  emptyText?: string;
  getRowKey?: (row: T, index: number) => string;
}) {
  if (!rows.length) {
    return <EmptyState title={emptyText} description="当前接口没有返回可展示的记录。" />;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((column) => (
                <th key={column.key} className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase text-slate-500">
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row, index) => (
              <tr key={getRowKey?.(row, index) ?? index} className="hover:bg-slate-50/70">
                {columns.map((column) => (
                  <td key={column.key} className={`px-4 py-3 align-middle text-slate-700 ${column.className ?? ""}`}>
                    {column.render(row, index)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
