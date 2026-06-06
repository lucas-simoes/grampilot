"""Unit tests for publisher.py."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from instagram_manager.models import (
    ContentItem, ContentFormat, ItemStatus, HashtagSet, ContentPlan, PlanStatus,
)
from instagram_manager import storage, publisher as pub_module
from instagram_manager.publisher import (
    check_token_expiry, TokenExpiredError, publish_item, publish_plan,
)
from instagram_manager.storage import reset_config, save_plan


def _make_item(fmt=ContentFormat.FEED, status=ItemStatus.GENERATED) -> ContentItem:
    return ContentItem(
        id="2026-23-001",
        day="2026-06-01",
        intended_time="09:00",
        format=fmt,
        theme="test",
        copy_draft="test copy",
        hashtags=HashtagSet(broad=["#test"], niche=[], branded=[]),
        status=status,
    )


def _make_plan(items=None, week="2026-23") -> ContentPlan:
    return ContentPlan(
        week=week,
        week_start="2026-06-01",
        week_end="2026-06-07",
        status=PlanStatus.APPROVED,
        items=items or [_make_item()],
    )


@pytest.fixture(autouse=True)
def tmp_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reset_config()
    storage.PLANS_DIR = tmp_path / ".instagram" / "memory" / "plans"
    storage.MEMORY_DIR = tmp_path / ".instagram" / "memory"
    storage.ASSETS_DIR = tmp_path / ".instagram" / "memory" / "assets"
    storage.INSIGHTS_DIR = tmp_path / ".instagram" / "memory" / "insights"
    storage.MEDIA_INDEX_PATH = tmp_path / ".instagram" / "memory" / "media-index.json"
    pub_module.TOKEN_META_PATH = tmp_path / ".instagram" / "memory" / ".token-meta"
    pub_module.MEMORY_DIR = tmp_path / ".instagram" / "memory"
    yield
    from pathlib import Path as P
    storage.PLANS_DIR = P(".instagram/memory/plans")
    storage.MEMORY_DIR = P(".instagram/memory")
    storage.ASSETS_DIR = P(".instagram/memory/assets")
    storage.INSIGHTS_DIR = P(".instagram/memory/insights")
    storage.MEDIA_INDEX_PATH = P(".instagram/memory/media-index.json")
    pub_module.TOKEN_META_PATH = P(".instagram/memory/.token-meta")
    pub_module.MEMORY_DIR = P(".instagram/memory")
    reset_config()


def _make_asset_dir(item_id: str, week: str, tmp_path) -> Path:
    asset_dir = storage.ASSETS_DIR / week / item_id
    asset_dir.mkdir(parents=True, exist_ok=True)
    # Caption
    (asset_dir / "caption.txt").write_text("Test caption #test", encoding="utf-8")
    # Image
    try:
        from PIL import Image
        import io
        img = Image.new("RGB", (1080, 1080), color=(100, 200, 100))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        (asset_dir / "image_01.jpg").write_bytes(buf.getvalue())
    except ImportError:
        # Fallback: create minimal JPEG if PIL not available
        (asset_dir / "image_01.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100 + b"\xff\xd9")
    # Manifest
    manifest = {
        "item_id": item_id,
        "format": "feed",
        "generated_at": "2026-06-05T10:00:00Z",
        "images": [{"filename": "image_01.jpg", "asset_source": "ai-generated"}],
        "caption_file": "caption.txt",
        "script_file": None,
    }
    (asset_dir / "manifest.json").write_text(json.dumps(manifest))
    return asset_dir


class TestCheckTokenExpiry:
    def test_no_cache_returns_none(self, tmp_path):
        result = check_token_expiry()
        assert result is None

    def test_expired_raises(self, tmp_path):
        import time
        past = int(time.time()) - 3600
        pub_module.TOKEN_META_PATH.parent.mkdir(parents=True, exist_ok=True)
        pub_module.TOKEN_META_PATH.write_text(json.dumps({"expires_at": past}))
        with pytest.raises(TokenExpiredError):
            check_token_expiry()

    def test_near_expiry_returns_warning(self, tmp_path):
        import time
        soon = int(time.time()) + 3 * 86400  # 3 days
        pub_module.TOKEN_META_PATH.parent.mkdir(parents=True, exist_ok=True)
        pub_module.TOKEN_META_PATH.write_text(json.dumps({"expires_at": soon}))
        warning = check_token_expiry()
        assert warning is not None
        assert "expires in" in warning

    def test_ok_returns_none(self, tmp_path):
        import time
        future = int(time.time()) + 30 * 86400  # 30 days
        pub_module.TOKEN_META_PATH.parent.mkdir(parents=True, exist_ok=True)
        pub_module.TOKEN_META_PATH.write_text(json.dumps({"expires_at": future}))
        result = check_token_expiry()
        assert result is None


class TestPublishItem:
    def test_successful_feed_publish(self, tmp_path):
        plan = _make_plan()
        save_plan(plan)
        _make_asset_dir("2026-23-001", "2026-23", tmp_path)

        with (
            patch.object(pub_module, "check_token_expiry", return_value=None),
            patch("instagram_manager.meta_client.create_media_container", return_value="container-123"),
            patch("instagram_manager.meta_client.publish_container", return_value="post-456"),
        ):
            result = publish_item(plan.items[0], "2026-23")

        assert result["success"] is True
        assert result["meta_post_id"] == "post-456"
        loaded = storage.load_plan("2026-23")
        assert loaded.items[0].status == ItemStatus.PUBLISHED
        assert loaded.items[0].meta_post_id == "post-456"

    def test_reel_blocked_without_video(self, tmp_path):
        reel_item = _make_item(ContentFormat.REEL)
        plan = _make_plan(items=[reel_item])
        save_plan(plan)
        asset_dir = storage.ASSETS_DIR / "2026-23" / "2026-23-001"
        asset_dir.mkdir(parents=True, exist_ok=True)
        (asset_dir / "script.md").write_text("Script content")
        (asset_dir / "caption.txt").write_text("Caption")
        manifest = {"item_id": "2026-23-001", "format": "reel", "images": [], "script_file": "script.md"}
        (asset_dir / "manifest.json").write_text(json.dumps(manifest))

        with (
            patch.object(pub_module, "check_token_expiry", return_value=None),
            patch("instagram_manager.media.get_media_for_slot", return_value=None),
        ):
            result = publish_item(reel_item, "2026-23")

        assert result["success"] is False
        assert "video" in result["error"].lower()

    def test_meta_api_error_marks_failed(self, tmp_path):
        from instagram_manager.meta_client import MetaAPIError
        plan = _make_plan()
        save_plan(plan)
        _make_asset_dir("2026-23-001", "2026-23", tmp_path)

        with (
            patch.object(pub_module, "check_token_expiry", return_value=None),
            patch("instagram_manager.meta_client.create_media_container", side_effect=MetaAPIError("API error")),
        ):
            result = publish_item(plan.items[0], "2026-23")

        assert result["success"] is False
        loaded = storage.load_plan("2026-23")
        assert loaded.items[0].status == ItemStatus.FAILED

    def test_auth_error_propagates(self, tmp_path):
        from instagram_manager.meta_client import AuthError
        plan = _make_plan()
        save_plan(plan)
        _make_asset_dir("2026-23-001", "2026-23", tmp_path)

        with (
            patch.object(pub_module, "check_token_expiry", return_value=None),
            patch("instagram_manager.meta_client.create_media_container", side_effect=AuthError("expired")),
        ):
            with pytest.raises(AuthError):
                publish_item(plan.items[0], "2026-23")

    def test_skips_non_generated_items(self, tmp_path):
        item = _make_item(status=ItemStatus.PENDING)
        plan = _make_plan(items=[item])
        save_plan(plan)

        with patch.object(pub_module, "check_token_expiry", return_value=None):
            summary = publish_plan("2026-23")

        assert summary["skipped"] == 1
        assert summary["succeeded"] == 0
