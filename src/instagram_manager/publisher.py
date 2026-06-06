"""Instagram publishing orchestrator using Meta Graph API."""
from __future__ import annotations
import datetime
import os
import time
import json
from pathlib import Path
from typing import Optional

from instagram_manager.models import ContentItem, ContentFormat, ItemStatus
from instagram_manager.storage import (
    load_plan, update_item_status, load_manifest, ASSETS_DIR, MEMORY_DIR,
)
from instagram_manager import logger, meta_client


# ---------------------------------------------------------------------------
# Token management (T049)
# ---------------------------------------------------------------------------

TOKEN_META_PATH = MEMORY_DIR / ".token-meta"


class TokenExpiredError(Exception):
    pass


def check_token_expiry() -> Optional[str]:
    """Check META_ACCESS_TOKEN expiry.

    Returns a warning string if token expires < 7 days, None if OK.
    Raises TokenExpiredError if token is already expired.

    Reads from cached .token-meta file to avoid API calls on every publish.
    """
    import time as _time

    # Try cached file first
    if TOKEN_META_PATH.exists():
        try:
            cached = json.loads(TOKEN_META_PATH.read_text())
            expires_at = cached.get("expires_at")
            if expires_at:
                now = _time.time()
                remaining = expires_at - now
                if remaining <= 0:
                    raise TokenExpiredError(
                        "META_ACCESS_TOKEN has expired. Generate a new token and update .env.\n"
                        "  → Go to: https://developers.facebook.com/tools/explorer/"
                    )
                days_left = remaining / 86400
                if days_left < 7:
                    return f"⚠  META_ACCESS_TOKEN expires in {days_left:.0f} days. Renew before it expires."
                return None
        except (json.JSONDecodeError, KeyError):
            pass

    # No cache — skip API call and proceed (init writes the cache)
    return None


def cache_token_expiry(expires_at: int) -> None:
    """Cache token expiry timestamp to avoid repeated API calls."""
    TOKEN_META_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_META_PATH.write_text(json.dumps({"expires_at": expires_at}))


# ---------------------------------------------------------------------------
# Image upload helpers (T048 + T048b)
# ---------------------------------------------------------------------------

def _read_caption(item_id: str, week: str) -> str:
    """Read caption.txt for a ContentItem."""
    caption_path = ASSETS_DIR / week / item_id / "caption.txt"
    if caption_path.exists():
        return caption_path.read_text(encoding="utf-8").strip()
    return ""


def _upload_image_to_meta(image_path: Path, caption: str, media_type: str = "IMAGE") -> str:
    """Create an image media container on Meta.

    Because Meta requires a publicly accessible URL and we store images locally,
    this implementation uses the image file path. In production, the operator should
    configure a CDN or use Meta's upload session endpoint.

    For the current implementation: we attempt to use a file:// URL which only works
    in development/testing. Real deployments require a public URL.

    Returns container ID.
    """
    # For real deployments, this would be a publicly accessible URL.
    # We store the local path and note it in the manifest.
    # In tests this is mocked entirely.
    image_url = f"file://{image_path.resolve()}"
    return meta_client.create_media_container(
        media_type=media_type,
        image_url=image_url,
        caption=caption,
    )


def _upload_carousel_slide(image_path: Path) -> str:
    """Create a child container for a carousel slide. Returns child container ID."""
    image_url = f"file://{image_path.resolve()}"
    return meta_client.create_media_container(
        media_type="IMAGE",
        image_url=image_url,
    )


# ---------------------------------------------------------------------------
# Publishing orchestrator (T050)
# ---------------------------------------------------------------------------

