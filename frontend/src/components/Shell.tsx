"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const nav = [
  ["/", "系统概览"],
  ["/single", "单图检测"],
  ["/batch", "批量检测"],
  ["/records", "检测记录"],
  ["/reviews", "人工复核"],
  ["/quality", "数据质量"],
  ["/feedback", "反馈样本"],
  ["/datasets", "数据集版本"],
  ["/models", "模型版本"],
  ["/benchmarks", "性能评测"],
  ["/settings", "系统设置"]
];

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="min-h-screen bg-slate-100">
      <aside className="fixed left-0 top-0 hidden h-full w-64 border-r border-slate-800 bg-slate-950 lg:block">
        <div className="border-b border-slate-800 px-5 py-5">
          <h1 className="text-lg font-semibold text-white">Factory Vision</h1>
          <p className="mt-1 text-xs leading-5 text-slate-400">工业视觉质量检测闭环平台</p>
        </div>
        <nav className="space-y-1 p-3">
          {nav.map(([href, label]) => {
            const active = pathname === href || (href !== "/" && pathname.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className={`block rounded-md px-3 py-2.5 text-sm transition ${
                  active ? "bg-sky-600 text-white" : "text-slate-300 hover:bg-slate-900 hover:text-white"
                }`}
              >
                {label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
        <div className="font-semibold text-slate-950">Factory Vision</div>
        <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
          {nav.map(([href, label]) => (
            <Link
              key={href}
              href={href}
              className={`shrink-0 rounded-md px-3 py-2 text-sm ${
                pathname === href ? "bg-sky-600 text-white" : "bg-slate-100 text-slate-700"
              }`}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>
      <main className="lg:pl-64">
        <div className="mx-auto w-full max-w-[1680px] p-4 lg:p-6 xl:p-8">{children}</div>
      </main>
    </div>
  );
}
