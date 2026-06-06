"""File-based storage and config management."""
from __future__ import annotations
import json
import os
import dataclasses
import datetime
from pathlib import Path
from typing import Optional, Any

from dotenv import load_dotenv

from instagram_manager.models import (
    ContentPlan, ContentItem, ContentFormat, PlanStatus, ItemStatus,
    HashtagSet, PostInsights,
)

# Load .env at import time
load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_DIR = Path(".instagram")
MEMORY_DIR = BASE_DIR / "memory"
PLANS_DIR = MEMORY_DIR / "plans"
ASSETS_DIR = MEMORY_DIR / "assets"
INSIGHTS_DIR = MEMORY_DIR / "insights"
LOGS_DIR = MEMORY_DIR / "logs"
MEDIA_DIR = BASE_DIR / "media"
MEDIA_INDEX_PATH = MEMORY_DIR / "media-index.json"


def _load_yaml_config() -> dict:
    """Load .instagram/config.yml; return empty dict if missing."""
    config_path = BASE_DIR / "config.yml"
    if not config_path.exists():
        return {}
    try:
        import yaml  # type: ignore
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        # yaml not installed — parse minimal subset manually
        result: dict = {}
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if ":" in line and not line.startswith("#"):
                    k, _, v = line.partition(":")
                    result[k.strip()] = v.strip()
        return result


class Config:
    """Typed config object combining config.yml + env vars."""

    def __init__(self):
        self._cfg = _load_yaml_config()
        self.meta_access_token: str = os.getenv("META_ACCESS_TOKEN", "")
        self.meta_ig_user_id: str = os.getenv("META_IG_USER_ID", "")
        self.anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
        self.image_provider: str = os.getenv("IMAGE_PROVIDER", "huggingface")
        self.hf_api_token: str = os.getenv("HF_API_TOKEN", "")
        self.replicate_api_token: str = os.getenv("REPLICATE_API_TOKEN", "")

        ip = self._cfg.get("image_provider", {})
        if isinstance(ip, dict):
            self.image_provider_type: str = ip.get("type", self.image_provider)
            self.image_provider_model: str = ip.get(
                "model", "stabilityai/stable-diffusion-xl-base-1.0"
            )
        else:
            self.image_provider_type = self.image_provider
            self.image_provider_model = "stabilityai/stable-diffusion-xl-base-1.0"

        sa = self._cfg.get("style_analysis", {})
        if isinstance(sa, dict):
            self.style_analysis_max_photos: int = int(sa.get("max_photos", 10))
            self.style_analysis_auto_update: bool = bool(sa.get("auto_update", True))
        else:
            self.style_analysis_max_photos = 10
            self.style_analysis_auto_update = True

    def validate_required(self) -> list[str]:
        """Return list of missing required env vars."""
        missing = []
        for var in ("META_ACCESS_TOKEN", "META_IG_USER_ID", "ANTHROPIC_API_KEY"):
            if not os.getenv(var):
                missing.append(var)
        return missing


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> None:
    """Reset cached config (useful in tests)."""
    global _config
    _config = None


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _item_to_dict(item: ContentItem) -> dict:
    d = dataclasses.asdict(item)
    d["format"] = item.format.value
    d["status"] = item.status.value
    if item.hashtags:
        d["hashtags"] = {
            "broad": item.hashtags.broad,
            "niche": item.hashtags.niche,
            "branded": item.hashtags.branded,
        }
    return d


def _item_from_dict(d: dict) -> ContentItem:
    hashtags_raw = d.pop("hashtags", {})
    hashtags = HashtagSet(
        broad=hashtags_raw.get("broad", []),
        niche=hashtags_raw.get("niche", []),
        branded=hashtags_raw.get("branded", []),
    )
    format_ = ContentFormat(d.pop("format"))
    status = ItemStatus(d.pop("status", "pending"))
    return ContentItem(
        format=format_,
        status=status,
        hashtags=hashtags,
        **d,
    )


def _plan_to_dict(plan: ContentPlan) -> dict:
    d = dataclasses.asdict(plan)
    d["status"] = plan.status.value
    d["items"] = [_item_to_dict(item) for item in plan.items]
    return d


