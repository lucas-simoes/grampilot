"""Unit tests for insights.py."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from instagram_manager.models import (
    ContentItem, ContentFormat, ItemStatus, HashtagSet, ContentPlan, PlanStatus,
)
from instagram_manager import storage, insights as insights_module
from instagram_manager.insights import (
    compute_summary, save_week_insights, fetch_week_insights,
)
from instagram_manager.storage import reset_config, save_plan


def _make_plan_with_published_items(week="2026-23", tmp_path=None):
    item1 = ContentItem(
        id=f"{week}-001",
        day="2026-06-01",
        intended_time="09:00",
        format=ContentFormat.FEED,
        theme="test",
        copy_draft="copy",
        hashtags=HashtagSet(),
        status=ItemStatus.PUBLISHED,
        meta_post_id="post-001",
    )
    item2 = ContentItem(
        id=f"{week}-002",
        day="2026-06-02",
        intended_time="18:00",
        format=ContentFormat.CAROUSEL,
        theme="test2",
        copy_draft="copy2",
        hashtags=HashtagSet(broad=[], niche=[], branded=[]),
        slide_count=3,
        status=ItemStatus.PUBLISHED,
        meta_post_id="post-002",
    )
    item3 = ContentItem(
        id=f"{week}-003",
        day="2026-06-03",
        intended_time="12:00",
        format=ContentFormat.STORY,
        theme="test3",
        copy_draft="copy3",
        hashtags=HashtagSet(),
        status=ItemStatus.GENERATED,  # Not published
    )
    return ContentPlan(
        week=week,
        week_start="2026-06-01",
        week_end="2026-06-07",
        status=PlanStatus.APPROVED,
        items=[item1, item2, item3],
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
    yield
    from pathlib import Path as P
    storage.PLANS_DIR = P(".instagram/memory/plans")
    storage.MEMORY_DIR = P(".instagram/memory")
    storage.ASSETS_DIR = P(".instagram/memory/assets")
    storage.INSIGHTS_DIR = P(".instagram/memory/insights")
    storage.MEDIA_INDEX_PATH = P(".instagram/memory/media-index.json")
    reset_config()


class TestComputeSummary:
    def _make_post(self, item_id, fmt, engagement, asset_source="ai-generated", pub_time="09:00"):
        return {
            "item_id": item_id,
            "format": fmt,
            "asset_source": asset_source,
            "published_at": f"2026-06-01T{pub_time}:00Z",
            "data_available": True,
            "metrics": {
                "reach": 1000,
                "engagement_rate": engagement,
            },
        }

    def test_identifies_top_format(self):
        posts = [
            self._make_post("001", "feed", 0.10),
            self._make_post("002", "carousel", 0.20),
            self._make_post("003", "feed", 0.12),
        ]
        summary = compute_summary(posts)
        assert summary["best_format"] == "carousel"

    def test_avg_engagement_rate(self):
        posts = [
            self._make_post("001", "feed", 0.10),
            self._make_post("002", "feed", 0.20),
        ]
        summary = compute_summary(posts)
        assert abs(summary["avg_engagement_rate"] - 0.15) < 0.001

    def test_top_item_id(self):
        posts = [
            self._make_post("001", "feed", 0.05),
            self._make_post("002", "carousel", 0.25),
        ]
        summary = compute_summary(posts)
        assert summary["top_item_id"] == "002"

    def test_best_asset_source(self):
        posts = [
            self._make_post("001", "feed", 0.08, asset_source="ai-generated"),
            self._make_post("002", "feed", 0.18, asset_source="creator"),
        ]
        summary = compute_summary(posts)
        assert summary["best_asset_source"] == "creator"

    def test_empty_posts(self):
        summary = compute_summary([])
        assert summary["avg_engagement_rate"] == 0.0
        assert summary["top_item_id"] is None

    def test_data_not_available_excluded(self):
        posts = [
            self._make_post("001", "feed", 0.10),
            {
                "item_id": "002",
                "format": "story",
                "asset_source": "ai-generated",
                "published_at": "2026-06-01T09:00:00Z",
                "data_available": False,
                "metrics": {"reach": 0, "engagement_rate": 0.0},
            },
        ]
        summary = compute_summary(posts)
        assert summary["top_item_id"] == "001"


class TestSaveWeekInsights:
    def test_saves_json_file(self):
        posts = [
            {
                "item_id": "2026-23-001",
                "format": "feed",
                "asset_source": "ai-generated",
                "published_at": "2026-06-01T09:00:00Z",
                "data_available": True,
                "top_performer": False,
                "metrics": {"reach": 1000, "impressions": 1500, "likes": 80, "comments": 5, "shares": 3, "saved": 12},
            }
        ]
        result = save_week_insights("2026-23", posts)
        insights_path = storage.INSIGHTS_DIR / "2026-23.json"
        assert insights_path.exists()
        data = json.loads(insights_path.read_text())
        assert data["week"] == "2026-23"
        assert len(data["posts"]) == 1
        assert data["posts"][0]["top_performer"] is True  # Only post is top performer

    def test_top_performer_tagged(self):
        posts = [
            {
                "item_id": "001",
                "format": "feed",
                "asset_source": "ai-generated",
                "published_at": "2026-06-01T09:00:00Z",
                "data_available": True,
                "top_performer": False,
                "metrics": {"reach": 1000, "impressions": 1500, "likes": 10, "comments": 1, "shares": 0, "saved": 0},
            },
            {
                "item_id": "002",
                "format": "carousel",
                "asset_source": "creator",
                "published_at": "2026-06-02T18:00:00Z",
                "data_available": True,
                "top_performer": False,
                "metrics": {"reach": 1000, "impressions": 1500, "likes": 100, "comments": 20, "shares": 10, "saved": 30},
            },
        ]
        result = save_week_insights("2026-23", posts)
        top = next(p for p in result["posts"] if p["top_performer"])
        assert top["item_id"] == "002"


class TestFetchWeekInsights:
    def test_fetches_for_published_items(self, tmp_path):
        plan = _make_plan_with_published_items()
        save_plan(plan)

        mock_metrics = {"reach": 1250, "impressions": 1840, "likes": 87, "comments": 12, "shares": 5, "saved": 23, "data_available": True}

        with patch("instagram_manager.meta_client.get_post_insights", return_value=mock_metrics):
            result = fetch_week_insights("2026-23")

        assert len(result["posts"]) == 2  # item3 has no meta_post_id
        insights_path = storage.INSIGHTS_DIR / "2026-23.json"
        assert insights_path.exists()

    def test_data_not_available_flag(self, tmp_path):
        plan = _make_plan_with_published_items()
        save_plan(plan)

        not_available = {"data_available": False}
        with patch("instagram_manager.meta_client.get_post_insights", return_value=not_available):
            result = fetch_week_insights("2026-23")

        for p in result["posts"]:
            assert p["data_available"] is False

    def test_engagement_rate_computed(self, tmp_path):
        plan = _make_plan_with_published_items()
        save_plan(plan)

        mock_metrics = {"reach": 1000, "likes": 80, "comments": 10, "shares": 5, "saved": 5, "data_available": True}
        with patch("instagram_manager.meta_client.get_post_insights", return_value=mock_metrics):
            result = fetch_week_insights("2026-23")

        for p in result["posts"]:
            if p["data_available"]:
                assert p["metrics"]["engagement_rate"] == pytest.approx(0.10, rel=0.01)
