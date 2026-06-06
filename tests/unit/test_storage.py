"""Unit tests for storage.py."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from instagram_manager.models import (
    ContentPlan, ContentItem, ContentFormat, ItemStatus, PlanStatus, HashtagSet,
)
from instagram_manager import storage
from instagram_manager.storage import (
    save_plan, load_plan, update_item_status, approve_plan,
    save_media_index, load_media_index, save_insights, load_insights,
    PlanNotFound, AlreadyApproved, reset_config,
)


def _make_plan(week="2026-99") -> ContentPlan:
    item = ContentItem(
        id=f"{week}-001",
        day="2026-01-01",
        intended_time="09:00",
        format=ContentFormat.FEED,
        theme="test",
        copy_draft="test copy",
        hashtags=HashtagSet(broad=["#test"], niche=[], branded=[]),
    )
    return ContentPlan(
        week=week,
        week_start="2026-01-01",
        week_end="2026-01-07",
        items=[item],
    )


@pytest.fixture(autouse=True)
def tmp_instagram(tmp_path, monkeypatch):
    """Redirect all storage paths to a temp directory."""
    monkeypatch.chdir(tmp_path)
    reset_config()
    # Re-import path constants with new cwd
    storage.PLANS_DIR = tmp_path / ".instagram" / "memory" / "plans"
    storage.MEMORY_DIR = tmp_path / ".instagram" / "memory"
    storage.INSIGHTS_DIR = tmp_path / ".instagram" / "memory" / "insights"
    storage.MEDIA_INDEX_PATH = tmp_path / ".instagram" / "memory" / "media-index.json"
    yield
    # Reset to relative paths
    from pathlib import Path
    storage.PLANS_DIR = Path(".instagram/memory/plans")
    storage.MEMORY_DIR = Path(".instagram/memory")
    storage.INSIGHTS_DIR = Path(".instagram/memory/insights")
    storage.MEDIA_INDEX_PATH = Path(".instagram/memory/media-index.json")
    reset_config()


class TestSavePlan:
    def test_round_trip(self):
        plan = _make_plan()
        save_plan(plan)
        loaded = load_plan(plan.week)
        assert loaded.week == plan.week
        assert loaded.status == PlanStatus.DRAFT
        assert len(loaded.items) == 1
        assert loaded.items[0].id == f"{plan.week}-001"

    def test_json_file_created(self):
        plan = _make_plan("2026-50")
        save_plan(plan)
        json_path = storage.PLANS_DIR / "2026-50.json"
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert data["week"] == "2026-50"

    def test_md_file_created(self):
        plan = _make_plan("2026-51")
        save_plan(plan)
        md_path = storage.PLANS_DIR / "2026-51.md"
        assert md_path.exists()


class TestLoadPlan:
    def test_not_found_raises(self):
        with pytest.raises(PlanNotFound):
            load_plan("2026-00")


class TestUpdateItemStatus:
    def test_status_transition(self):
        plan = _make_plan("2026-98")
        save_plan(plan)
        update_item_status("2026-98", "2026-98-001", ItemStatus.GENERATED)
        loaded = load_plan("2026-98")
        assert loaded.items[0].status == ItemStatus.GENERATED

    def test_item_not_found_raises(self):
        plan = _make_plan("2026-97")
        save_plan(plan)
        with pytest.raises(PlanNotFound):
            update_item_status("2026-97", "nonexistent", ItemStatus.FAILED)

    def test_extra_kwargs_set(self):
        plan = _make_plan("2026-96")
        save_plan(plan)
        update_item_status("2026-96", "2026-96-001", ItemStatus.PUBLISHED, meta_post_id="12345")
        loaded = load_plan("2026-96")
        assert loaded.items[0].meta_post_id == "12345"


class TestApprovePlan:
    def test_approve_draft(self):
        plan = _make_plan("2026-95")
        save_plan(plan)
        approved = approve_plan("2026-95")
        assert approved.status == PlanStatus.APPROVED
        assert approved.approved_at is not None

    def test_already_approved_raises(self):
        plan = _make_plan("2026-94")
        save_plan(plan)
        approve_plan("2026-94")
        with pytest.raises(AlreadyApproved):
            approve_plan("2026-94")


class TestMediaIndex:
    def test_load_empty_returns_default(self):
        idx = load_media_index()
        assert idx["files"] == []

    def test_save_load_round_trip(self):
        idx = {"last_updated": "2026-06-05T00:00:00Z", "files": [{"id": "m1"}]}
        save_media_index(idx)
        loaded = load_media_index()
        assert loaded["files"][0]["id"] == "m1"


class TestInsights:
    def test_load_missing_returns_none(self):
        assert load_insights("2026-00") is None

    def test_save_load_round_trip(self):
        data = {"week": "2026-23", "posts": []}
        save_insights("2026-23", data)
        loaded = load_insights("2026-23")
        assert loaded["week"] == "2026-23"
