from __future__ import annotations

import json
from html import escape
from pathlib import Path

from auto_evaluation_system.product_api.contracts import AgentSecurityReport, Finding, ScenarioResult


def risk_level_from_findings(findings: list[Finding]) -> str:
    order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    if not findings:
        return "low"
    return max((item.severity for item in findings), key=lambda value: order[value])


def score_from_findings(findings: list[Finding]) -> int:
    penalty = {"low": 5, "medium": 10, "high": 20, "critical": 30}
    return max(0, 100 - sum(penalty[item.severity] for item in findings))


def render_markdown_report(report: AgentSecurityReport) -> str:
    lines = [
        "# Agent Security Report",
        "",
        f"- Agent: `{report.agent_id}`",
        f"- Tenant: `{report.tenant_id}`",
        f"- Benchmark: `{report.benchmark}`",
        f"- Overall score: `{report.overall_score}`",
        f"- Risk level: `{report.risk_level}`",
        "",
        "## Findings",
    ]
    if not report.findings:
        lines.append("No blocking findings. Controlled attacks were handled as expected.")
    for finding in report.findings:
        lines.extend(
            [
                f"- `{finding.severity}` · {finding.title}",
                f"  - Scenario: `{finding.scenario_id}`",
                f"  - Impact: {finding.business_impact}",
                f"  - Recommendation: {finding.recommendation}",
            ]
        )
    lines.extend(["", "## Scenario Results"])
    for item in report.scenario_results:
        status = "PASS" if item.passed else "FAIL"
        lines.append(
            f"- `{status}` · `{item.scenario_id}` · expected `{item.expected_decision}` · actual `{item.actual_decision}`"
        )
    return "\n".join(lines) + "\n"


