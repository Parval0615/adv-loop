from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def generate_console(input_dir: Path, out_dir: Path) -> Path:
    input_dir = Path(input_dir)
    out_dir = Path(out_dir)
    assets_dir = out_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    runs = _discover_runs(input_dir)
    eval_report = _load_json(input_dir / "arena_eval_report.json")

    (assets_dir / "style.css").write_text(_css(), encoding="utf-8")
    _write_svgs(assets_dir, runs[0] if runs else {})
    index_path = out_dir / "index.html"
    index_path.write_text(_html(input_dir, runs, eval_report), encoding="utf-8")
    return index_path


def _discover_runs(input_dir: Path) -> list[dict[str, Any]]:
    candidates = []
    if (input_dir / "trace_report.json").exists():
        candidates.append(input_dir)
    candidates.extend(path for path in input_dir.rglob("*") if path.is_dir() and (path / "trace_report.json").exists())

    runs = []
    seen = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        trace_report = _load_json(path / "trace_report.json")
        summary = _load_json(path / "summary.json")
        decisions = _load_jsonl(path / "sentinel_decisions.jsonl")
        runs.append(
            {
                "path": path,
                "trace_report": trace_report,
                "summary": summary,
                "decisions": decisions,
                "mermaid": (path / "trace_graph.md").read_text(encoding="utf-8") if (path / "trace_graph.md").exists() else "",
            }
        )
    return runs


def _html(input_dir: Path, runs: list[dict[str, Any]], eval_report: dict[str, Any] | None) -> str:
    first = runs[0] if runs else {}
    report = first.get("trace_report", {})
    dag = _dag_view(first)
    timeline = _timeline_view(report)
    verdict = _verdict_panel(report, first.get("decisions", []))
    decisions = _decision_stream(runs)
    metrics = _metrics(eval_report)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MCP-Sentinel Console</title>
  <link rel="stylesheet" href="assets/style.css">
</head>
<body>
  <header>
    <div>
      <p class="eyebrow">MCP-Sentinel</p>
      <h1>Security Review Console</h1>
      <p class="subtitle">Local deterministic arena review. This is not a production MCP gateway.</p>
    </div>
    <div class="source">Input: {html.escape(str(input_dir))}</div>
  </header>
  <main>
    <section>
      <h2>DAG View</h2>
      {dag}
    </section>
    <section>
      <h2>Timeline View</h2>
      {timeline}
    </section>
    <section>
      <h2>Verdict Panel</h2>
      {verdict}
    </section>
    <section>
      <h2>Decision Stream</h2>
      {decisions}
    </section>
    <section>
      <h2>Policy Alerts And Trace Links</h2>
      {metrics}
      {_artifact_links(runs)}
    </section>
  </main>
