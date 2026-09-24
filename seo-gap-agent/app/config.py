from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    gsc_client_id: str
    gsc_client_secret: str
    gsc_refresh_token: str
    gsc_site_url: str
    openai_model: str = "gpt-4.1-mini"
    min_impressions: int = 1
    min_position: float = 1.0
    max_position: float = 12.0
    max_rows: int = 50_000
    top_n: int = 5
    request_timeout_seconds: int = 20
    openai_max_retries: int = 6
    openai_base_retry_delay_seconds: float = 1.0
    openai_max_retry_delay_seconds: float = 45.0
    exclude_brand_queries: list[str] = field(default_factory=list)
    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1])

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def reports_dir(self) -> Path:
        return self.project_root / "reports"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "seo_gap_agent.db"

    @property
    def start_date(self) -> str:
        return (date.today() - timedelta(days=28)).isoformat()

    @property
    def end_date(self) -> str:
        return date.today().isoformat()


def _parse_brand_queries(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [q.strip().lower() for q in raw.split(",") if q.strip()]


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return float(raw)


def load_settings() -> Settings:
    required = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "GSC_CLIENT_ID": os.getenv("GSC_CLIENT_ID", ""),
        "GSC_CLIENT_SECRET": os.getenv("GSC_CLIENT_SECRET", ""),
        "GSC_REFRESH_TOKEN": os.getenv("GSC_REFRESH_TOKEN", ""),
        "GSC_SITE_URL": os.getenv("GSC_SITE_URL", ""),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    settings = Settings(
        openai_api_key=required["OPENAI_API_KEY"],
        gsc_client_id=required["GSC_CLIENT_ID"],
        gsc_client_secret=required["GSC_CLIENT_SECRET"],
        gsc_refresh_token=required["GSC_REFRESH_TOKEN"],
        gsc_site_url=required["GSC_SITE_URL"],
        openai_model=(os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip(),
        min_impressions=_int_env("MIN_IMPRESSIONS", 1),
        min_position=_float_env("MIN_POSITION", 1.0),
        max_position=_float_env("MAX_POSITION", 12.0),
        top_n=_int_env("TOP_N", 5),
        openai_max_retries=_int_env("OPENAI_MAX_RETRIES", 6),
        openai_base_retry_delay_seconds=_float_env("OPENAI_BASE_RETRY_DELAY_SECONDS", 1.0),
        openai_max_retry_delay_seconds=_float_env("OPENAI_MAX_RETRY_DELAY_SECONDS", 45.0),
        exclude_brand_queries=_parse_brand_queries(os.getenv("EXCLUDE_BRAND_QUERIES")),
    )

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    return settings
