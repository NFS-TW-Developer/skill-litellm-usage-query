#!/usr/bin/env python3
"""查詢 LiteLLM Gateway 每日使用量（aggregated activity）。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import matplotlib
import requests

matplotlib.use("Agg")

import matplotlib.pyplot as plt

DEFAULT_BASE_URL = "http://litellm:4000"
ENDPOINT_PATH = "/user/daily/activity/aggregated"
KEY_LIST_PATH = "/key/list"

stdout_reconfigure = getattr(sys.stdout, "reconfigure", None)
if callable(stdout_reconfigure):
    stdout_reconfigure(encoding="utf-8")


def load_dotenv(path: Path) -> None:
    """簡易讀取 .env，不覆蓋已存在的環境變數。"""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="查詢 LiteLLM Gateway 使用者每日使用量（aggregated activity）"
    )
    parser.add_argument("--start-date", required=True, help="起始日期，格式 YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="結束日期，格式 YYYY-MM-DD")
    parser.add_argument(
        "--timezone",
        type=int,
        default=-480,
        help="時區偏移（分鐘），預設 -480（UTC+8）",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LITELLM_BASE_URL", DEFAULT_BASE_URL),
        help="Gateway 基底網址",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("LITELLM_API_KEY"),
        help="API Key（也可用環境變數 LITELLM_API_KEY）",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="輸出逐日彙整後的完整 JSON，不做摘要",
    )
    parser.add_argument(
        "--include-key-map",
        action="store_true",
        help="附帶抓取 /key/list 並輸出 key 對應與使用者排行",
    )
    parser.add_argument(
        "--user-rank-by",
        choices=("spend", "tokens", "requests"),
        default="spend",
        help="使用者排行排序欄位，預設依花費排序",
    )
    parser.add_argument(
        "--include-model-ranking",
        action="store_true",
        help="輸出 Top Public Model Names 排行",
    )
    parser.add_argument(
        "--model-rank-by",
        choices=("spend", "tokens", "requests"),
        default="spend",
        help="Model 排行排序欄位，預設依花費排序",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="排行顯示筆數，預設 10",
    )
    parser.add_argument(
        "--chart",
        choices=(
            "daily-spend",
            "daily-tokens",
            "daily-requests",
            "user-spend",
            "user-tokens",
            "user-requests",
            "user-spend-pie",
            "user-tokens-pie",
            "user-requests-pie",
            "model-spend",
            "model-tokens",
            "model-requests",
            "model-spend-pie",
            "model-tokens-pie",
            "model-requests-pie",
        ),
        default=None,
        help="輸出圖表類型",
    )
    parser.add_argument(
        "--chart-output",
        default=None,
        help="圖檔輸出路徑，例如 reports/usage.png",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="自訂 .env 路徑（預設為腳本上層目錄的 .env）",
    )
    return parser.parse_args()


def validate_date(value: str, label: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"{label} 格式錯誤，請使用 YYYY-MM-DD：{value}") from exc
    return value


def fetch_usage(
    base_url: str,
    api_key: str,
    start_date: str,
    end_date: str,
    timezone: int,
) -> Any:
    url = f"{base_url.rstrip('/')}{ENDPOINT_PATH}"
    headers = {"x-litellm-api-key": api_key, "Accept": "application/json"}
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "timezone": timezone,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
    except requests.RequestException as exc:
        raise SystemExit(f"連線失敗：{exc}") from exc

    if response.status_code == 401:
        raise SystemExit("認證失敗（401）：請確認 LITELLM_API_KEY 是否正確。")
    if response.status_code == 403:
        raise SystemExit("權限不足（403）：此 API Key 無法查詢使用量。")
    if not response.ok:
        body = response.text[:500]
        raise SystemExit(f"API 錯誤（HTTP {response.status_code}）：{body}")

    try:
        return response.json()
    except json.JSONDecodeError as exc:
        raise SystemExit(f"回應不是有效 JSON：{response.text[:300]}") from exc


def fetch_json(base_url: str, api_key: str, path: str, params: dict[str, Any] | None = None) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    headers = {"x-litellm-api-key": api_key, "Accept": "application/json"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
    except requests.RequestException as exc:
        suffix = f"?{urlencode(params, doseq=True)}" if params else ""
        raise SystemExit(f"連線失敗：GET {path}{suffix}：{exc}") from exc

    if not response.ok:
        body = response.text[:500]
        raise SystemExit(f"API 錯誤（GET {path} HTTP {response.status_code}）：{body}")

    try:
        return response.json()
    except json.JSONDecodeError as exc:
        raise SystemExit(f"回應不是有效 JSON：{response.text[:300]}") from exc


def as_number(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def empty_metrics() -> dict[str, float]:
    return {
        "spend": 0.0,
        "prompt_tokens": 0.0,
        "completion_tokens": 0.0,
        "cache_read_input_tokens": 0.0,
        "cache_creation_input_tokens": 0.0,
        "total_tokens": 0.0,
        "successful_requests": 0.0,
        "failed_requests": 0.0,
        "api_requests": 0.0,
    }


def merge_metrics(target: dict[str, float], source: dict[str, Any]) -> None:
    for key in target:
        target[key] += as_number(source.get(key))


def pick_first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def extract_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        records = data.get("data") or data.get("results") or data.get("activity") or []
    elif isinstance(data, list):
        records = data
    else:
        records = []

    return [row for row in records if isinstance(row, dict)]


def aggregate_records(records: list[dict[str, Any]], label: str) -> dict[str, Any]:
    totals = {
        "date": label,
        "metrics": empty_metrics(),
        "api_key_breakdown": {},
        "model_group_breakdown": {},
    }

    for row in records:
        raw_metrics = row.get("metrics")
        metrics: dict[str, Any] = raw_metrics if isinstance(raw_metrics, dict) else row
        merge_metrics(totals["metrics"], metrics)

        breakdown = row.get("breakdown")
        if not isinstance(breakdown, dict):
            continue
        api_keys_group = breakdown.get("api_keys")
        if not isinstance(api_keys_group, dict):
            pass
        else:
            for key_hash, entry in api_keys_group.items():
                if not isinstance(entry, dict):
                    continue
                bucket_any = totals["api_key_breakdown"].setdefault(
                    key_hash,
                    {
                        "metrics": empty_metrics(),
                        "metadata": entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {},
                    },
                )
                bucket: dict[str, Any] = bucket_any if isinstance(bucket_any, dict) else {}
                entry_metrics_any = entry.get("metrics")
                entry_metrics: dict[str, Any] = (
                    entry_metrics_any if isinstance(entry_metrics_any, dict) else {}
                )
                merge_metrics(bucket["metrics"], entry_metrics)

        model_groups = breakdown.get("model_groups")
        if not isinstance(model_groups, dict):
            continue
        for model_name, entry in model_groups.items():
            if not isinstance(entry, dict):
                continue
            bucket_any = totals["model_group_breakdown"].setdefault(
                model_name,
                {
                    "metrics": empty_metrics(),
                    "metadata": entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {},
                },
            )
            bucket: dict[str, Any] = bucket_any if isinstance(bucket_any, dict) else {}
            entry_metrics_any = entry.get("metrics")
            entry_metrics: dict[str, Any] = (
                entry_metrics_any if isinstance(entry_metrics_any, dict) else {}
            )
            merge_metrics(bucket["metrics"], entry_metrics)

    return totals


def fetch_usage_split_by_day(
    base_url: str,
    api_key: str,
    start_date: str,
    end_date: str,
    timezone: int,
) -> dict[str, Any]:
    """逐日查詢並合併每次回傳的相鄰日期資料。"""
    current = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    results: list[dict[str, Any]] = []

    while current <= end:
        day = current.isoformat()
        data = fetch_usage(base_url, api_key, day, day, timezone)
        results.append(aggregate_records(extract_records(data), day))
        current += timedelta(days=1)

    return {"results": results}


def fetch_key_map(base_url: str, api_key: str) -> dict[str, Any]:
    first_page = fetch_json(
        base_url,
        api_key,
        KEY_LIST_PATH,
        {"page": 1, "size": 100, "return_full_object": "true", "expand": "user"},
    )
    total_pages = first_page.get("total_pages", 1) if isinstance(first_page, dict) else 1
    page_payloads = [first_page]

    for page in range(2, int(total_pages) + 1):
        page_payloads.append(
            fetch_json(
                base_url,
                api_key,
                KEY_LIST_PATH,
                {"page": page, "size": 100, "return_full_object": "true", "expand": "user"},
            )
        )

    mappings: list[dict[str, Any]] = []
    for payload in page_payloads:
        if not isinstance(payload, dict):
            continue
        keys = payload.get("keys", [])
        if not isinstance(keys, list):
            continue
        for key_info in keys:
            if not isinstance(key_info, dict):
                continue
            user_any = key_info.get("user")
            user = user_any if isinstance(user_any, dict) else {}
            created_by_user_any = key_info.get("created_by_user")
            created_by_user = (
                created_by_user_any if isinstance(created_by_user_any, dict) else {}
            )
            mappings.append(
                {
                    "key": key_info.get("token"),
                    "key_alias": key_info.get("key_alias"),
                    "key_name": key_info.get("key_name"),
                    "user_id": key_info.get("user_id"),
                    "user_email": user.get("user_email") or created_by_user.get("user_email"),
                    "user_role": user.get("user_role") or key_info.get("user_role"),
                    "team_id": key_info.get("team_id"),
                    "spend": key_info.get("spend"),
                    "models": key_info.get("models") or [],
                    "created_at": key_info.get("created_at"),
                    "updated_at": key_info.get("updated_at"),
                    "last_active": key_info.get("last_active"),
                }
            )

    return {"keys": mappings}


def build_user_ranking(
    data: dict[str, Any], key_map: dict[str, Any], rank_by: str
) -> list[dict[str, Any]]:
    key_rows = key_map.get("keys", []) if isinstance(key_map, dict) else []
    key_lookup = {
        row.get("key"): row
        for row in key_rows
        if isinstance(row, dict) and isinstance(row.get("key"), str)
    }

    user_totals: dict[str, dict[str, Any]] = {}
    records = extract_records(data)
    for record in records:
        api_key_breakdown = record.get("api_key_breakdown")
        if not isinstance(api_key_breakdown, dict):
            continue
        for key_hash, entry in api_key_breakdown.items():
            if not isinstance(entry, dict):
                continue
            key_info = key_lookup.get(key_hash, {})
            user_id = key_info.get("user_id") or "unknown"
            user_row = user_totals.setdefault(
                user_id,
                {
                    "user_id": user_id,
                    "user_email": key_info.get("user_email"),
                    "team_id": key_info.get("team_id"),
                    "key_count": 0,
                    "keys": set(),
                    "metrics": empty_metrics(),
                },
            )
            if not user_row.get("user_email") and key_info.get("user_email"):
                user_row["user_email"] = key_info.get("user_email")
            if isinstance(key_hash, str) and key_hash not in user_row["keys"]:
                user_row["keys"].add(key_hash)
                user_row["key_count"] += 1

            entry_metrics_any = entry.get("metrics")
            entry_metrics: dict[str, Any] = (
                entry_metrics_any if isinstance(entry_metrics_any, dict) else {}
            )
            user_metrics: dict[str, float] = user_row["metrics"]
            merge_metrics(user_metrics, entry_metrics)

    ranking: list[dict[str, Any]] = []
    for row in user_totals.values():
        ranking.append(
                {
                    "user_id": row["user_id"],
                    "user_email": row.get("user_email"),
                    "team_id": row.get("team_id"),
                    "key_count": row["key_count"],
                    "metrics": row["metrics"],
                }
            )

    metric_name = {
        "spend": "spend",
        "tokens": "total_tokens",
        "requests": "api_requests",
    }.get(rank_by, "spend")

    ranking.sort(
        key=lambda item: (
            -as_number(item.get("metrics", {}).get(metric_name)),
            -as_number(item.get("metrics", {}).get("spend")),
            -as_number(item.get("metrics", {}).get("api_requests")),
            item.get("user_id") or "",
        )
    )
    return ranking


def build_model_ranking(data: dict[str, Any], rank_by: str) -> list[dict[str, Any]]:
    model_totals: dict[str, dict[str, Any]] = {}
    records = extract_records(data)
    for record in records:
        model_group_breakdown = record.get("model_group_breakdown")
        if not isinstance(model_group_breakdown, dict):
            continue
        for public_name, entry in model_group_breakdown.items():
            if not isinstance(entry, dict):
                continue
            row = model_totals.setdefault(
                public_name,
                {
                    "public_model_name": public_name,
                    "metrics": empty_metrics(),
                },
            )
            entry_metrics_any = entry.get("metrics")
            entry_metrics: dict[str, Any] = (
                entry_metrics_any if isinstance(entry_metrics_any, dict) else {}
            )
            model_metrics: dict[str, float] = row["metrics"]
            merge_metrics(model_metrics, entry_metrics)

    ranking: list[dict[str, Any]] = []
    for row in model_totals.values():
        ranking.append(
            {
                "public_model_name": row["public_model_name"],
                "metrics": row["metrics"],
            }
        )

    metric_name = {
        "spend": "spend",
        "tokens": "total_tokens",
        "requests": "api_requests",
    }.get(rank_by, "spend")
    ranking.sort(
        key=lambda item: (
            -as_number(item.get("metrics", {}).get(metric_name)),
            -as_number(item.get("metrics", {}).get("spend")),
            -as_number(item.get("metrics", {}).get("api_requests")),
            item.get("public_model_name") or "",
        )
    )
    return ranking


def chart_metric_and_label(chart: str) -> tuple[str, str]:
    normalized = chart.removesuffix("-pie")
    if normalized.endswith("spend"):
        return "spend", "Spend"
    if normalized.endswith("tokens"):
        return "total_tokens", "Tokens"
    return "api_requests", "Requests"


def format_timezone_label(offset_minutes: int) -> str:
    total_minutes = -offset_minutes
    sign = "+" if total_minutes >= 0 else "-"
    absolute = abs(total_minutes)
    hours = absolute // 60
    minutes = absolute % 60
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def format_timezone_slug(offset_minutes: int) -> str:
    total_minutes = -offset_minutes
    sign = "plus" if total_minutes >= 0 else "minus"
    absolute = abs(total_minutes)
    hours = absolute // 60
    minutes = absolute % 60
    return f"utc-{sign}-{hours:02d}-{minutes:02d}"


def default_chart_output(chart: str, start_date: str, end_date: str, timezone: int) -> Path:
    timezone_slug = format_timezone_slug(timezone)
    return Path(
        f"reports/{chart}-{start_date}_to_{end_date}-{timezone_slug}.png"
    )


def format_chart_value(value: float) -> str:
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    if float(value).is_integer():
        return f"{value:.0f}"
    return f"{value:,.2f}"


def compress_pie_data(labels: list[str], values: list[float], top_n: int) -> tuple[list[str], list[float]]:
    if len(labels) <= top_n:
        return labels, values

    kept_labels = labels[:top_n]
    kept_values = values[:top_n]
    others_value = sum(values[top_n:])
    if others_value > 0:
        kept_labels.append("Others")
        kept_values.append(others_value)
    return kept_labels, kept_values


def render_chart(data: dict[str, Any], chart: str, output_path: Path) -> Path:
    metric_name, ylabel = chart_metric_and_label(chart)
    is_pie = chart.endswith("-pie")
    date_range = str(data.get("date_range") or "")
    timezone_label = str(data.get("timezone_label") or "")

    if chart.startswith("daily-"):
        rows = extract_records(data)
        labels = [str(row.get("date") or "-") for row in rows]
        values = [
            as_number((row.get("metrics") or {}).get(metric_name))
            if isinstance(row.get("metrics"), dict)
            else 0.0
            for row in rows
        ]
        title = f"Daily {ylabel} ({date_range}, {timezone_label})"
    elif chart.startswith("user-"):
        ranking = data.get("user_ranking")
        if not isinstance(ranking, list) or not ranking:
            raise SystemExit("請先加上 --include-key-map 才能輸出 user 圖表。")
        top_n = data.get("top") if isinstance(data.get("top"), int) and data.get("top") else 10
        sorted_rows = sorted(
            [row for row in ranking if isinstance(row, dict)],
            key=lambda row: (
                -as_number((row.get("metrics") or {}).get(metric_name))
                if isinstance(row.get("metrics"), dict)
                else 0.0,
                -as_number((row.get("metrics") or {}).get("spend"))
                if isinstance(row.get("metrics"), dict)
                else 0.0,
                str(row.get("user_email") or row.get("user_id") or ""),
            ),
        )
        rows = sorted_rows[:top_n]
        labels = [
            str(row.get("user_email") or row.get("user_id") or "unknown") for row in rows
        ]
        values = [
            as_number((row.get("metrics") or {}).get(metric_name))
            if isinstance(row.get("metrics"), dict)
            else 0.0
            for row in rows
        ]
        title = f"Top Users by {ylabel} ({date_range}, {timezone_label})"
    else:
        ranking = data.get("model_ranking")
        if not isinstance(ranking, list) or not ranking:
            raise SystemExit("請先加上 --include-model-ranking 才能輸出 model 圖表。")
        top_n = data.get("top") if isinstance(data.get("top"), int) and data.get("top") else 10
        sorted_rows = sorted(
            [row for row in ranking if isinstance(row, dict)],
            key=lambda row: (
                -as_number((row.get("metrics") or {}).get(metric_name))
                if isinstance(row.get("metrics"), dict)
                else 0.0,
                -as_number((row.get("metrics") or {}).get("spend"))
                if isinstance(row.get("metrics"), dict)
                else 0.0,
                str(row.get("public_model_name") or ""),
            ),
        )
        rows = sorted_rows[:top_n]
        labels = [str(row.get("public_model_name") or "unknown") for row in rows]
        values = [
            as_number((row.get("metrics") or {}).get(metric_name))
            if isinstance(row.get("metrics"), dict)
            else 0.0
            for row in rows
        ]
        title = f"Top Public Model Names by {ylabel} ({date_range}, {timezone_label})"

    if not labels:
        raise SystemExit("沒有可用資料可繪製圖表。")

    top_any = data.get("top") if isinstance(data, dict) else None
    top_n = top_any if isinstance(top_any, int) and top_any > 0 else 10
    if is_pie:
        labels, values = compress_pie_data(labels, values, min(top_n, 5))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6))
    positions = list(range(len(labels)))

    if is_pie:
        total = sum(values)
        wedges, _, autotexts = ax.pie(
            values,
            startangle=90,
            counterclock=False,
            autopct=lambda pct: f"{pct:.1f}%" if pct >= 3 else "",
            pctdistance=0.72,
        )
        for autotext in autotexts:
            autotext.set_fontsize(9)
            autotext.set_color("white")
        legend_labels = [
            f"{label} | {format_chart_value(value)}"
            if total
            else f"{label} | 0"
            for label, value in zip(labels, values)
        ]
        ax.legend(
            wedges,
            legend_labels,
            title=ylabel,
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            frameon=False,
        )
        ax.axis("equal")
    elif chart.startswith("daily-"):
        ax.plot(positions, values, marker="o", linewidth=2, color="#1f77b4")
        ax.set_xticks(positions)
        ax.set_xticklabels(labels, rotation=30, ha="right")
        for x, y in zip(positions, values):
            ax.annotate(
                format_chart_value(y),
                (x, y),
                textcoords="offset points",
                xytext=(0, 6),
                ha="center",
                va="bottom",
                fontsize=9,
            )
    else:
        labels = list(reversed(labels))
        values = list(reversed(values))
        positions = list(range(len(labels)))
        ax.barh(positions, values, color="#1f77b4")
        ax.set_yticks(positions)
        ax.set_yticklabels(labels)
        for y, x in zip(positions, values):
            ax.annotate(
                format_chart_value(x),
                (x, y),
                textcoords="offset points",
                xytext=(4, 0),
                ha="left",
                va="center",
                fontsize=9,
            )

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    if is_pie:
        ax.set_ylabel("")
    elif chart.startswith("daily-"):
        if values:
            ax.set_ylim(top=max(values) * 1.12)
        ax.grid(axis="y", linestyle="--", alpha=0.3)
    else:
        if values:
            ax.set_xlim(right=max(values) * 1.15)
        ax.set_xlabel(ylabel)
        ax.set_ylabel("")
        ax.grid(axis="x", linestyle="--", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def summarize(data: Any) -> str:
    """將常見 LiteLLM aggregated activity 格式整理成可讀摘要。"""
    lines: list[str] = []

    if isinstance(data, (dict, list)):
        records = extract_records(data)
        if not records and isinstance(data, dict) and any(
            k for k in data if k not in ("message", "status")
        ):
            records = [data]
    else:
        return json.dumps(data, ensure_ascii=False, indent=2)

    if not records:
        return "查無資料（指定區間內沒有使用量紀錄）。"

    if not isinstance(records, list):
        records = [records]

    total_requests = 0.0
    total_spend = 0.0
    total_tokens = 0.0

    lines.append("## 使用量摘要")
    lines.append("")
    lines.append("| 日期 | 請求數 | Tokens | 花費 |")
    lines.append("| --- | ---: | ---: | ---: |")

    for row in records:
        if not isinstance(row, dict):
            continue

        raw_metrics = row.get("metrics")
        metrics: dict[str, Any] = raw_metrics if isinstance(raw_metrics, dict) else row

        day = (
            row.get("date")
            or row.get("day")
            or row.get("start_date")
            or row.get("period")
            or "-"
        )
        requests_count = as_number(
            pick_first(
                metrics,
                "requests",
                "num_requests",
                "total_requests",
                "request_count",
                "api_requests",
                "successful_requests",
            )
        )
        tokens_value = pick_first(metrics, "tokens", "total_tokens", "token_count")
        if tokens_value is None:
            tokens_value = as_number(pick_first(metrics, "prompt_tokens")) + as_number(
                pick_first(metrics, "completion_tokens")
            )
        tokens = as_number(tokens_value)
        spend = as_number(
            pick_first(metrics, "spend", "cost", "total_spend", "total_cost")
        )

        total_requests += requests_count
        total_tokens += tokens
        total_spend += spend

        lines.append(
            f"| {day} | {requests_count:,.0f} | {tokens:,.0f} | {spend:,.4f} |"
        )

    lines.append("")
    lines.append(
        f"**合計**：請求 {total_requests:,.0f} 次，"
        f"Tokens {total_tokens:,.0f}，花費 {total_spend:,.4f}"
    )

    user_ranking = data.get("user_ranking") if isinstance(data, dict) else None
    if isinstance(user_ranking, list) and user_ranking:
        top_n = 10
        if isinstance(data, dict):
            top_any = data.get("top")
            if isinstance(top_any, int) and top_any > 0:
                top_n = top_any
        lines.append("")
        rank_label = "花費"
        if isinstance(data, dict):
            rank_by_any = data.get("user_rank_by")
            rank_by = rank_by_any if isinstance(rank_by_any, str) else "spend"
            rank_label = {
                "spend": "花費",
                "tokens": "Tokens",
                "requests": "請求數",
            }.get(rank_by, "花費")
        lines.append(f"## 使用者排行（依 {rank_label} 排序）")
        lines.append("")
        lines.append("| user_email | user_id | 成功 | 失敗 | 請求數 | Tokens | 花費 | Keys |")
        lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for row in user_ranking[:top_n]:
            if not isinstance(row, dict):
                continue
            metrics_any = row.get("metrics")
            metrics: dict[str, Any] = metrics_any if isinstance(metrics_any, dict) else {}
            lines.append(
                f"| {row.get('user_email') or '-'} | "
                f"{row.get('user_id') or '-'} | "
                f"{as_number(metrics.get('successful_requests')):,.0f} | "
                f"{as_number(metrics.get('failed_requests')):,.0f} | "
                f"{as_number(metrics.get('api_requests')):,.0f} | "
                f"{as_number(metrics.get('total_tokens')):,.0f} | "
                f"{as_number(metrics.get('spend')):,.4f} | "
                f"{as_number(row.get('key_count')):,.0f} |"
            )

    model_ranking = data.get("model_ranking") if isinstance(data, dict) else None
    if isinstance(model_ranking, list) and model_ranking:
        top_n = 10
        if isinstance(data, dict):
            top_any = data.get("top")
            if isinstance(top_any, int) and top_any > 0:
                top_n = top_any
        lines.append("")
        model_rank_label = "花費"
        if isinstance(data, dict):
            model_rank_by_any = data.get("model_rank_by")
            model_rank_by = model_rank_by_any if isinstance(model_rank_by_any, str) else "spend"
            model_rank_label = {
                "spend": "花費",
                "tokens": "Tokens",
                "requests": "請求數",
            }.get(model_rank_by, "花費")
        lines.append(f"## Top Public Model Names（依 {model_rank_label} 排序）")
        lines.append("")
        lines.append("| public_model_name | 成功 | 失敗 | 請求數 | Tokens | 花費 |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for row in model_ranking[:top_n]:
            if not isinstance(row, dict):
                continue
            metrics_any = row.get("metrics")
            metrics: dict[str, Any] = metrics_any if isinstance(metrics_any, dict) else {}
            lines.append(
                f"| {row.get('public_model_name') or '-'} | "
                f"{as_number(metrics.get('successful_requests')):,.0f} | "
                f"{as_number(metrics.get('failed_requests')):,.0f} | "
                f"{as_number(metrics.get('api_requests')):,.0f} | "
                f"{as_number(metrics.get('total_tokens')):,.0f} | "
                f"{as_number(metrics.get('spend')):,.4f} |"
            )

    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    env_path = (
        Path(args.env_file)
        if args.env_file
        else Path(__file__).resolve().parent.parent / ".env"
    )
    load_dotenv(env_path)

    api_key = args.api_key or os.environ.get("LITELLM_API_KEY")
    if not api_key:
        raise SystemExit(
            "缺少 API Key。請設定環境變數 LITELLM_API_KEY，"
            "或在專案根目錄建立 .env 檔。"
        )

    start_date = validate_date(args.start_date, "start_date")
    end_date = validate_date(args.end_date, "end_date")

    data = fetch_usage_split_by_day(
        base_url=args.base_url,
        api_key=api_key,
        start_date=start_date,
        end_date=end_date,
        timezone=args.timezone,
    )
    data["top"] = args.top
    data["date_range"] = f"{start_date} to {end_date}"
    data["timezone_label"] = format_timezone_label(args.timezone)

    if args.include_key_map:
        data["key_map"] = fetch_key_map(args.base_url, api_key)
        data["user_rank_by"] = args.user_rank_by
        data["user_ranking"] = build_user_ranking(
            data, data["key_map"], args.user_rank_by
        )

    if args.include_model_ranking:
        data["model_rank_by"] = args.model_rank_by
        data["model_ranking"] = build_model_ranking(data, args.model_rank_by)

    chart_path: Path | None = None
    if args.chart:
        chart_output = (
            Path(args.chart_output)
            if args.chart_output
            else default_chart_output(args.chart, start_date, end_date, args.timezone)
        )
        chart_path = render_chart(data, args.chart, chart_output)
        data["chart"] = {"type": args.chart, "output": str(chart_path)}

    if args.raw:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(summarize(data))
        if chart_path is not None:
            print("")
            print(f"圖表已輸出：{chart_path}")


if __name__ == "__main__":
    main()
