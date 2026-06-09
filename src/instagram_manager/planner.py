"""Weekly content plan generator using Claude API."""
from __future__ import annotations
import datetime
import json
import re
from typing import Optional

import anthropic

from instagram_manager.brand import load_brand, BrandNotFound
from instagram_manager.models import (
    ContentPlan, ContentItem, ContentFormat, ItemStatus, HashtagSet,
)
from instagram_manager.storage import save_plan, load_insights, PLANS_DIR
from instagram_manager import logger


def _week_dates(week: str) -> tuple[str, str]:
    """Return (week_start, week_end) as YYYY-MM-DD for an ISO week string YYYY-WW."""
    year, wnum = week.split("-")
    # ISO week: Monday=1
    d = datetime.date.fromisocalendar(int(year), int(wnum), 1)
    return str(d), str(d + datetime.timedelta(days=6))


def _current_week() -> str:
    """Return current ISO week as YYYY-WW."""
    today = datetime.date.today()
    iso = today.isocalendar()
    return f"{iso[0]}-{iso[1]:02d}"


def _load_insights_summary(week: str) -> str:
    """Load previous week insights and return a summary string for Claude."""
    year, wnum = week.split("-")
    prev_wnum = int(wnum) - 1
    prev_year = int(year)
    if prev_wnum == 0:
        prev_wnum = 52
        prev_year -= 1
    prev_week = f"{prev_year}-{prev_wnum:02d}"
    data = load_insights(prev_week)
    if not data:
        return "No insights available yet (first week). Use brand profile defaults for recommendations."

    summary = data.get("summary", {})
    posts = data.get("posts", [])
    top = next((p for p in posts if p.get("top_performer")), None)

    lines = [
        f"## Previous Week Performance ({prev_week})",
        f"",
        f"**Best performing format**: {summary.get('best_format', 'unknown')}",
        f"**Best time slot**: {summary.get('best_time_slot', 'unknown')}",
        f"**Best asset source**: {summary.get('best_asset_source', 'unknown')} (creator vs AI-generated)",
        f"**Average engagement rate**: {summary.get('avg_engagement_rate', 0):.1%}",
    ]
    if top:
        metrics = top.get("metrics", {})
        lines += [
            f"",
            f"**Top post**: {top['item_id']} ({top.get('format', 'unknown')} format)",
            f"  - Reach: {metrics.get('reach', 0):,}",
            f"  - Engagement: {metrics.get('engagement_rate', 0):.1%}",
        ]
    lines += [
        f"",
        f"**Recommendation**: Favour {summary.get('best_format', 'varied')} format and "
        f"{summary.get('best_time_slot', 'morning')} publishing time next week.",
    ]
    return "\n".join(lines)


def _read_prompt_template() -> str:
    from pathlib import Path
    p = Path(".instagram/templates/prompts/plan-week.md")
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def _build_prompt(
    week: str,
    week_start: str,
    week_end: str,
    brand_text: str,
    insights_summary: str,
    theme: Optional[str],
) -> str:
    template = _read_prompt_template()
    if template:
        return (
            template
            .replace("{brand_profile}", brand_text)
            .replace("{insights_summary}", insights_summary)
            .replace("{week}", week)
            .replace("{week_start}", week_start)
            .replace("{week_end}", week_end)
            .replace("{theme_override}", theme or "none")
        )
    # Fallback inline prompt
    return f"""Generate a 7-day Instagram content calendar as a JSON array.

Brand profile:
{brand_text}

Week: {week} ({week_start} to {week_end})
Theme override: {theme or "none"}
Previous insights: {insights_summary}

Output a JSON array of 7 ContentItem objects with fields:
id (YYYY-WW-NNN), day (YYYY-MM-DD), intended_time (HH:MM), format (feed/carousel/reel/story),
theme, copy_draft, hashtags (broad/niche/branded arrays, total ≤30), slide_count (2-10 for carousel, null otherwise), audio_ref (null), status ("pending").
Use all 4 formats. Output ONLY the JSON array."""


