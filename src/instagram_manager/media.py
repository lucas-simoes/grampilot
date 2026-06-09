"""Creator media library management."""
from __future__ import annotations
import datetime
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from instagram_manager.models import MediaType, ContentFormat
from instagram_manager.storage import (
    load_media_index, save_media_index, MEMORY_DIR, BASE_DIR, get_config,
)
from instagram_manager import logger


MEDIA_DIR = BASE_DIR / "media"

# Accepted formats by type
ACCEPTED_FORMATS = {
    "photo": {"jpg", "jpeg", "png", "webp", "heic"},
    "video": {"mp4", "mov"},
    "audio": {"mp3", "wav", "m4a"},
}


def _detect_media_type(ext: str) -> Optional[str]:
    """Return 'photo', 'video', 'audio', or None for unknown extension."""
    ext = ext.lower().lstrip(".")
    for media_type, exts in ACCEPTED_FORMATS.items():
        if ext in exts:
            return media_type
    return None


def _next_media_id(index: dict) -> str:
    existing = {f["id"] for f in index.get("files", [])}
    n = len(existing) + 1
    while f"media-{n:03d}" in existing:
        n += 1
    return f"media-{n:03d}"


def sync_dropped_files() -> list[str]:
    """Scan .instagram/media/ for files not yet in media-index.json.
    Adds them as unassigned entries. Returns list of new file ids.
    """
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    index = load_media_index()
    known_filenames = {f["filename"] for f in index.get("files", [])}
    new_ids = []
    for file_path in MEDIA_DIR.iterdir():
        if not file_path.is_file():
            continue
        if file_path.name.startswith("."):
            continue
        if file_path.name in known_filenames:
            continue
        ext = file_path.suffix.lstrip(".")
        media_type = _detect_media_type(ext)
        if not media_type:
            continue
        media_id = _next_media_id(index)
        entry = {
            "id": media_id,
            "filename": file_path.name,
            "path": str(file_path),
            "type": media_type,
            "format": ext.lower(),
            "description": "",
            "assigned_item": None,
            "added_at": datetime.datetime.utcnow().isoformat() + "Z",
            "used": False,
            "included_in_style_profile": False,
        }
        index.setdefault("files", []).append(entry)
        index["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
        new_ids.append(media_id)
    if new_ids:
        save_media_index(index)
    return new_ids


def add_media(
    path: str,
    slot_id: Optional[str] = None,
    description: str = "",
) -> dict:
    """Add a media file to the library.

    Copies the file into .instagram/media/ if it is not already there.
    Returns the media index entry dict.
    """
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ext = src.suffix.lstrip(".")
    media_type = _detect_media_type(ext)
    if not media_type:
        supported = ", ".join(
            ext for exts in ACCEPTED_FORMATS.values() for ext in exts
        )
        raise ValueError(f"Format .{ext} not supported. Accepted: {supported}")

    # Validate audio is only added to reel slots
    if media_type == "audio" and slot_id:
        # Validation is deferred to assignment; accept for now
        pass

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    dest = MEDIA_DIR / src.name
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)

    index = load_media_index()
    # Check for duplicate filename
    for entry in index.get("files", []):
        if entry["filename"] == src.name:
            # Update assignment/description if provided
            if slot_id:
                entry["assigned_item"] = slot_id
            if description:
                entry["description"] = description
            index["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
            save_media_index(index)
            return entry

    media_id = _next_media_id(index)
    entry = {
        "id": media_id,
        "filename": src.name,
        "path": str(dest),
        "type": media_type,
        "format": ext.lower(),
        "description": description,
        "assigned_item": slot_id,
        "added_at": datetime.datetime.utcnow().isoformat() + "Z",
        "used": False,
        "included_in_style_profile": False,
    }
    index.setdefault("files", []).append(entry)
    index["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
    save_media_index(index)

    logger.append_event(
        skill="instagram-media",
        item_id=slot_id,
        plan_week=None,
        event_type="media_added",
        outcome="success",
        media_id=media_id,
        filename=src.name,
        media_type=media_type,
    )

    # Auto-update style profile when a photo is added
    if media_type == "photo":
        try:
            cfg = get_config()
            if cfg.style_analysis_auto_update:
                analyze_style(max_photos=cfg.style_analysis_max_photos)
        except Exception:
            pass  # Auto-update failure is non-fatal

    return entry


def list_media() -> dict:
    """Return media index split into assigned and unassigned files.
    Also runs sync_dropped_files() first.
    """
    sync_dropped_files()
    index = load_media_index()
    files = index.get("files", [])
    assigned = [f for f in files if f.get("assigned_item")]
    unassigned = [f for f in files if not f.get("assigned_item")]
    return {"assigned": assigned, "unassigned": unassigned, "total": len(files)}


def assign_media(media_id: str, slot_id: str) -> dict:
    """Assign a media file to a ContentItem slot."""
    index = load_media_index()
    for entry in index.get("files", []):
        if entry["id"] == media_id:
            entry["assigned_item"] = slot_id
            index["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
            save_media_index(index)
            return entry
    raise KeyError(f"Media {media_id} not found in library")


def remove_media(media_id: str) -> bool:
    """Remove a media entry from the index (does NOT delete the file)."""
    index = load_media_index()
    before = len(index.get("files", []))
    index["files"] = [f for f in index.get("files", []) if f["id"] != media_id]
    if len(index["files"]) == before:
        raise KeyError(f"Media {media_id} not found")
    index["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
    save_media_index(index)
    return True


def get_media_for_slot(slot_id: str) -> Optional[dict]:
    """Return the first media file assigned to a slot, or None."""
    index = load_media_index()
    for entry in index.get("files", []):
        if entry.get("assigned_item") == slot_id:
            return entry
    return None


def analyze_style(max_photos: Optional[int] = None) -> str:
    """Run Claude Vision on creator photos and write style-profile.md.

    Returns the generation prompt suffix string.
    """
    import base64
    import anthropic

    if max_photos is None:
        max_photos = 10

    index = load_media_index()
    photos = [
        f for f in index.get("files", [])
        if f.get("type") == "photo"
    ][:max_photos]

    if not photos:
        raise ValueError("No photos in library. Add photos first with /instagram-media add.")

    # Build Claude Vision message
    content = []
    analyzed_paths = []
    for photo in photos:
        photo_path = Path(photo["path"])
        if not photo_path.exists():
            continue
        with open(photo_path, "rb") as f:
            b64 = base64.standard_b64encode(f.read()).decode("utf-8")
        ext = photo["format"].lower()
        media_type_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
        mime = media_type_map.get(ext, "image/jpeg")
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": mime, "data": b64},
        })
        analyzed_paths.append(photo["path"])

    if not analyzed_paths:
        raise ValueError("No photo files found on disk.")

    # Add the text prompt
    prompt_path = Path(".instagram/templates/prompts/analyze-style.md")
    if prompt_path.exists():
        prompt_text = prompt_path.read_text(encoding="utf-8")
    else:
        prompt_text = (
            "Analyse these Instagram photos and describe the visual style. "
            "Include: colour palette, lighting, composition, subject matter, and mood. "
            "Then write a compact 'Generation Prompt Suffix' (one line, comma-separated descriptors) "
            "suitable for appending to AI image generation prompts. "
            "Format your response as a Markdown document with sections: "
            "'## Style Description' and '## Generation Prompt Suffix'."
        )
    content.append({"type": "text", "text": prompt_text})

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": content}],
    )
    analysis = message.content[0].text

    # Write style-profile.md atomically
    style_path = MEMORY_DIR / "style-profile.md"
    style_path.parent.mkdir(parents=True, exist_ok=True)
    photos_list = "\n".join(f"  - {p}" for p in analyzed_paths)
    profile_content = f"""# Visual Style Profile

generated_at: {datetime.datetime.utcnow().isoformat()}Z
photo_sample_count: {len(analyzed_paths)}
photos_analyzed:
{photos_list}

{analysis}
"""
    tmp = style_path.with_suffix(".tmp")
    tmp.write_text(profile_content, encoding="utf-8")
    tmp.rename(style_path)

    # Mark photos as included in style profile
    for entry in index.get("files", []):
        if entry["path"] in analyzed_paths:
            entry["included_in_style_profile"] = True
    index["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
    save_media_index(index)

    logger.append_event(
        skill="instagram-media",
        item_id=None,
        plan_week=None,
        event_type="style_analyzed",
        outcome="success",
        photo_count=len(analyzed_paths),
    )

    # Extract and return the suffix
    marker = "## Generation Prompt Suffix"
    idx = analysis.find(marker)
    if idx != -1:
        after = analysis[idx + len(marker):].strip()
        lines = [l.strip() for l in after.splitlines() if l.strip()]
        return lines[0].strip('"') if lines else ""
    return ""


def extract_audio_metadata(path: str) -> dict:
    """Extract audio metadata using mutagen.

    Returns dict with: duration_seconds, format, bpm (if available), title (if available).
    """
    try:
        import mutagen
        from mutagen import File as MutagenFile
        audio = MutagenFile(path)
        if audio is None:
            return {"format": Path(path).suffix.lstrip("."), "duration_seconds": None}
        duration = getattr(audio.info, "length", None)
        bpm = None
        title = None
        if hasattr(audio, "tags") and audio.tags:
            tags = audio.tags
            # BPM stored differently per format
            for key in ("TBPM", "bpm", "BPM"):
                val = tags.get(key)
                if val:
                    try:
                        bpm = float(str(val[0]) if isinstance(val, list) else str(val))
                    except (ValueError, TypeError):
                        pass
                    break
            for key in ("TIT2", "title", "©nam"):
                val = tags.get(key)
                if val:
                    title = str(val[0]) if isinstance(val, list) else str(val)
                    break
        return {
            "format": Path(path).suffix.lstrip(".").lower(),
            "duration_seconds": round(duration, 1) if duration else None,
            "bpm": bpm,
            "title": title,
        }
    except Exception as e:
        return {"format": Path(path).suffix.lstrip("."), "error": str(e)}
