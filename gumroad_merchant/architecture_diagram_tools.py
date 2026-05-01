from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gumroad_merchant.settings import PROJECT_ROOT


ARCHITECTURE_DIR = PROJECT_ROOT / "artifacts" / "architecture"


def slugify(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned or "architecture"


def component(x: int, y: int, width: int, height: int, label: str, sublabel: str, fill: str, stroke: str) -> str:
    cx = x + width // 2
    return f"""
      <rect x="{x}" y="{y}" width="{width}" height="{height}" rx="6" fill="#0f172a"/>
      <rect x="{x}" y="{y}" width="{width}" height="{height}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>
      <text x="{cx}" y="{y + 22}" fill="white" font-size="11" font-weight="600" text-anchor="middle">{html.escape(label)}</text>
      <text x="{cx}" y="{y + 40}" fill="#94a3b8" font-size="9" text-anchor="middle">{html.escape(sublabel)}</text>
    """


def arrow(x1: int, y1: int, x2: int, y2: int, label: str = "") -> str:
    midpoint_x = (x1 + x2) // 2
    midpoint_y = (y1 + y2) // 2 - 8
    text = (
        f'<text x="{midpoint_x}" y="{midpoint_y}" fill="#94a3b8" font-size="8" text-anchor="middle">{html.escape(label)}</text>'
        if label
        else ""
    )
    return f"""
      <path d="M {x1} {y1} L {x2} {y2}" stroke="#64748b" stroke-width="1.4" fill="none" marker-end="url(#arrowhead)"/>
      {text}
    """


def render_agent_action_diagram(title: str, generated_at: str) -> str:
    safe_title = html.escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      background: #020617;
      color: #e2e8f0;
      font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    .wrap {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 34px 24px 42px;
    }}
    header {{
      margin-bottom: 18px;
    }}
    .status {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: #34d399;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0;
      margin-bottom: 10px;
    }}
    .dot {{
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: #34d399;
      box-shadow: 0 0 18px #34d399;
      animation: pulse 1.8s ease-in-out infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: .55; transform: scale(.92); }}
      50% {{ opacity: 1; transform: scale(1.08); }}
    }}
    h1 {{
      margin: 0;
      font-size: 28px;
      line-height: 1.15;
      letter-spacing: 0;
    }}
    .subtitle {{
      color: #94a3b8;
      max-width: 860px;
      line-height: 1.55;
      font-size: 13px;
    }}
    .diagram {{
      border: 1px solid #1e293b;
      border-radius: 12px;
      overflow: hidden;
      background: #020617;
    }}
    svg {{
      display: block;
      width: 100%;
      height: auto;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-top: 16px;
    }}
    .card {{
      border: 1px solid #1e293b;
      border-radius: 8px;
      background: rgba(15, 23, 42, .72);
      padding: 14px;
    }}
    .card h3 {{
      margin: 0 0 10px;
      font-size: 12px;
      color: #f8fafc;
    }}
    .card ul {{
      margin: 0;
      padding-left: 16px;
      color: #94a3b8;
      font-size: 10px;
      line-height: 1.55;
    }}
    footer {{
      margin-top: 18px;
      color: #64748b;
      font-size: 10px;
    }}
    @media (max-width: 820px) {{
      .cards {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 22px; }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <header>
      <div class="status"><span class="dot"></span> Deterministic repo-local diagram</div>
      <h1>{safe_title}</h1>
      <p class="subtitle">The agent can suggest a local action, stage it as a pending row, apply it once after explicit confirmation, write the target table or artifact, and return the resulting link with an audit trail.</p>
    </header>

    <section class="diagram" aria-label="Gumroad Merchant agent action architecture diagram">
      <svg viewBox="0 0 1000 700" role="img" aria-labelledby="diagram-title diagram-desc">
        <title id="diagram-title">{safe_title}</title>
        <desc id="diagram-desc">Gumroad Merchant agent action flow from UI through chat agent, pending actions, applied writes, artifacts, and audit trail.</desc>
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" stroke-width="0.5"/>
          </pattern>
          <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#64748b"/>
          </marker>
        </defs>
        <rect width="1000" height="700" fill="#020617"/>
        <rect width="1000" height="700" fill="url(#grid)" opacity="0.65"/>

        <rect x="34" y="74" width="932" height="452" rx="12" fill="none" stroke="#fbbf24" stroke-width="1.4" stroke-dasharray="8,4"/>
        <text x="54" y="100" fill="#fbbf24" font-size="10" font-weight="600">LOCAL TEST PROFILE - simulated writes only</text>

        {arrow(190, 198, 310, 198, "POST /api/agent/chat")}
        {arrow(430, 198, 552, 198, "stage action")}
        {arrow(670, 198, 790, 198, "apply once")}
        {arrow(670, 322, 790, 322, "artifact write")}
        {arrow(550, 246, 550, 300, "confirm")}
        {arrow(550, 390, 550, 448, "audit event")}

        {component(70, 154, 120, 88, "Demo UI", "chat + tables", "rgba(8, 51, 68, 0.4)", "#22d3ee")}
        {component(310, 154, 120, 88, "FastAPI", "chat + action API", "rgba(6, 78, 59, 0.4)", "#34d399")}
        {component(552, 154, 118, 88, "Agent Harness", "suggest + confirm", "rgba(6, 78, 59, 0.4)", "#34d399")}
        {component(790, 154, 128, 88, "tracked_campaigns", "local UTM rows", "rgba(76, 29, 149, 0.4)", "#a78bfa")}

        {component(492, 300, 116, 74, "agent_actions", "pending/applied", "rgba(76, 29, 149, 0.4)", "#a78bfa")}
        {component(790, 290, 128, 88, "Artifacts", "roadmap + diagram", "rgba(30, 41, 59, 0.5)", "#94a3b8")}
        {component(492, 448, 116, 74, "Audit Events", "who/what/when", "rgba(136, 19, 55, 0.4)", "#fb7185")}

        <rect x="70" y="566" width="154" height="34" rx="4" fill="rgba(251, 146, 60, 0.3)" stroke="#fb923c" stroke-width="1"/>
        <text x="147" y="588" fill="#fb923c" font-size="8" text-anchor="middle">idempotency key</text>
        <path d="M 224 583 L 492 485" stroke="#fb923c" stroke-width="1.2" stroke-dasharray="4,4" fill="none" marker-end="url(#arrowhead)"/>

        <rect x="250" y="566" width="164" height="34" rx="4" fill="rgba(251, 146, 60, 0.3)" stroke="#fb923c" stroke-width="1"/>
        <text x="332" y="588" fill="#fb923c" font-size="8" text-anchor="middle">explicit confirmation</text>
        <path d="M 414 583 L 548 374" stroke="#fb923c" stroke-width="1.2" stroke-dasharray="4,4" fill="none" marker-end="url(#arrowhead)"/>

        <rect x="440" y="566" width="196" height="34" rx="4" fill="rgba(251, 146, 60, 0.3)" stroke="#fb923c" stroke-width="1"/>
        <text x="538" y="588" fill="#fb923c" font-size="8" text-anchor="middle">no production Gumroad writes</text>
        <path d="M 636 583 L 790 358" stroke="#fb923c" stroke-width="1.2" stroke-dasharray="4,4" fill="none" marker-end="url(#arrowhead)"/>

        <rect x="664" y="566" width="190" height="34" rx="4" fill="rgba(251, 146, 60, 0.3)" stroke="#fb923c" stroke-width="1"/>
        <text x="759" y="588" fill="#fb923c" font-size="8" text-anchor="middle">download URL returned</text>
        <path d="M 790 566 L 850 378" stroke="#fb923c" stroke-width="1.2" stroke-dasharray="4,4" fill="none" marker-end="url(#arrowhead)"/>

        <g transform="translate(54 638)">
          <rect x="0" y="0" width="890" height="38" rx="6" fill="rgba(15, 23, 42, .88)" stroke="#1e293b"/>
          <circle cx="22" cy="19" r="5" fill="#22d3ee"/><text x="36" y="23" fill="#94a3b8" font-size="8">frontend</text>
          <circle cx="132" cy="19" r="5" fill="#34d399"/><text x="146" y="23" fill="#94a3b8" font-size="8">backend / agent</text>
          <circle cx="286" cy="19" r="5" fill="#a78bfa"/><text x="300" y="23" fill="#94a3b8" font-size="8">SQLite tables</text>
          <circle cx="420" cy="19" r="5" fill="#94a3b8"/><text x="434" y="23" fill="#94a3b8" font-size="8">local artifacts</text>
          <circle cx="560" cy="19" r="5" fill="#fb7185"/><text x="574" y="23" fill="#94a3b8" font-size="8">audit trail</text>
        </g>
      </svg>
    </section>

    <section class="cards">
      <div class="card">
        <h3>Action Control</h3>
        <ul>
          <li>Pending rows hold draft intent before a write.</li>
          <li>Confirmation applies the action once.</li>
          <li>Idempotency prevents duplicate campaign rows.</li>
        </ul>
      </div>
      <div class="card">
        <h3>Write Targets</h3>
        <ul>
          <li>Tracked campaigns create local UTM rows.</li>
          <li>Roadmaps and diagrams create downloadable files.</li>
          <li>Production Gumroad writes remain blocked.</li>
        </ul>
      </div>
      <div class="card">
        <h3>Audit Trail</h3>
        <ul>
          <li>Every staged/applied action is stored.</li>
          <li>Results include URLs and file paths.</li>
          <li>MCP and chat share the same tool layer.</li>
        </ul>
      </div>
    </section>

    <footer>Generated at {html.escape(generated_at)} by gumroad_merchant.architecture_diagram_tools.</footer>
  </main>
</body>
</html>
"""


def generate_architecture_diagram_artifact(
    diagram_type: str = "agent-action-system",
    title: str | None = None,
) -> dict[str, Any]:
    if diagram_type != "agent-action-system":
        diagram_type = "agent-action-system"
    title = title or "Gumroad Merchant agent action architecture"
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    filename = f"{slugify(title)}-{generated_at}.html"
    ARCHITECTURE_DIR.mkdir(parents=True, exist_ok=True)
    path = ARCHITECTURE_DIR / filename
    path.write_text(render_agent_action_diagram(title, generated_at), encoding="utf-8")
    return {
        "artifact_id": filename.removesuffix(".html"),
        "artifact_type": "architecture",
        "diagram_type": diagram_type,
        "title": title,
        "format": "html",
        "file_path": str(path),
        "download_url": f"/api/artifacts/architecture/{filename}",
        "source": "repo-local deterministic architecture diagram tool",
    }
