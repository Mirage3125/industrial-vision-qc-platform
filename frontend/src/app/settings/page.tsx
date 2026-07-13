import { PageHeader, SectionTitle, StatCard } from "@/components/ProductUI";

export default function SettingsPage() {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

  return (
    <div className="space-y-6">
      <PageHeader title="系统设置" description="查看前端连接后端服务所需的运行配置，便于部署检查和演示前确认环境。" />
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="API Base" value={<span className="break-all text-base">{apiBase}</span>} />
        <StatCard label="前端环境变量" value={<span className="text-base">frontend/.env.local</span>} />
        <StatCard label="后端 CORS" value={<span className="text-base">FVQL_CORS_ORIGINS</span>} />
      </div>
      <section className="card">
        <SectionTitle title="部署检查项" />
        <div className="grid gap-3 text-sm text-slate-700 md:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">后端健康检查接口可访问。</div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">前端 API Base 指向当前后端地址。</div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">模型版本和数据集版本已在后台注册。</div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">演示前准备真实检测样本，避免空数据页面。</div>
        </div>
      </section>
    </div>
  );
}