</body>
</html>
"""


def _dag_view(run: dict[str, Any]) -> str:
    report = run.get("trace_report", {})
    graph = report.get("graph", {})
    nodes = graph.get("nodes", [])
    if not nodes:
        return "<p>No trace graph available.</p>"
    return '<img class="viz" src="assets/dag.svg" alt="Trace DAG view">'


def _dag_list(run: dict[str, Any]) -> str:
    report = run.get("trace_report", {})
    graph = report.get("graph", {})
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_items = "".join(
        f"<li><strong>{html.escape(node.get('label', 'node'))}</strong><span>{html.escape(node.get('node_type', ''))} / {html.escape(node.get('actor', ''))}</span></li>"
        for node in nodes[:24]
    )
    edge_items = "".join(
        f"<li>{html.escape(edge.get('source', ''))} -> {html.escape(edge.get('target', ''))} <span>{html.escape(edge.get('relation', ''))}</span></li>"
        for edge in edges[:32]
    )
    return f"<div class=\"split\"><ol class=\"nodes\">{node_items}</ol><ol class=\"edges\">{edge_items}</ol></div>"


def _timeline_view(report: dict[str, Any]) -> str:
    calls = report.get("call_details", [])
    if not calls:
        return "<p>No timeline calls available.</p>"
    fallback = "<ol class=\"timeline\">" + "".join(
        f"<li><strong>{html.escape(call.get('name', 'tool'))}</strong><span>{html.escape(call.get('actor', ''))}</span></li>"
        for call in calls
    ) + "</ol>"
    return '<img class="viz" src="assets/timeline.svg" alt="Trace timeline view">' + fallback


def _verdict_panel(report: dict[str, Any], decisions: list[dict[str, Any]]) -> str:
    impact = report.get("impact_scope", {})
    alerts = [
        decision for decision in decisions
        if decision.get("decision", {}).get("decision") in ("ask", "block")
    ]
    alert_items = "".join(
        f"<li><strong>{html.escape(item.get('request', {}).get('name', 'tool'))}</strong><span>{html.escape(item.get('decision', {}).get('decision', ''))}: {html.escape(item.get('decision', {}).get('reason', ''))}</span></li>"
        for item in alerts
    ) or "<li><strong>allow</strong><span>No blocking policy alerts.</span></li>"
    return f"""
    <div class="verdict">
      <p>{html.escape(impact.get('summary', 'No impact summary available.'))}</p>
      <ul>{alert_items}</ul>
    </div>
    """


def _decision_stream(runs: list[dict[str, Any]]) -> str:
    rows = []
    for run in runs:
        for decision in run.get("decisions", []):
            selected = decision.get("decision", {})
            rows.append(
                "<tr>"
                f"<td>{html.escape(run.get('summary', {}).get('scenario_id', run['path'].name))}</td>"
                f"<td>{html.escape(decision.get('request', {}).get('name', ''))}</td>"
                f"<td>{html.escape(selected.get('decision', ''))}</td>"
                f"<td>{html.escape(selected.get('stage', ''))}</td>"
                f"<td>{html.escape(selected.get('reason', ''))}</td>"
                "</tr>"
            )
    if not rows:
        return "<p>No sentinel decisions available.</p>"
    return "<table><thead><tr><th>Run</th><th>Tool</th><th>Decision</th><th>Stage</th><th>Reason</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _metrics(eval_report: dict[str, Any] | None) -> str:
    if not eval_report:
        return ""
    metrics = eval_report.get("metrics", {})
    items = "".join(
        f"<li><strong>{html.escape(str(key))}</strong><span>{html.escape(str(value))}</span></li>"
        for key, value in metrics.items()
        if not isinstance(value, dict)
    )
    return f"<ul class=\"metrics\">{items}</ul>"


def _artifact_links(runs: list[dict[str, Any]]) -> str:
    items = []
    for run in runs:
        path = Path(run["path"])
        label = run.get("summary", {}).get("scenario_id", path.name)
        items.append(
            f"<li><strong>{html.escape(label)}</strong><span>{html.escape(str(path / 'trace_report.json'))}</span></li>"
        )
    return "<ul class=\"artifacts\">" + "".join(items) + "</ul>"


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_svgs(assets_dir: Path, run: dict[str, Any]) -> None:
    report = run.get("trace_report", {})
    (assets_dir / "dag.svg").write_text(_dag_svg(report), encoding="utf-8")
    (assets_dir / "timeline.svg").write_text(_timeline_svg(report), encoding="utf-8")


def _dag_svg(report: dict[str, Any]) -> str:
    graph = report.get("graph", {})
    nodes = graph.get("nodes", [])[:18]
    edges = graph.get("edges", [])
    if not nodes:
        return _empty_svg("No trace graph available")
    width = 980
    row_h = 86
    height = max(220, 60 + row_h * len(nodes))
    positions = {}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#64748b"/></marker></defs>',
    ]
    for index, node in enumerate(nodes):
        x = 40 + (index % 3) * 310
        y = 36 + (index // 3) * row_h
        positions[node.get("node_id")] = (x + 130, y + 28)
        fill = _node_fill(str(node.get("node_type", "")))
        parts.append(f'<rect x="{x}" y="{y}" width="260" height="56" rx="7" fill="{fill}" stroke="#94a3b8"/>')
        parts.append(f'<text x="{x + 12}" y="{y + 23}" font-size="13" font-family="Segoe UI, Arial" fill="#0f172a">{_xml(node.get("label", "node"), 34)}</text>')
        parts.append(f'<text x="{x + 12}" y="{y + 43}" font-size="11" font-family="Segoe UI, Arial" fill="#475569">{_xml(node.get("node_type", ""), 30)}</text>')
    for edge in edges[:40]:
        source = positions.get(edge.get("source"))
        target = positions.get(edge.get("target"))
        if not source or not target:
            continue
        parts.append(
            f'<line x1="{source[0]}" y1="{source[1]}" x2="{target[0]}" y2="{target[1]}" stroke="#64748b" stroke-width="1.4" marker-end="url(#arrow)"/>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def _timeline_svg(report: dict[str, Any]) -> str:
    calls = report.get("call_details", [])
    if not calls:
        return _empty_svg("No timeline available")
    width = 980
    row_h = 62
    height = 60 + row_h * len(calls)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<line x1="56" y1="34" x2="56" y2="' + str(height - 28) + '" stroke="#94a3b8" stroke-width="2"/>',
    ]
    for index, call in enumerate(calls):
        y = 42 + index * row_h
        decision = call.get("sentinel_decision") or {}
        color = {"allow": "#16a34a", "ask": "#d97706", "block": "#dc2626"}.get(decision.get("decision"), "#2563eb")
        parts.append(f'<circle cx="56" cy="{y}" r="9" fill="{color}"/>')
        parts.append(f'<rect x="86" y="{y - 22}" width="820" height="44" rx="7" fill="#ffffff" stroke="#cbd5e1"/>')
        label = f"{call.get('name', 'tool')} / {decision.get('decision', 'event')}"
        parts.append(f'<text x="102" y="{y - 3}" font-size="13" font-family="Segoe UI, Arial" fill="#0f172a">{_xml(label, 80)}</text>')
        parts.append(f'<text x="102" y="{y + 15}" font-size="11" font-family="Segoe UI, Arial" fill="#64748b">{_xml(call.get("actor", ""), 80)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _empty_svg(message: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="980" height="180" viewBox="0 0 980 180">'
        '<rect width="100%" height="100%" fill="#f8fafc"/>'
        f'<text x="40" y="90" font-size="16" font-family="Segoe UI, Arial" fill="#475569">{_xml(message, 80)}</text>'
        "</svg>"
    )


def _node_fill(node_type: str) -> str:
    return {
        "decision": "#eef2ff",
        "tool_call": "#ecfeff",
        "resource_read": "#f0fdf4",
        "sub_dispatch": "#fff7ed",
        "injection_finding": "#fef2f2",
    }.get(node_type, "#ffffff")


def _xml(value: Any, limit: int) -> str:
    text = str(value)
    if len(text) > limit:
        text = text[: limit - 3] + "..."
    return html.escape(text, quote=True)


def _css() -> str:
    return """