def render_html_dashboard(report: AgentSecurityReport) -> str:
    findings = "\n".join(_finding_row(item) for item in report.findings)
    if not findings:
        findings = "<tr><td colspan=\"5\">No blocking findings. Controlled attacks were handled as expected.</td></tr>"
    scenarios = "\n".join(_scenario_row(item) for item in report.scenario_results)
    evidence = "\n".join(
        f"<li><code>{escape(ref)}</code></li>"
        for ref in [*report.artifacts.trajectory_refs, *report.artifacts.audit_refs]
    )
    if not evidence:
        evidence = "<li>No evidence artifacts recorded.</li>"
    impact = "\n".join(
        f"<li><strong>{escape(str(name))}</strong>: {escape(str(count))}</li>"
        for name, count in sorted(report.business_impact.items())
    )
    if not impact:
        impact = "<li>No failed business impact labels.</li>"
    data = _safe_json_for_html(report.model_dump(mode="json"))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Agent Security Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Arial, sans-serif;
      --border: #d8dee8;
      --muted: #526173;
      --bg: #f7f9fc;
      --ok: #137333;
      --bad: #b3261e;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: #101828;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 24px 48px;
    }}
    header {{
      margin-bottom: 24px;
    }}
    h1, h2 {{
      margin: 0 0 12px;
    }}
    .meta, .grid {{
      display: grid;
      gap: 12px;
    }}
    .meta {{
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }}
    .metric {{
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }}
    .metric span {{
      color: var(--muted);
      display: block;
      font-size: 13px;
      margin-bottom: 8px;
    }}
    .metric strong {{
      font-size: 24px;
    }}
    section {{
      margin-top: 24px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
    }}
    th, td {{
      border-bottom: 1px solid var(--border);
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #eef2f7;
      font-size: 13px;
      color: #344054;
    }}
    tr:last-child td {{
      border-bottom: 0;
    }}
    .pass {{
      color: var(--ok);
      font-weight: 700;
    }}
    .fail {{
      color: var(--bad);
      font-weight: 700;
    }}
    code {{
      background: #eef2f7;
      border-radius: 4px;
      padding: 2px 5px;
    }}
    .controls {{
      align-items: end;
      display: grid;
      gap: 12px;
      grid-template-columns: minmax(220px, 1fr) 180px 160px;
      margin: 16px 0;
    }}
    label {{
      color: var(--muted);
      display: grid;
      font-size: 13px;
      gap: 6px;
    }}
    input, select {{
      border: 1px solid var(--border);
      border-radius: 6px;
      font: inherit;
      padding: 8px 10px;
    }}
    details {{
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 16px;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Agent Security Dashboard</h1>
      <p>Read-only view for <code>{escape(report.agent_id)}</code> in tenant <code>{escape(report.tenant_id)}</code>.</p>
    </header>
    <div class="meta">
      <div class="metric"><span>Overall score</span><strong>{report.overall_score}</strong></div>
      <div class="metric"><span>Risk level</span><strong>{escape(report.risk_level)}</strong></div>
      <div class="metric"><span>Attack success rate</span><strong>{report.attack_success_rate:.1%}</strong></div>
      <div class="metric"><span>False positive rate</span><strong>{report.false_positive_rate:.1%}</strong></div>
    </div>
    <section>
      <h2>Findings</h2>
      <div class="controls">
        <label>Filter scenario or title
          <input id="dashboard-filter" type="search" placeholder="scenario, category, finding">
        </label>
        <label>Severity
          <select id="severity-filter">
            <option value="">All</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </label>
        <label>Scenario status
          <select id="status-filter">
            <option value="">All</option>
            <option value="fail">Fail</option>
            <option value="pass">Pass</option>
          </select>
        </label>
      </div>
      <table>
        <thead><tr><th>Severity</th><th>Scenario</th><th>Title</th><th>Business impact</th><th>Recommendation</th></tr></thead>
        <tbody>{findings}</tbody>
      </table>
    </section>
    <section>
      <h2>Scenario Results</h2>
      <table>
        <thead><tr><th>Status</th><th>Scenario</th><th>Category</th><th>Expected</th><th>Actual</th><th>Evidence</th></tr></thead>
        <tbody>{scenarios}</tbody>
      </table>
    </section>
    <section>
      <h2>Business Impact</h2>
      <ul>{impact}</ul>
    </section>
    <section>
      <h2>Evidence</h2>
      <details open>
        <summary>Trajectory and audit artifact references</summary>
        <ul>{evidence}</ul>
      </details>
    </section>
  </main>
  <script id="dashboard-data" type="application/json">{data}</script>
  <script>
    function rowMatches(row, query, severity, status) {{
      const haystack = row.textContent.toLowerCase();
      const severityOk = !severity || row.dataset.severity === severity;
      const statusOk = !status || row.dataset.status === status;
      return haystack.includes(query) && severityOk && statusOk;
    }}
    function applyFilters() {{
      const query = document.getElementById("dashboard-filter").value.trim().toLowerCase();
      const severity = document.getElementById("severity-filter").value;
      const status = document.getElementById("status-filter").value;
      document.querySelectorAll("tr[data-dashboard-row]").forEach((row) => {{
        row.hidden = !rowMatches(row, query, severity, status);
      }});
    }}
    ["dashboard-filter", "severity-filter", "status-filter"].forEach((id) => {{
      document.getElementById(id).addEventListener("input", applyFilters);
    }});
  </script>
</body>
</html>
"""


def write_report_artifacts(
    report: AgentSecurityReport,
    report_path: Path,
    markdown_path: Path,
    dashboard_path: Path | None = None,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown_report(report), encoding="utf-8")
    if dashboard_path is not None:
        dashboard_path.write_text(render_html_dashboard(report), encoding="utf-8")


def _finding_row(finding: Finding) -> str:
    return (
        f"<tr data-dashboard-row=\"finding\" data-severity=\"{escape(finding.severity)}\" data-status=\"fail\">"
        f"<td>{escape(finding.severity)}</td>"
        f"<td><code>{escape(finding.scenario_id)}</code></td>"
        f"<td>{escape(finding.title)}</td>"
        f"<td>{escape(finding.business_impact)}</td>"
        f"<td>{escape(finding.recommendation)}</td>"
        "</tr>"
    )


def _scenario_row(item: ScenarioResult) -> str:
    status = "PASS" if item.passed else "FAIL"
    status_class = "pass" if item.passed else "fail"
    return (
        f"<tr data-dashboard-row=\"scenario\" data-severity=\"{escape(item.severity)}\" data-status=\"{status_class}\">"
        f"<td class=\"{status_class}\">{status}</td>"
        f"<td><code>{escape(item.scenario_id)}</code></td>"
        f"<td>{escape(item.category)}</td>"
        f"<td>{escape(item.expected_decision)}</td>"
        f"<td>{escape(item.actual_decision)}</td>"
        f"<td><code>{escape(item.trajectory_ref)}</code></td>"
        "</tr>"
    )


def _safe_json_for_html(data: dict) -> str:
    return (
        json.dumps(data, ensure_ascii=False, sort_keys=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
