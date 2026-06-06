"""Unit tests for planner.py."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from instagram_manager.models import ContentPlan, ContentFormat, PlanStatus
from instagram_manager import storage, planner as planner_module
from instagram_manager.storage import reset_config


MOCK_PLAN_JSON = json.dumps([
    {
        "id": "2026-23-001",
        "day": "2026-06-02",
        "intended_time": "09:00",
        "format": "feed",
        "theme": "Productivity tips",
        "copy_draft": "Start your week strong! 💪 #motivation",
        "hashtags": {"broad": ["#productivity"], "niche": ["#morningroutine"], "branded": ["#mybrand"]},
        "slide_count": None,
        "audio_ref": None,
        "status": "pending",
    },
    {
        "id": "2026-23-002",
        "day": "2026-06-03",
        "intended_time": "18:00",
        "format": "carousel",
        "theme": "Morning routine guide",
        "copy_draft": "6 steps to a better morning ☀️",
        "hashtags": {"broad": ["#wellness"], "niche": ["#routine"], "branded": ["#mybrand"]},
        "slide_count": 6,
        "audio_ref": None,
        "status": "pending",
    },
    {
        "id": "2026-23-003",
        "day": "2026-06-04",
        "intended_time": "12:00",
        "format": "story",
        "theme": "Behind the scenes",
        "copy_draft": "Ever wonder how we create content? 👀",
        "hashtags": {"broad": ["#bts"], "niche": [], "branded": ["#mybrand"]},
        "slide_count": None,
        "audio_ref": None,
        "status": "pending",
    },
    {
        "id": "2026-23-004",
        "day": "2026-06-05",
        "intended_time": "09:00",
        "format": "feed",
        "theme": "Product spotlight",
        "copy_draft": "Introducing our latest feature 🎉",
        "hashtags": {"broad": ["#product"], "niche": ["#launch"], "branded": ["#mybrand"]},
        "slide_count": None,
        "audio_ref": None,
        "status": "pending",
    },
    {
        "id": "2026-23-005",
        "day": "2026-06-06",
        "intended_time": "19:00",
        "format": "reel",
        "theme": "Quick tutorial",
        "copy_draft": "Watch how easy this is! 🎬",
        "hashtags": {"broad": ["#tutorial"], "niche": ["#howto"], "branded": ["#mybrand"]},
        "slide_count": None,
        "audio_ref": None,
        "status": "pending",
    },
    {
        "id": "2026-23-006",
        "day": "2026-06-07",
        "intended_time": "10:00",
        "format": "carousel",
        "theme": "Weekend inspiration",
        "copy_draft": "Make your weekend count ✨",
        "hashtags": {"broad": ["#weekend"], "niche": ["#inspo"], "branded": ["#mybrand"]},
        "slide_count": 4,
        "audio_ref": None,
        "status": "pending",
    },
    {
        "id": "2026-23-007",
        "day": "2026-06-08",
        "intended_time": "11:00",
        "format": "story",
        "theme": "Community Q&A",
        "copy_draft": "Ask me anything! 💬",
        "hashtags": {"broad": ["#qa"], "niche": [], "branded": ["#mybrand"]},
        "slide_count": None,
        "audio_ref": None,
        "status": "pending",
    },
])


@pytest.fixture(autouse=True)
def tmp_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reset_config()
    storage.PLANS_DIR = tmp_path / ".instagram" / "memory" / "plans"
    storage.MEMORY_DIR = tmp_path / ".instagram" / "memory"
    storage.INSIGHTS_DIR = tmp_path / ".instagram" / "memory" / "insights"
    storage.MEDIA_INDEX_PATH = tmp_path / ".instagram" / "memory" / "media-index.json"
    # Create brand.md
    brand_dir = tmp_path / ".instagram" / "memory"
    brand_dir.mkdir(parents=True, exist_ok=True)
    (brand_dir / "brand.md").write_text(
        "# Brand Profile\naccount_handle: @testbrand\nniche: tech\ntone_of_voice: friendly\n"
        "target_audience: developers\nlanguage: en-US\npost_frequency: 7/week\n"
        "content_pillars:\n  - tutorials\n  - news\nbranded_hashtags:\n  - #testbrand\n"
        "content_restrictions:\nimage_style: clean\n",
        encoding="utf-8",
    )
    # Create prompt template
    prompts_dir = tmp_path / ".instagram" / "templates" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "plan-week.md").write_text(
        "Generate a weekly plan for week {week}. Brand: {brand_profile}. "
        "Insights: {insights_summary}. Theme: {theme_override}. "
        "Start: {week_start}. End: {week_end}. Output only a JSON array.",
        encoding="utf-8",
    )
    yield
    from pathlib import Path as P
    storage.PLANS_DIR = P(".instagram/memory/plans")
    storage.MEMORY_DIR = P(".instagram/memory")
    storage.INSIGHTS_DIR = P(".instagram/memory/insights")
    storage.MEDIA_INDEX_PATH = P(".instagram/memory/media-index.json")
    reset_config()


def _mock_claude_response(text: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


class TestGeneratePlan:
    def test_generates_7_items(self):
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_claude_response(MOCK_PLAN_JSON)
            plan = planner_module.generate_plan(week="2026-23")
        assert isinstance(plan, ContentPlan)
        assert plan.week == "2026-23"
        assert len(plan.items) == 7
        assert plan.status == PlanStatus.DRAFT

    def test_plan_saved_to_disk(self):
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_claude_response(MOCK_PLAN_JSON)
            plan = planner_module.generate_plan(week="2026-23")
        json_path = storage.PLANS_DIR / "2026-23.json"
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert data["week"] == "2026-23"

    def test_fallback_when_no_insights(self):
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_claude_response(MOCK_PLAN_JSON)
            plan = planner_module.generate_plan(week="2026-23")
        # Should not raise even without insights
        assert plan is not None

    def test_theme_override_in_prompt(self):
        captured = []
        def mock_create(**kwargs):
            captured.append(kwargs["messages"][0]["content"])
            return _mock_claude_response(MOCK_PLAN_JSON)
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.side_effect = mock_create
            planner_module.generate_plan(week="2026-23", theme="summer recipes")
        assert "summer recipes" in captured[0]

    def test_uses_current_week_when_none(self):
        import datetime
        today = datetime.date.today()
        iso = today.isocalendar()
        expected_week = f"{iso[0]}-{iso[1]:02d}"
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_claude_response(MOCK_PLAN_JSON)
            plan = planner_module.generate_plan()
        assert plan.week == expected_week

    def test_carousel_has_slide_count(self):
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_claude_response(MOCK_PLAN_JSON)
            plan = planner_module.generate_plan(week="2026-23")
        carousels = [i for i in plan.items if i.format == ContentFormat.CAROUSEL]
        for c in carousels:
            assert c.slide_count is not None
            assert 2 <= c.slide_count <= 10
