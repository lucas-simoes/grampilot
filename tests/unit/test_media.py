"""Unit tests for media.py."""
import io
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image

from instagram_manager import storage, media as media_module
from instagram_manager.media import (
    add_media, list_media, assign_media, remove_media, sync_dropped_files,
    get_media_for_slot, extract_audio_metadata, analyze_style,
)
from instagram_manager.storage import reset_config


def _make_jpeg(tmp_path: Path, name: str = "test.jpg") -> Path:
    p = tmp_path / name
    img = Image.new("RGB", (200, 200), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    p.write_bytes(buf.getvalue())
    return p


@pytest.fixture(autouse=True)
def tmp_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reset_config()
    # Redirect storage paths
    storage.MEMORY_DIR = tmp_path / ".instagram" / "memory"
    storage.MEDIA_INDEX_PATH = tmp_path / ".instagram" / "memory" / "media-index.json"
    storage.ASSETS_DIR = tmp_path / ".instagram" / "memory" / "assets"
    storage.PLANS_DIR = tmp_path / ".instagram" / "memory" / "plans"
    storage.INSIGHTS_DIR = tmp_path / ".instagram" / "memory" / "insights"
    # Redirect media module paths
    media_module.MEDIA_DIR = tmp_path / ".instagram" / "media"
    yield
    from pathlib import Path as P
    storage.MEMORY_DIR = P(".instagram/memory")
    storage.MEDIA_INDEX_PATH = P(".instagram/memory/media-index.json")
    storage.ASSETS_DIR = P(".instagram/memory/assets")
    storage.PLANS_DIR = P(".instagram/memory/plans")
    storage.INSIGHTS_DIR = P(".instagram/memory/insights")
    media_module.MEDIA_DIR = P(".instagram/media")
    reset_config()


class TestAddMedia:
    def test_add_photo(self, tmp_path):
        src = _make_jpeg(tmp_path, "photo.jpg")
        with patch.object(media_module, "analyze_style", return_value="style"):
            entry = add_media(str(src))
        assert entry["type"] == "photo"
        assert entry["format"] == "jpg"
        assert entry["filename"] == "photo.jpg"
        assert entry["assigned_item"] is None

    def test_add_with_slot(self, tmp_path):
        src = _make_jpeg(tmp_path, "photo2.jpg")
        with patch.object(media_module, "analyze_style", return_value=""):
            entry = add_media(str(src), slot_id="2026-23-001")
        assert entry["assigned_item"] == "2026-23-001"

    def test_unsupported_format_raises(self, tmp_path):
        src = tmp_path / "file.bmp"
        src.write_bytes(b"fake bmp")
        with pytest.raises(ValueError, match="not supported"):
            add_media(str(src))

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            add_media("/nonexistent/path/photo.jpg")

    def test_media_index_updated(self, tmp_path):
        src = _make_jpeg(tmp_path, "photo3.jpg")
        with patch.object(media_module, "analyze_style", return_value=""):
            add_media(str(src))
        idx = storage.load_media_index()
        assert len(idx["files"]) == 1
        assert idx["files"][0]["filename"] == "photo3.jpg"


class TestSyncDroppedFiles:
    def test_detects_new_files(self, tmp_path):
        media_dir = media_module.MEDIA_DIR
        media_dir.mkdir(parents=True, exist_ok=True)
        src = _make_jpeg(tmp_path, "dropped.jpg")
        import shutil
        shutil.copy2(src, media_dir / "dropped.jpg")
        new_ids = sync_dropped_files()
        assert len(new_ids) == 1
        idx = storage.load_media_index()
        assert idx["files"][0]["filename"] == "dropped.jpg"

    def test_ignores_already_indexed(self, tmp_path):
        src = _make_jpeg(tmp_path, "known.jpg")
        with patch.object(media_module, "analyze_style", return_value=""):
            add_media(str(src))
        # Run sync again — should find no new files
        new_ids = sync_dropped_files()
        assert new_ids == []


class TestListMedia:
    def test_split_assigned_unassigned(self, tmp_path):
        src1 = _make_jpeg(tmp_path, "a.jpg")
        src2 = _make_jpeg(tmp_path, "b.jpg")
        with patch.object(media_module, "analyze_style", return_value=""):
            add_media(str(src1))
            add_media(str(src2), slot_id="2026-23-001")
        result = list_media()
        assert len(result["unassigned"]) == 1
        assert len(result["assigned"]) == 1
        assert result["total"] == 2


class TestAssignMedia:
    def test_assign_updates_index(self, tmp_path):
        src = _make_jpeg(tmp_path, "photo.jpg")
        with patch.object(media_module, "analyze_style", return_value=""):
            entry = add_media(str(src))
        updated = assign_media(entry["id"], "2026-23-005")
        assert updated["assigned_item"] == "2026-23-005"
        # Verify persisted
        idx = storage.load_media_index()
        assert idx["files"][0]["assigned_item"] == "2026-23-005"

    def test_unknown_id_raises(self):
        with pytest.raises(KeyError, match="media-999"):
            assign_media("media-999", "2026-23-001")


class TestRemoveMedia:
    def test_remove_from_index(self, tmp_path):
        src = _make_jpeg(tmp_path, "photo.jpg")
        with patch.object(media_module, "analyze_style", return_value=""):
            entry = add_media(str(src))
        remove_media(entry["id"])
        idx = storage.load_media_index()
        assert idx["files"] == []

    def test_unknown_id_raises(self):
        with pytest.raises(KeyError):
            remove_media("media-999")


class TestGetMediaForSlot:
    def test_returns_assigned_entry(self, tmp_path):
        src = _make_jpeg(tmp_path, "photo.jpg")
        with patch.object(media_module, "analyze_style", return_value=""):
            add_media(str(src), slot_id="2026-23-001")
        result = get_media_for_slot("2026-23-001")
        assert result is not None
        assert result["filename"] == "photo.jpg"

    def test_returns_none_when_unassigned(self, tmp_path):
        src = _make_jpeg(tmp_path, "photo.jpg")
        with patch.object(media_module, "analyze_style", return_value=""):
            add_media(str(src))
        result = get_media_for_slot("2026-23-999")
        assert result is None


class TestAnalyzeStyle:
    def test_writes_style_profile(self, tmp_path):
        # Create fake photo in media dir
        media_dir = media_module.MEDIA_DIR
        media_dir.mkdir(parents=True, exist_ok=True)
        photo = _make_jpeg(tmp_path, "sample.jpg")
        import shutil
        shutil.copy2(photo, media_dir / "sample.jpg")
        # Add to index
        storage.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        storage.save_media_index({
            "last_updated": "2026-06-05T00:00:00Z",
            "files": [{
                "id": "media-001",
                "filename": "sample.jpg",
                "path": str(media_dir / "sample.jpg"),
                "type": "photo",
                "format": "jpg",
                "description": "",
                "assigned_item": None,
                "added_at": "2026-06-05T00:00:00Z",
                "used": False,
                "included_in_style_profile": False,
            }],
        })
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=(
            "## Style Description\n**Colour palette**: warm earth tones\n\n"
            "## Generation Prompt Suffix\n\"warm earth tones, natural light\""
        ))]
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = mock_response
            suffix = analyze_style(max_photos=1)
        assert suffix == "warm earth tones, natural light"
        style_path = storage.MEMORY_DIR / "style-profile.md"
        assert style_path.exists()
        content = style_path.read_text()
        assert "Generation Prompt Suffix" in content

    def test_no_photos_raises(self):
        with pytest.raises(ValueError, match="No photos"):
            analyze_style()


class TestExtractAudioMetadata:
    def test_unknown_format_graceful(self, tmp_path):
        # Create a non-audio file and verify graceful handling
        fake_mp3 = tmp_path / "fake.mp3"
        fake_mp3.write_bytes(b"not real audio")
        result = extract_audio_metadata(str(fake_mp3))
        assert "format" in result
        assert result["format"] == "mp3"