def _plan_from_dict(d: dict) -> ContentPlan:
    status = PlanStatus(d.pop("status", "draft"))
    items_raw = d.pop("items", [])
    items = [_item_from_dict(i) for i in items_raw]
    return ContentPlan(status=status, items=items, **d)


# ---------------------------------------------------------------------------
# Plan CRUD
# ---------------------------------------------------------------------------

class PlanNotFound(Exception):
    pass


class AlreadyApproved(Exception):
    pass


def save_plan(plan: ContentPlan) -> None:
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = PLANS_DIR / f"{plan.week}.json"
    tmp_path = json_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(_plan_to_dict(plan), f, indent=2, ensure_ascii=False)
    tmp_path.rename(json_path)
    # Also write human-readable .md
    _write_plan_md(plan)


def load_plan(week: str) -> ContentPlan:
    json_path = PLANS_DIR / f"{week}.json"
    if not json_path.exists():
        raise PlanNotFound(f"Plan {week} not found at {json_path}")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    return _plan_from_dict(data)


def _write_plan_md(plan: ContentPlan) -> None:
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = PLANS_DIR / f"{plan.week}.md"
    lines = [
        f"# Content Plan: Week {plan.week}",
        f"**Status**: {plan.status.value} | **Created**: {plan.created_at}",
        "",
    ]
    for item in plan.items:
        tags = " ".join(item.hashtags.all_tags())
        lines += [
            f"## {item.id} — {item.day} at {item.intended_time}",
            f"**Format**: {item.format.value} | **Status**: {item.status.value}",
            f"**Theme**: {item.theme}",
            f"**Copy**: {item.copy_draft}",
            f"**Hashtags**: {tags}",
            "",
        ]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def update_item_status(week: str, item_id: str, status: ItemStatus, **kwargs) -> None:
    plan = load_plan(week)
    for item in plan.items:
        if item.id == item_id:
            item.status = status
            for k, v in kwargs.items():
                setattr(item, k, v)
            break
    else:
        raise PlanNotFound(f"Item {item_id} not found in plan {week}")
    save_plan(plan)


def approve_plan(week: str) -> ContentPlan:
    plan = load_plan(week)
    if plan.status != PlanStatus.DRAFT:
        raise AlreadyApproved(f"Plan {week} is already in status '{plan.status.value}'")
    plan.status = PlanStatus.APPROVED
    plan.approved_at = datetime.datetime.utcnow().isoformat() + "Z"
    save_plan(plan)
    return plan


# ---------------------------------------------------------------------------
# Media index CRUD
# ---------------------------------------------------------------------------

def save_media_index(index: dict) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    tmp = MEDIA_INDEX_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    tmp.rename(MEDIA_INDEX_PATH)


def load_media_index() -> dict:
    if not MEDIA_INDEX_PATH.exists():
        return {"last_updated": datetime.datetime.utcnow().isoformat() + "Z", "files": []}
    with open(MEDIA_INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Insights CRUD
# ---------------------------------------------------------------------------

def save_insights(week: str, data: dict) -> None:
    INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    path = INSIGHTS_DIR / f"{week}.json"
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.rename(path)


def load_insights(week: str) -> Optional[dict]:
    path = INSIGHTS_DIR / f"{week}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Asset storage helpers
# ---------------------------------------------------------------------------

def save_asset(item_id: str, week: str, filename: str, data: bytes) -> Path:
    """Save a binary asset file and return its path."""
    asset_dir = ASSETS_DIR / week / item_id
    asset_dir.mkdir(parents=True, exist_ok=True)
    path = asset_dir / filename
    path.write_bytes(data)
    return path


def write_manifest(item_id: str, week: str, manifest: dict) -> Path:
    """Write manifest.json for an asset directory."""
    asset_dir = ASSETS_DIR / week / item_id
    asset_dir.mkdir(parents=True, exist_ok=True)
    path = asset_dir / "manifest.json"
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    tmp.rename(path)
    return path


def load_manifest(item_id: str, week: str) -> Optional[dict]:
    """Load manifest.json for an asset directory. Returns None if missing."""
    path = ASSETS_DIR / week / item_id / "manifest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
