"""Unit tests for generator.py."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from instagram_manager.models import (
    ContentItem, ContentFormat, ItemStatus, HashtagSet, ContentPlan, PlanStatus,
)
from instagram_manager import storage, generator as gen_module
from instagram_manager.storage import reset_config, save_plan


def _make_item(fmt=ContentFormat.FEED, slide_count=None, audio_ref=None) -> ContentItem:
    return ContentItem(
        id="2026-23-001",
        day="2026-06-01",
        intended_time="09:00",
        format=fmt,
        theme="test theme",
        copy_draft="test copy",
        hashtags=HashtagSet(broad=["#test"], niche=[], branded=[]),
        slide_count=slide_count,
        audio_ref=audio_ref,
    )


def _make_plan(week="2026-23", items=None) -> ContentPlan:
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
    # Brand profile
    brand_dir = tmp_path / ".instagram" / "memory"
    brand_dir.mkdir(parents=True, exist_ok=True)
    (brand_dir / "brand.md").write_text(
        "account_handle: @test\nniche: tech\ntone_of_voice: friendly\n"
        "target_audience: devs\ncontent_pillars:\n  - a\n  - b\n",
        encoding="utf-8",
    )
    # Prompts
    prompts_dir = tmp_path / ".instagram" / "templates" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    for name in ["generate-caption", "generate-carousel", "generate-reel-script"]:
        (prompts_dir / f"{name}.md").write_text(f"# Prompt {name}\nGenerate for: {{theme}}", encoding="utf-8")
    yield
    from pathlib import Path as P
    storage.PLANS_DIR = P(".instagram/memory/plans")
    storage.MEMORY_DIR = P(".instagram/memory")
    storage.ASSETS_DIR = P(".instagram/memory/assets")
    storage.INSIGHTS_DIR = P(".instagram/memory/insights")
    storage.MEDIA_INDEX_PATH = P(".instagram/memory/media-index.json")
    reset_config()


def _mock_claude(text: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


def _mock_image_bytes():
    """Return minimal valid JPEG bytes."""
    from PIL import Image
    import io
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestGenerateTextAssets:
    def test_feed_returns_caption(self):
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_claude("Test caption #test")
            item = _make_item(ContentFormat.FEED)
            result = gen_module.generate_text_assets(item)
        assert "caption" in result
        assert result["caption"] == "Test caption #test"

    def test_reel_returns_script(self):
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_claude("# Script\n## Intro\nHook!")
            item = _make_item(ContentFormat.REEL)
            result = gen_module.generate_text_assets(item)
        assert "script" in result

    def test_carousel_parses_json(self):
        carousel_json = '{"caption": "Main caption", "slides": [{"slide": 1, "headline": "h1", "body": "b1"}]}'
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_claude(carousel_json)
            item = _make_item(ContentFormat.CAROUSEL, slide_count=3)
            result = gen_module.generate_text_assets(item)
        assert result.get("caption") == "Main caption"
        assert len(result.get("slides", [])) == 1

    def test_story_returns_caption(self):
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_claude("Story caption!")
            item = _make_item(ContentFormat.STORY)
            result = gen_module.generate_text_assets(item)
        assert "caption" in result


class TestGenerateItem:
    def test_feed_creates_manifest_and_files(self):
        plan = _make_plan()
        save_plan(plan)
        with (
            patch("anthropic.Anthropic") as MockClient,
            patch("instagram_manager.image_client.get_image_client") as MockImgClient,
        ):
            MockClient.return_value.messages.create.return_value = _mock_claude("Caption text #test")
            img_mock = MagicMock()
            img_mock.generate.return_value = _mock_image_bytes()
            MockImgClient.return_value = img_mock
            ok = gen_module.generate_item(plan.items[0], "2026-23")
        assert ok is True
        manifest_path = storage.ASSETS_DIR / "2026-23" / "2026-23-001" / "manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert manifest["images"][0]["asset_source"] == "ai-generated"
        assert manifest["caption_file"] == "caption.txt"

    def test_blocked_on_image_error(self):
        from instagram_manager.image_client import ImageGenerationError
        plan = _make_plan()
        save_plan(plan)
        with (
            patch("anthropic.Anthropic") as MockClient,
            patch("instagram_manager.image_client.get_image_client") as MockImgClient,
        ):
            MockClient.return_value.messages.create.return_value = _mock_claude("Caption")
            img_mock = MagicMock()
            img_mock.generate.side_effect = ImageGenerationError("rate limit")
            MockImgClient.return_value = img_mock
            ok = gen_module.generate_item(plan.items[0], "2026-23")
        assert ok is False
        loaded = storage.load_plan("2026-23")
        assert loaded.items[0].status == ItemStatus.BLOCKED

    def test_reel_script_saved_no_image(self):
        plan = _make_plan(items=[_make_item(ContentFormat.REEL)])
        save_plan(plan)
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_claude("# Script\n## Intro\nHook!")
            ok = gen_module.generate_item(plan.items[0], "2026-23")
        assert ok is True
        script_path = storage.ASSETS_DIR / "2026-23" / "2026-23-001" / "script.md"
        assert script_path.exists()
        manifest_path = storage.ASSETS_DIR / "2026-23" / "2026-23-001" / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        assert manifest["script_file"] == "script.md"
        assert manifest["images"] == []

    def test_carousel_produces_n_slides(self):
        carousel_item = _make_item(ContentFormat.CAROUSEL, slide_count=3)
        carousel_json = json.dumps({
            "caption": "Carousel caption",
            "slides": [
                {"slide": 1, "headline": "h1", "body": "b1"},
                {"slide": 2, "headline": "h2", "body": "b2"},
                {"slide": 3, "headline": "h3", "body": "b3"},
            ],
        })
        plan = _make_plan(items=[carousel_item])
        save_plan(plan)
        with (
            patch("anthropic.Anthropic") as MockClient,
            patch("instagram_manager.image_client.get_image_client") as MockImgClient,
        ):
            MockClient.return_value.messages.create.return_value = _mock_claude(carousel_json)
            img_mock = MagicMock()
            img_mock.generate.return_value = _mock_image_bytes()
            MockImgClient.return_value = img_mock
            ok = gen_module.generate_item(plan.items[0], "2026-23")
        assert ok is True
        manifest_path = storage.ASSETS_DIR / "2026-23" / "2026-23-001" / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        assert len(manifest["images"]) == 3
