"""Meta Insights API client and aggregation."""
from __future__ import annotations
import datetime
from typing import Optional
from collections import defaultdict

from instagram_manager import meta_client, logger
from instagram_manager.storage import (
    load_plan, save_insights, load_insights, INSIGHTS_DIR, load_manifest,
)


# ---------------------------------------------------------------------------
# T058 — Insights fetching
# ---------------------------------------------------------------------------

def fetch_insights(media_id: str) -> dict:
    """Fetch insights for a single published post.

    Returns dict with metrics or {data_available: False} if data not ready.
    Handles 48h latency — posts published < 48h ago may not have data.
    """
    return meta_client.get_post_insights(media_id)


# ---------------------------------------------------------------------------
# T059 — Insights aggregation
# ---------------------------------------------------------------------------

def compute_summary(posts: list[dict]) -> dict:
    """Compute aggregated insights summary across multiple posts.

    Returns dict with:
      best_format, best_time_slot, best_asset_source,
      avg_engagement_rate, top_item_id
    """
    available = [p for p in posts if p.get("data_available", True)]
    if not available:
        return {
            "best_format": None,
            "best_time_slot": None,
            "best_asset_source": None,
            "avg_engagement_rate": 0.0,
            "top_item_id": None,
        }

    # Avg engagement rate
    rates = [p["metrics"].get("engagement_rate", 0.0) for p in available]
    avg_rate = sum(rates) / len(rates) if rates else 0.0

    # Top performer
    top = max(available, key=lambda p: p["metrics"].get("engagement_rate", 0.0))

    # Best format
    format_rates: dict = defaultdict(list)
    for p in available:
        fmt = p.get("format", "unknown")
        rate = p["metrics"].get("engagement_rate", 0.0)
        format_rates[fmt].append(rate)
    best_format = max(
        format_rates,
        key=lambda f: sum(format_rates[f]) / len(format_rates[f]) if format_rates[f] else 0
    ) if format_rates else None

    # Best time slot (from published_at field, or intended_time)
    # Group by hour
    hour_rates: dict = defaultdict(list)
    for p in available:
        pub = p.get("published_at", "")
        if "T" in pub:
            hour = pub.split("T")[1][:5]  # HH:MM
        else:
            hour = "09:00"
        hour_rates[hour].append(p["metrics"].get("engagement_rate", 0.0))
    best_time = max(
        hour_rates,
        key=lambda h: sum(hour_rates[h]) / len(hour_rates[h]) if hour_rates[h] else 0
    ) if hour_rates else None

    # Best asset source
    source_rates: dict = defaultdict(list)
    for p in available:
        source = p.get("asset_source", "ai-generated")
        rate = p["metrics"].get("engagement_rate", 0.0)
        source_rates[source].append(rate)
    best_source = max(
        source_rates,
        key=lambda s: sum(source_rates[s]) / len(source_rates[s]) if source_rates[s] else 0
    ) if source_rates else None

    return {
        "best_format": best_format,
        "best_time_slot": best_time,
        "best_asset_source": best_source,
        "avg_engagement_rate": round(avg_rate, 4),
        "top_item_id": top["item_id"],
    }


# ---------------------------------------------------------------------------
# T060 — Insights storage and top-performer tagging
# ---------------------------------------------------------------------------

def save_week_insights(week: str, posts: list[dict]) -> dict:
    """Compute summary, tag top performer, and save insights JSON.

    Returns the saved insights dict.
    """
    if posts:
        # Compute engagement_rate for posts that have raw metrics
        for p in posts:
            metrics = p.get("metrics", {})
            reach = metrics.get("reach", 0)
            if reach > 0:
                interactions = (
                    metrics.get("likes", 0)
                    + metrics.get("comments", 0)
                    + metrics.get("shares", 0)
                    + metrics.get("saved", 0)
                )
                metrics["engagement_rate"] = round(interactions / reach, 4)
            else:
                metrics["engagement_rate"] = 0.0
            p["metrics"] = metrics

        summary = compute_summary(posts)

        # Tag top performer
        top_id = summary.get("top_item_id")
        for p in posts:
            p["top_performer"] = p["item_id"] == top_id

    else:
        summary = {
            "best_format": None,
            "best_time_slot": None,
            "best_asset_source": None,
            "avg_engagement_rate": 0.0,
            "top_item_id": None,
        }

    data = {
        "week": week,
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
        "posts": posts,
        "summary": summary,
    }
    save_insights(week, data)
    return data


def fetch_week_insights(week: str) -> dict:
    """Fetch insights for all published posts in a week and save.

    Returns summary dict.
    """
    plan = load_plan(week)
    posts = []

    for item in plan.items:
        if not item.meta_post_id:
            continue  # Not published yet

        raw = fetch_insights(item.meta_post_id)
        data_available = raw.get("data_available", True)

        # Get asset_source from manifest
        manifest = load_manifest(item.id, week)
        asset_source = "ai-generated"
        if manifest and manifest.get("images"):
            asset_source = manifest["images"][0].get("asset_source", "ai-generated")

        post_data = {
            "item_id": item.id,
            "meta_post_id": item.meta_post_id,
            "format": item.format.value,
            "asset_source": asset_source,
            "published_at": datetime.datetime.utcnow().isoformat() + "Z",
            "data_available": data_available,
            "top_performer": False,
            "metrics": {
                "reach": raw.get("reach", 0),
                "impressions": raw.get("impressions", 0),
                "likes": raw.get("likes", 0),
                "comments": raw.get("comments", 0),
                "shares": raw.get("shares", 0),
                "saved": raw.get("saved", 0),
                "engagement_rate": 0.0,
            },
        }
        posts.append(post_data)

    result = save_week_insights(week, posts)
    logger.append_event(
        skill="instagram-insights",
        item_id=None,
        plan_week=week,
        event_type="insights_fetched",
        outcome="success",
        post_count=len(posts),
    )
    return result
