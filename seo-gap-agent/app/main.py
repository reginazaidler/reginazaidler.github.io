from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from app.analyzer import analyze_page_gap
from app.config import load_settings
from app.db import bulk_insert, get_connection, init_db
from app.fetch_gsc_data import GSCFetchParams, fetch_gsc_data
from app.gsc_client import GSCClient
from app.new_queries import mark_new_queries
from app.opportunity_scoring import filter_opportunities, score_opportunities
from app.page_extractor import extract_page_snapshot
from app.report_builder import build_reports


def _empty_opportunities_df():
    import pandas as pd

    return pd.DataFrame(
        columns=[
            "query",
            "page",
            "clicks",
            "impressions",
            "ctr",
            "position",
            "expected_ctr",
            "opportunity_score",
        ]
    )


def _analysis_cache_key(model: str, payload: dict) -> str:
    stable = json.dumps({"model": model, "payload": payload}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()

def _cached_analysis(cache_dir: Path, key: str):
    path = cache_dir / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _save_analysis_cache(cache_dir: Path, key: str, analysis: dict) -> None:
    if analysis.get("_meta", {}).get("fallback_reason"):
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

def run_pipeline() -> None:
    settings = load_settings()
    conn = get_connection(settings.db_path)
    init_db(conn)

    gsc_client = GSCClient(
        client_id=settings.gsc_client_id,
        client_secret=settings.gsc_client_secret,
        refresh_token=settings.gsc_refresh_token,
        site_url=settings.gsc_site_url,
        timeout=settings.request_timeout_seconds,
    )

    fetch_params = GSCFetchParams(
        start_date=settings.start_date,
        end_date=settings.end_date,
        max_rows=settings.max_rows,
    )
    raw_df = fetch_gsc_data(gsc_client, fetch_params)
    fetched_at = str(raw_df["fetched_at"].iloc[0]) if not raw_df.empty else ""
    print(f"Fetched {len(raw_df)} query-page rows from GSC ({settings.start_date} to {settings.end_date}).")

    if raw_df.empty:
        build_reports(settings.reports_dir, _empty_opportunities_df(), [])
        print("No GSC rows returned. Generated empty reports.")
        return

    impressions_mask = raw_df["impressions"] >= settings.min_impressions
    position_mask = (raw_df["position"] >= settings.min_position) & (raw_df["position"] <= settings.max_position)
    brand_mask = raw_df["query"].astype(str).str.lower()
    brand_pattern = "|".join(settings.exclude_brand_queries) if settings.exclude_brand_queries else ""
    brand_pass_mask = ~brand_mask.str.contains(brand_pattern, regex=True, na=False) if brand_pattern else None

    print(
        "Filter diagnostics:",
        f"impressions>={settings.min_impressions}: {int(impressions_mask.sum())}/{len(raw_df)};",
        f"position_between_{settings.min_position}_{settings.max_position}: {int(position_mask.sum())}/{len(raw_df)};",
        (
            f"brand_excluded_pass: {int(brand_pass_mask.sum())}/{len(raw_df)};"
            if brand_pass_mask is not None
            else "brand_excluded_pass: skipped;"
        ),
    )

    bulk_insert(
        conn,
        """
        INSERT INTO query_page_metrics (
            query, page, clicks, impressions, ctr, position, start_date, end_date, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row.query,
                row.page,
                float(row.clicks),
                float(row.impressions),
                float(row.ctr),
                float(row.position),
                row.start_date,
                row.end_date,
                row.fetched_at,
            )
            for row in raw_df.itertuples(index=False)
        ],
    )

    raw_df = mark_new_queries(conn, raw_df, fetched_at=fetched_at)
    new_queries_count = int(raw_df["is_new_query"].sum())
    print(f"Detected {new_queries_count} new queries in this run.")

    filtered_df = filter_opportunities(
        df=raw_df,
        min_impressions=settings.min_impressions,
        min_position=settings.min_position,
        max_position=settings.max_position,
        exclude_brand_queries=settings.exclude_brand_queries,
    )

    scored_df = score_opportunities(filtered_df)
    top_df = scored_df.head(settings.top_n).copy()

    if top_df.empty:
        # Fallback: if strict filters return nothing, continue with the best rows
        # from raw data so the run still returns actionable output files.
        fallback_df = score_opportunities(raw_df).head(settings.top_n).copy()
        if fallback_df.empty:
            build_reports(settings.reports_dir, _empty_opportunities_df(), [])
            print("No opportunities found after fallback. Generated empty reports.")
            return
        top_df = fallback_df
        print("No opportunities matched strict filters; using fallback ranking from raw GSC data.")

    selected_at = datetime.now(timezone.utc).isoformat()
    bulk_insert(
        conn,
        """
        INSERT INTO opportunities (
            query, page, clicks, impressions, ctr, position, expected_ctr, opportunity_score, selected_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row.query,
                row.page,
                float(row.clicks),
                float(row.impressions),
                float(row.ctr),
                float(row.position),
                float(row.expected_ctr),
                float(row.opportunity_score),
                selected_at,
            )
            for row in top_df.itertuples(index=False)
        ],
    )

    analysis_items: list[dict] = []
    openai_rate_limited = False

    for row in top_df.itertuples(index=False):
        try:
            snapshot = extract_page_snapshot(row.page, timeout=settings.request_timeout_seconds)
        except Exception as exc:
            # GSC can retain historical URLs after a page was removed or renamed.
            # One stale URL must not abort the whole daily optimization run.
            print(f"Skipping page snapshot for {row.page}: {type(exc).__name__}: {exc}")
            continue

        bulk_insert(
            conn,
            """
            INSERT INTO page_snapshots (
                page, title, meta_description, h1, h2s_json, main_content, html_fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    snapshot.page,
                    snapshot.title,
                    snapshot.meta_description,
                    snapshot.h1,
                    json.dumps(snapshot.h2s, ensure_ascii=False),
                    snapshot.main_content,
                    datetime.now(timezone.utc).isoformat(),
                )
            ],
        )

        if openai_rate_limited:
            analysis = {
                "query_intent": "unknown",
                "why_not_rank_1": [
                    "OpenAI analysis skipped because a previous request in this run hit persistent rate limits"
                ],
                "title_fix": "Retry this run later to generate title recommendations.",
                "opening_paragraph_fix": "Retry this run later to generate opening paragraph recommendations.",
                "sections_to_add": ["Retry analysis after rate limit window resets"],
                "faq_to_add": ["What should we improve once analysis is available?"],
                "trust_elements_to_add": ["N/A (rate-limited run)"],
                "cta_fix": "Retry this run later to generate CTA recommendations.",
                "priority": "low",
                "_meta": {
                    "fallback_reason": "openai_rate_limit_short_circuit",
                    "status_code": 429,
                },
            }
        else:
            analysis_payload = {
                "query": row.query,
                "page": row.page,
                "position": float(row.position),
                "ctr": float(row.ctr),
                "is_new_query": bool(getattr(row, "is_new_query", False)),
                "title": snapshot.title,
                "meta_description": snapshot.meta_description,
                "h1": snapshot.h1,
                "h2s": snapshot.h2s,
                "main_content": snapshot.main_content,
            }
            cache_dir = settings.data_dir / "analysis-cache"
            cache_key = _analysis_cache_key(settings.openai_model, analysis_payload)
            analysis = _cached_analysis(cache_dir, cache_key)
            if analysis is not None:
                print(f"Using cached OpenAI analysis for {row.query} -> {row.page}")
            else:
                analysis = analyze_page_gap(
                    api_key=settings.openai_api_key,
                    model=settings.openai_model,
                    payload=analysis_payload,
                    timeout=max(40, settings.request_timeout_seconds),
                    max_attempts=settings.openai_max_retries,
                    base_retry_delay_seconds=settings.openai_base_retry_delay_seconds,
                    max_retry_delay_seconds=settings.openai_max_retry_delay_seconds,
                )
                _save_analysis_cache(cache_dir, cache_key, analysis)

            if analysis.get("_meta", {}).get("status_code") == 429:
                openai_rate_limited = True
                print(
                    "OpenAI returned persistent 429 rate-limit responses. "
                    "Skipping further OpenAI calls for this run and using fallback analysis."
                )

        analysis_items.append(
            {
                "query": row.query,
                "page": row.page,
                "position": float(row.position),
                "impressions": float(row.impressions),
                "opportunity_score": float(row.opportunity_score),
                "is_new_query": bool(getattr(row, "is_new_query", False)),
                "analysis": analysis,
            }
        )

    build_reports(settings.reports_dir, top_df, analysis_items)
    print("Pipeline completed successfully.")


if __name__ == "__main__":
    try:
        run_pipeline()
    except RuntimeError as exc:
        message = str(exc)
        if "invalid_grant" in message.lower() or "refresh token is invalid" in message.lower():
            print("::error::Google OAuth refresh token failed. Check GSC_REFRESH_TOKEN and OAuth consent screen status.")
            print(
                "Troubleshooting: publish OAuth consent screen to Production, generate a fresh refresh token, "
                "update GitHub Secret GSC_REFRESH_TOKEN, then re-run this workflow."
            )
        raise