def _parse_items(raw: str, week: str, week_start: str) -> list[ContentItem]:
    """Extract JSON array from Claude's response and parse into ContentItem list."""
    # Strip markdown code fences if present
    clean = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    # Find first [ ... ] block
    start = clean.find("[")
    end = clean.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON array found in response: {raw[:200]}")
    data = json.loads(clean[start:end])

    items = []
    for i, d in enumerate(data, 1):
        fmt = ContentFormat(d.get("format", "feed"))
        status = ItemStatus(d.get("status", "pending"))
        hashtags_raw = d.get("hashtags", {})
        hashtags = HashtagSet(
            broad=hashtags_raw.get("broad", []),
            niche=hashtags_raw.get("niche", []),
            branded=hashtags_raw.get("branded", []),
        )
        # Auto-assign id if missing
        item_id = d.get("id") or f"{week}-{i:03d}"
        item = ContentItem(
            id=item_id,
            day=d.get("day", week_start),
            intended_time=d.get("intended_time", "09:00"),
            format=fmt,
            theme=d.get("theme", ""),
            copy_draft=d.get("copy_draft", ""),
            hashtags=hashtags,
            slide_count=d.get("slide_count"),
            audio_ref=d.get("audio_ref"),
            status=status,
        )
        items.append(item)
    return items


class HashtagLimitError(Exception):
    """Raised when hashtag generation response exceeds 30-tag limit."""
    pass


def generate_hashtags(theme: str, format: str, brand_text: str) -> HashtagSet:
    """Generate a HashtagSet for a ContentItem using Claude API.

    Args:
        theme: The post theme/topic
        format: The content format (feed, carousel, reel, story)
        brand_text: The brand profile markdown text

    Returns:
        HashtagSet with broad, niche, and branded tiers (total ≤ 30)

    Raises:
        HashtagLimitError if response exceeds 30 tags
    """
    from pathlib import Path as PathlibPath
    import re as _re

    prompt_path = PathlibPath(".instagram/templates/prompts/generate-hashtags.md")
    if prompt_path.exists():
        prompt = (
            prompt_path.read_text(encoding="utf-8")
            .replace("{brand_profile}", brand_text)
            .replace("{theme}", theme)
            .replace("{format}", format)
        )
    else:
        prompt = (
            f"Generate Instagram hashtags for theme: {theme}, format: {format}.\n"
            f"Brand: {brand_text[:300]}\n"
            "Output JSON: {\"broad\": [...], \"niche\": [...], \"branded\": [...]}\n"
            "Total count must not exceed 30."
        )

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text

    # Parse JSON response
    clean = _re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    start = clean.find("{")
    end = clean.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object in hashtag response: {raw[:200]}")
    data = json.loads(clean[start:end])

    hashtag_set = HashtagSet(
        broad=data.get("broad", []),
        niche=data.get("niche", []),
        branded=data.get("branded", []),
    )
    return hashtag_set


def generate_plan(week: Optional[str] = None, theme: Optional[str] = None) -> ContentPlan:
    """Generate a 7-day content plan and save it.

    Args:
        week: ISO week string YYYY-WW. Defaults to current week.
        theme: Optional theme override for the week.

    Returns:
        The generated ContentPlan (saved to disk).
    """
    if not week:
        week = _current_week()

    week_start, week_end = _week_dates(week)

    # Load brand profile
    brand = load_brand()
    from pathlib import Path
    brand_path = Path(".instagram/memory/brand.md")
    brand_text = brand_path.read_text(encoding="utf-8") if brand_path.exists() else str(brand)

    # Load insights
    insights_summary = _load_insights_summary(week)

    # Build prompt
    prompt = _build_prompt(week, week_start, week_end, brand_text, insights_summary, theme)

    # Call Claude API
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text

    # Parse response
    items = _parse_items(raw, week, week_start)

    # Enrich each item with generated hashtags if they are empty/minimal
    for item in items:
        try:
            if item.hashtags.total < 5:
                item.hashtags = generate_hashtags(item.theme, item.format.value, brand_text)
        except Exception:
            pass  # Hashtag generation failure is non-fatal; keep whatever was returned

    plan = ContentPlan(
        week=week,
        week_start=week_start,
        week_end=week_end,
        items=items,
    )
    save_plan(plan)

    logger.append_event(
        skill="instagram-plan",
        item_id=None,
        plan_week=week,
        event_type="planned",
        outcome="success",
        item_count=len(items),
    )

    return plan
