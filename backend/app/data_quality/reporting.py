import html
import json
from pathlib import Path
from typing import Any


def write_json_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_html_report(report: dict[str, Any], output_path: Path) -> None:
    """Write a portable report without requiring a template runtime."""

    summary_rows = "".join(
        f"<tr><td>{html.escape(str(key))}</td><td>{html.escape(str(value))}</td></tr>"
        for key, value in report["summary"].items()
    )
    issue_rows = "".join(
        "<tr>"
        f"<td>{html.escape(issue['code'])}</td>"
        f"<td>{html.escape(issue['path'])}</td>"
        f"<td><code>{html.escape(json.dumps(issue['details'], ensure_ascii=False))}</code></td>"
        f"<td>{_thumbnail_html(issue.get('thumbnail'))}</td>"
        "</tr>"
        for issue in report["issues"]
    )
    size_statistics = html.escape(
        json.dumps(report["image_size_statistics"], ensure_ascii=False, indent=2)
    )
    class_distribution = html.escape(
        json.dumps(report["class_distribution"], ensure_ascii=False, indent=2)
    )
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>Data Quality Report</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:2rem;color:#172033}}
table{{border-collapse:collapse;width:100%;margin:1rem 0}}
th,td{{border:1px solid #d7dce5;padding:.5rem;text-align:left;vertical-align:top}}
th{{background:#eef2f7}} img{{max-width:240px;max-height:180px}} code{{white-space:pre-wrap}}
</style></head><body>
<h1>数据质量报告</h1><p>数据集：{html.escape(report['dataset_path'])}</p>
<p>生成时间：{html.escape(report['created_at'])}</p>
<h2>汇总</h2><table><tr><th>指标</th><th>数值</th></tr>{summary_rows}</table>
<h2>尺寸统计</h2><pre>{size_statistics}</pre>
<h2>类别分布</h2><pre>{class_distribution}</pre>
<h2>问题样本</h2><table><tr><th>问题</th><th>路径</th><th>详情</th><th>缩略图</th></tr>{issue_rows}</table>
</body></html>"""
    output_path.write_text(document, encoding="utf-8")


def _thumbnail_html(thumbnail: str | None) -> str:
    if not thumbnail:
        return ""
    return f'<img src="{html.escape(thumbnail, quote=True)}" alt="issue thumbnail">'
