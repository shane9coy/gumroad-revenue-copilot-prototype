from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gumroad_merchant.analytics_tools import (
    build_strategy_plan_tool,
    format_currency,
    format_percent,
    get_detected_signals_tool,
    get_product_metrics_tool,
)
from gumroad_merchant.content_radar_tools import list_content_trends_tool
from gumroad_merchant.settings import PROJECT_ROOT


ROADMAP_DIR = PROJECT_ROOT / "artifacts" / "roadmaps"


def slugify(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned or "roadmap"


def money(metrics: dict[str, Any]) -> str:
    product = metrics["product"]
    return format_currency(metrics["current"]["revenue_cents"], product["currency"])


def signal_rows(signals: list[dict[str, Any]]) -> str:
    if not signals:
        return "<li>No high-confidence local signals were available for this selection.</li>"
    rows = []
    for signal in signals[:5]:
        rows.append(
            "<li>"
            f"<strong>{html.escape(signal.get('title', 'Signal'))}</strong>: "
            f"{html.escape(signal.get('summary', signal.get('label', 'Review this signal.')))}"
            "</li>"
        )
    return "\n".join(rows)


def trend_rows(trends: list[dict[str, Any]]) -> str:
    if not trends:
        return "<li>No Content Radar trend rows are seeded for this selection.</li>"
    rows = []
    for trend in trends[:4]:
        kpi = trend.get("expected_kpi") or {}
        target = kpi.get("target_formatted") or kpi.get("name") or "tracked campaign read"
        rows.append(
            "<li>"
            f"<strong>{html.escape(trend.get('title', 'Content test'))}</strong> on "
            f"{html.escape(trend.get('channel', 'best-fit channel'))}: "
            f"{html.escape(trend.get('rationale', 'Use as a controlled content test.'))} "
            f"<em>Target: {html.escape(str(target))}</em>"
            "</li>"
        )
    return "\n".join(rows)


def plan_rows(plan: dict[str, Any], horizon_days: int) -> str:
    steps = plan.get("plan_steps") or plan.get("pillars") or []
    if not steps:
        return "<li>Review current analytics, choose one controlled campaign, and measure the result before widening promotion.</li>"
    max_steps = 8 if horizon_days >= 60 else 4
    rows = []
    for index, step in enumerate(steps[:max_steps], start=1):
        move = step.get("move") or step.get("name") or "Review campaign move"
        why = step.get("why") or step.get("evidence") or "Tied to seeded analytics and Content Radar evidence."
        rows.append(
            "<li>"
            f"<span>Day {index * 7 if horizon_days >= 30 else index}</span>"
            f"<strong>{html.escape(move)}</strong>"
            f"<p>{html.escape(why)}</p>"
            "</li>"
        )
    return "\n".join(rows)


def render_roadmap_html(
    metrics: dict[str, Any],
    signals: list[dict[str, Any]],
    trends: list[dict[str, Any]],
    plan: dict[str, Any],
    horizon_days: int,
    generated_at: str,
) -> str:
    product = metrics["product"]
    current = metrics["current"]
    derived = metrics["derived"]
    title = f"{horizon_days}-day roadmap for {product['name']}"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #111827;
      --muted: #4b5563;
      --line: #d1d5db;
      --paper: #ffffff;
      --wash: #f8fafc;
      --accent: #16a34a;
    }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--wash);
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 48px 28px 64px;
    }}
    header {{
      border-bottom: 2px solid var(--ink);
      padding-bottom: 22px;
      margin-bottom: 26px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 36px;
      line-height: 1.05;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 32px 0 12px;
      font-size: 18px;
      letter-spacing: 0;
    }}
    p {{
      color: var(--muted);
      line-height: 1.6;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 24px 0;
    }}
    .metric, section {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }}
    .metric strong {{
      font-size: 20px;
    }}
    ul, ol {{
      padding-left: 22px;
      line-height: 1.55;
    }}
    li + li {{
      margin-top: 10px;
    }}
    ol.timeline {{
      list-style: none;
      padding: 0;
    }}
    ol.timeline li {{
      border-left: 3px solid var(--accent);
      padding-left: 14px;
    }}
    ol.timeline span {{
      display: block;
      color: var(--accent);
      font-weight: 700;
      font-size: 12px;
      margin-bottom: 4px;
    }}
    ol.timeline p {{
      margin: 4px 0 0;
    }}
    footer {{
      margin-top: 28px;
      color: var(--muted);
      font-size: 12px;
    }}
    @media (max-width: 760px) {{
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      h1 {{ font-size: 28px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{html.escape(title)}</h1>
      <p>Generated from the local Gumroad Merchant test dataset. This is a downloadable planning artifact, not an email send, external post, product edit, or production Gumroad action.</p>
    </header>

    <div class="metrics">
      <div class="metric"><span>Revenue</span><strong>{html.escape(money(metrics))}</strong></div>
      <div class="metric"><span>Sales</span><strong>{current['sales']:,}</strong></div>
      <div class="metric"><span>Conversion</span><strong>{html.escape(format_percent(derived['current_conversion']))}</strong></div>
      <div class="metric"><span>Refund rate</span><strong>{html.escape(format_percent(derived['current_refund_rate']))}</strong></div>
    </div>

    <section>
      <h2>Why these moves</h2>
      <ul>{signal_rows(signals)}</ul>
    </section>

    <section>
      <h2>Campaign opportunities</h2>
      <ul>{trend_rows(trends)}</ul>
    </section>

    <section>
      <h2>{horizon_days}-day execution path</h2>
      <ol class="timeline">{plan_rows(plan, horizon_days)}</ol>
    </section>

    <footer>Generated at {html.escape(generated_at)} from seeded local analytics.</footer>
  </main>
</body>
</html>
"""


def generate_roadmap_artifact(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    horizon_days: int = 30,
) -> dict[str, Any]:
    horizon_days = 60 if int(horizon_days) >= 60 else 30
    metrics = get_product_metrics_tool(db_path, product_id=product_id, date_range=date_range)
    signals = get_detected_signals_tool(db_path, product_id=product_id, date_range=date_range)
    trends = list_content_trends_tool(db_path, product_id=product_id, date_range=date_range, limit=4)
    plan = build_strategy_plan_tool(
        db_path,
        product_id=product_id,
        date_range=date_range,
        horizon_months=2 if horizon_days >= 60 else 3,
    )
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    product_slug = slugify(metrics["product"]["name"])
    filename = f"gumroad-{product_slug}-{horizon_days}d-roadmap-{generated_at}.html"
    ROADMAP_DIR.mkdir(parents=True, exist_ok=True)
    path = ROADMAP_DIR / filename
    path.write_text(
        render_roadmap_html(metrics, signals, trends, plan, horizon_days, generated_at),
        encoding="utf-8",
    )
    return {
        "artifact_id": filename.removesuffix(".html"),
        "artifact_type": "roadmap",
        "title": f"{horizon_days}-day roadmap for {metrics['product']['name']}",
        "format": "html",
        "horizon_days": horizon_days,
        "file_path": str(path),
        "download_url": f"/api/artifacts/roadmaps/{filename}",
        "source": "selected local analytics profile",
    }