def publish_item(item: ContentItem, week: str) -> dict:
    """Publish a single ContentItem to Instagram.

    Returns dict with: success (bool), meta_post_id (str or None), error (str or None)
    """
    # Check token
    token_warning = check_token_expiry()
    result = {"success": False, "meta_post_id": None, "error": None, "token_warning": token_warning}

    # Validate assets exist
    manifest = load_manifest(item.id, week)
    if not manifest and item.format != ContentFormat.REEL:
        result["error"] = f"No assets found for {item.id}. Run /instagram-generate first."
        update_item_status(week, item.id, ItemStatus.BLOCKED)
        return result

    caption = _read_caption(item.id, week)
    asset_dir = ASSETS_DIR / week / item.id

    update_item_status(week, item.id, ItemStatus.PUBLISHING)
    logger.append_event(
        skill="instagram-publish",
        item_id=item.id,
        plan_week=week,
        event_type="publishing",
        outcome="started",
        format=item.format.value,
    )

    try:
        if item.format == ContentFormat.REEL:
            # Reels require creator video
            from instagram_manager.media import get_media_for_slot
            video_media = get_media_for_slot(item.id)
            if not video_media or video_media.get("type") != "video":
                result["error"] = (
                    f"Reels require a creator-provided video. "
                    f"Assign a video file with: /instagram-media assign <media-id> --slot {item.id}"
                )
                update_item_status(week, item.id, ItemStatus.BLOCKED)
                return result

            video_path = Path(video_media["path"])
            if not video_path.exists():
                result["error"] = f"Video file not found: {video_media['path']}"
                update_item_status(week, item.id, ItemStatus.BLOCKED)
                return result

            container_id = meta_client.create_media_container(
                media_type="REELS",
                video_url=f"file://{video_path.resolve()}",
                caption=caption,
            )

        elif item.format == ContentFormat.CAROUSEL:
            # Upload each slide as a child container
            slide_images = sorted(asset_dir.glob("image_*.jpg"))
            if not slide_images:
                result["error"] = f"No slide images found in {asset_dir}"
                update_item_status(week, item.id, ItemStatus.BLOCKED)
                return result

            child_ids = []
            for slide_path in slide_images:
                child_id = _upload_carousel_slide(slide_path)
                child_ids.append(child_id)

            container_id = meta_client.create_media_container(
                media_type="CAROUSEL_ALBUM",
                caption=caption,
                children=child_ids,
            )

        else:
            # Feed or Story — single image
            images = manifest.get("images", []) if manifest else []
            if not images:
                result["error"] = f"No images found in manifest for {item.id}"
                update_item_status(week, item.id, ItemStatus.BLOCKED)
                return result

            img_filename = images[0]["filename"]
            img_path = asset_dir / img_filename
            if not img_path.exists():
                result["error"] = f"Image file not found: {img_path}"
                update_item_status(week, item.id, ItemStatus.BLOCKED)
                return result

            media_type = "STORIES" if item.format == ContentFormat.STORY else "IMAGE"
            container_id = _upload_image_to_meta(img_path, caption, media_type)

        # Publish the container
        post_id = meta_client.publish_container(container_id)

        update_item_status(week, item.id, ItemStatus.PUBLISHED, meta_post_id=post_id)
        logger.append_event(
            skill="instagram-publish",
            item_id=item.id,
            plan_week=week,
            event_type="published",
            outcome="success",
            meta_post_id=post_id,
            format=item.format.value,
            intended_time=item.intended_time,
        )
        result["success"] = True
        result["meta_post_id"] = post_id
        return result

    except meta_client.AuthError as e:
        error_msg = f"Authentication error: {e}"
        result["error"] = error_msg
        update_item_status(week, item.id, ItemStatus.FAILED)
        logger.append_event(
            skill="instagram-publish",
            item_id=item.id,
            plan_week=week,
            event_type="publish_failed",
            outcome="failure",
            error=error_msg,
        )
        raise  # Auth errors propagate — halt all publishing

    except meta_client.MetaAPIError as e:
        error_msg = str(e)
        result["error"] = error_msg
        update_item_status(week, item.id, ItemStatus.FAILED)
        logger.append_event(
            skill="instagram-publish",
            item_id=item.id,
            plan_week=week,
            event_type="publish_failed",
            outcome="failure",
            error=error_msg,
            retry_count=0,
        )
        return result


def publish_plan(
    week: str,
    item_id: Optional[str] = None,
    publish_all: bool = False,
) -> dict:
    """Publish all generated items in a plan (or a single item).

    Returns summary: {succeeded, failed, blocked, skipped}
    """
    plan = load_plan(week)
    items = plan.items

    if item_id:
        items = [i for i in items if i.id == item_id]

    # Show token warning once at the top
    token_warning = check_token_expiry()

    succeeded = failed = blocked = skipped = 0
    results = []

    for item in items:
        if item.status != ItemStatus.GENERATED:
            skipped += 1
            results.append({"item_id": item.id, "skipped": True, "reason": item.status.value})
            continue

        try:
            res = publish_item(item, week)
            if res["success"]:
                succeeded += 1
            elif res.get("error") and "BLOCKED" in res.get("error", "").upper() or item.status == ItemStatus.BLOCKED:
                blocked += 1
            else:
                failed += 1
            results.append(res)
        except meta_client.AuthError:
            # Auth error halts everything
            failed += len(items) - succeeded - failed - blocked - skipped
            break

    return {
        "week": week,
        "token_warning": token_warning,
        "succeeded": succeeded,
        "failed": failed,
        "blocked": blocked,
        "skipped": skipped,
        "results": results,
    }