:root { color-scheme: light; font-family: Inter, Segoe UI, Arial, sans-serif; }
body { margin: 0; background: #f6f7f9; color: #18202a; }
header { display: flex; justify-content: space-between; align-items: end; gap: 24px; padding: 32px 40px; background: #ffffff; border-bottom: 1px solid #dce1e7; }
h1, h2, p { margin: 0; }
h1 { font-size: 30px; line-height: 1.2; }
h2 { font-size: 18px; margin-bottom: 16px; }
main { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; padding: 24px 40px 40px; }
section { background: #ffffff; border: 1px solid #dce1e7; border-radius: 8px; padding: 18px; min-width: 0; }
section:nth-child(4), section:nth-child(5) { grid-column: 1 / -1; }
.eyebrow { color: #476582; font-size: 13px; text-transform: uppercase; letter-spacing: 0; margin-bottom: 6px; }
.subtitle { color: #5c6672; font-size: 13px; margin-top: 8px; }
.source { color: #5c6672; font-size: 13px; overflow-wrap: anywhere; }
.split { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
ol, ul { margin: 0; padding-left: 20px; }
li { margin: 8px 0; }
li span { display: block; color: #5c6672; font-size: 13px; overflow-wrap: anywhere; }
.timeline li { border-left: 3px solid #2f6fed; padding-left: 10px; }
.verdict p { margin-bottom: 12px; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; }
th, td { border-bottom: 1px solid #e5e9ef; padding: 9px 8px; text-align: left; vertical-align: top; overflow-wrap: anywhere; }
th { color: #476582; font-size: 13px; }
.viz { width: 100%; height: auto; border: 1px solid #e5e9ef; border-radius: 8px; background: #f8fafc; }
.metrics, .artifacts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px 18px; }
@media (max-width: 900px) { header, main { padding-left: 18px; padding-right: 18px; } main, .split, .metrics, .artifacts { grid-template-columns: 1fr; } section:nth-child(4), section:nth-child(5) { grid-column: auto; } }
"""
