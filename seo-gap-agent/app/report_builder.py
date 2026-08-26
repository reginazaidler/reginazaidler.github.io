from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def build_reports(
    reports_dir: Path,
    opportunities_df: pd.DataFrame,
    analysis_items: list[dict[str, Any]],
) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)

    csv_path = reports_dir / "top_opportunities.csv"
    md_path = reports_dir / "fixes_report.md"
    json_path = reports_dir / "dev_tasks.json"

    # Use UTF-8 BOM so Excel detects Hebrew/non-Latin text correctly on open.
    opportunities_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    markdown_lines: list[str] = [
        "# SEO Gap Agent Report",
        "",
        "## Top Opportunities",
        "",
    ]

    dev_tasks: list[dict[str, Any]] = []

    for idx, item in enumerate(analysis_items, start=1):
        analysis = item["analysis"]
        fallback_reason = analysis.get("_meta", {}).get("fallback_reason")
        rate_limited = fallback_reason in {"rate_limit", "openai_retryable_error"}
        issues = ", ".join(analysis.get("why_not_rank_1", [])) if analysis.get("why_not_rank_1") else "N/A"
        markdown_lines.extend(
            [
                f"### {idx}. Query: `{item['query']}`",
                f"- **Page:** {item['page']}",
                f"- **Position:** {item['position']:.2f}",
                f"- **Impressions:** {item['impressions']:.0f}",
                f"- **Opportunity Score:** {item['opportunity_score']:.4f}",
                f"- **New Query:** {'yes' if item.get('is_new_query') else 'no'}",
                f"- **Issues:** {issues}",
                (
                    "- **AI Analysis:** unavailable due to OpenAI rate limit in this run."
                    if rate_limited
                    else "- **Exact Fixes:**"
                ),
                (
                    "- Re-run this workflow later (or with higher API limits) to get concrete AI fixes."
                    if rate_limited
                    else f"  - Title: {analysis['title_fix']}"
                ),
                ("" if rate_limited else f"  - Opening paragraph: {analysis['opening_paragraph_fix']}"),
                ("" if rate_limited else f"  - Sections to add: {', '.join(analysis['sections_to_add'])}"),
                ("" if rate_limited else f"  - FAQ to add: {', '.join(analysis['faq_to_add'])}"),
                ("" if rate_limited else f"  - Trust elements: {', '.join(analysis['trust_elements_to_add'])}"),
                ("" if rate_limited else f"  - CTA fix: {analysis['cta_fix']}"),
                (
                    ""
                    if rate_limited
                    else f"  - Recommended action: {analysis.get('recommended_action', 'improve_existing_page')}"
                ),
                (
                    ""
                    if rate_limited or not analysis.get("new_page_slug")
                    else f"  - New page slug: {analysis['new_page_slug']}"
                ),
                f"  - Priority: {analysis['priority']}",
                "",
            ]
        )

        dev_tasks.append(
            {
                "query": item["query"],
                "page": item["page"],
                "position": item["position"],
                "opportunity_score": item["opportunity_score"],
                "priority": analysis["priority"],
                "is_new_query": bool(item.get("is_new_query", False)),
                "recommended_action": analysis.get("recommended_action", "improve_existing_page"),
                "new_page_slug": analysis.get("new_page_slug", ""),
                "analysis_status": "rate_limited" if rate_limited else "ok",
                "tasks": {
                    "title_fix": "" if rate_limited else analysis["title_fix"],
                    "opening_paragraph_fix": "" if rate_limited else analysis["opening_paragraph_fix"],
                    "sections_to_add": [] if rate_limited else analysis["sections_to_add"],
                    "faq_to_add": [] if rate_limited else analysis["faq_to_add"],
                    "trust_elements_to_add": [] if rate_limited else analysis["trust_elements_to_add"],
                    "cta_fix": "" if rate_limited else analysis["cta_fix"],
                },
            }
        )

    md_path.write_text("\n".join(markdown_lines), encoding="utf-8")
    json_path.write_text(json.dumps(dev_tasks, indent=2, ensure_ascii=False), encoding="utf-8")
