"""Content asset generator — text (Claude) and image (pluggable client)."""
from __future__ import annotations
import json
import datetime
from pathlib import Path
from typing import Optional

import anthropic

from instagram_manager.models import ContentItem, ContentFormat, ItemStatus
from instagram_manager.storage import (
    update_item_status, load_plan, ASSETS_DIR, MEMORY_DIR,
)
from instagram_manager import logger


def _read_prompt(name: str) -> str:
    p = Path(f".instagram/templates/prompts/{name}.md")
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _brand_text() -> str:
    p = Path(".instagram/memory/brand.md")
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _load_style_suffix() -> str:
    p = Path(".instagram/memory/style-profile.md")
    if not p.exists():
        return ""
    text = p.read_text(encoding="utf-8")
    # Extract the "Generation Prompt Suffix" section
    marker = "## Generation Prompt Suffix"
    idx = text.find(marker)
    if idx == -1:
        return ""
    after = text[idx + len(marker):].strip()
    # Take only the first paragraph
    lines = [l.strip() for l in after.splitlines() if l.strip()]
    return lines[0].strip('"') if lines else ""


def _hashtag_string(item: ContentItem) -> str:
    return " ".join(item.hashtags.all_tags())


def generate_text_assets(item: ContentItem) -> dict:
    """Generate text assets (caption, carousel copy, or script) for one ContentItem.

    Returns a dict with keys:
      - 'caption': str (for feed, story, or carousel main caption)
      - 'slides': list[dict] (for carousel only, per-slide copy)
      - 'script': str (for reel only)
    """
    client = anthropic.Anthropic()
    brand = _brand_text()
    hashtags = _hashtag_string(item)
    result: dict = {}

    if item.format == ContentFormat.REEL:
        # Audio description
        audio_desc = ""
        if item.audio_ref:
            idx_path = MEMORY_DIR / "media-index.json"
            if idx_path.exists():
                import json as _json
                idx = _json.loads(idx_path.read_text())
                for f in idx.get("files", []):
                    if f["id"] == item.audio_ref:
                        audio_desc = f.get("description", f.get("filename", ""))
                        break

        prompt = _read_prompt("generate-reel-script")
        if prompt:
            prompt = (
                prompt
                .replace("{brand_profile}", brand)
                .replace("{theme}", item.theme)
                .replace("{hashtags}", hashtags)
                .replace("{audio_ref_description}", audio_desc or "none")
                .replace("{audio_section_placeholder}", "## Music Style\n[Describe audio mood]" if item.audio_ref else "")
            )
        else:
            prompt = (
                f"Write an Instagram Reel script for theme: {item.theme}.\n"
                f"Brand: {brand}\nHashtags: {hashtags}\n"
                "Include: Intro (hook), Body (beats), CTA, and Caption sections."
            )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        result["script"] = msg.content[0].text

    elif item.format == ContentFormat.CAROUSEL:
        prompt = _read_prompt("generate-carousel")
        if prompt:
            prompt = (
                prompt
                .replace("{brand_profile}", brand)
                .replace("{theme}", item.theme)
                .replace("{hashtags}", hashtags)
                .replace("{slide_count}", str(item.slide_count or 5))
            )
        else:
            prompt = (
                f"Generate {item.slide_count} Instagram carousel slides for theme: {item.theme}.\n"
                f"Output JSON: {{\"caption\": \"...\", \"slides\": [{{\"slide\": 1, \"headline\": \"...\", \"body\": \"...\"}}]}}"
            )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text
        # Try to parse JSON response
        import re as _re
        clean = _re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end > 0:
            try:
                parsed = json.loads(clean[start:end])
                result["caption"] = parsed.get("caption", "")
                result["slides"] = parsed.get("slides", [])
            except json.JSONDecodeError:
                result["caption"] = raw
                result["slides"] = []
        else:
            result["caption"] = raw
            result["slides"] = []

    else:
        # feed or story
        prompt = _read_prompt("generate-caption")
        if prompt:
            prompt = (
                prompt
                .replace("{brand_profile}", brand)
                .replace("{format}", item.format.value)
                .replace("{theme}", item.theme)
                .replace("{hashtags}", hashtags)
            )
        else:
            prompt = (
                f"Write an Instagram {item.format.value} caption for: {item.theme}.\n"
                f"Brand tone: {brand[:200]}\nAppend hashtags: {hashtags}"
            )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        result["caption"] = msg.content[0].text

    return result


def generate_item(item: ContentItem, week: str) -> bool:
    """Generate all assets for one ContentItem.

    Returns True on success, False if the item ends up BLOCKED.
    Updates item status in the plan JSON.
    Creator-media-first: checks for assigned media before generating AI images.
    """
    update_item_status(week, item.id, ItemStatus.GENERATING)
    style_suffix = _load_style_suffix()
    manifest_images = []
    asset_dir = ASSETS_DIR / week / item.id
    asset_dir.mkdir(parents=True, exist_ok=True)

    try:
        text = generate_text_assets(item)

        if item.format == ContentFormat.REEL:
            # Reels: save script, no image generation
            script_path = asset_dir / "script.md"
            script_path.write_text(text.get("script", ""), encoding="utf-8")
            # Save caption placeholder as well
            caption_path = asset_dir / "caption.txt"
            caption_path.write_text(
                item.copy_draft + "\n\n" + _hashtag_string(item), encoding="utf-8"
            )
            manifest = {
                "item_id": item.id,
                "format": item.format.value,
                "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
                "images": [],
                "caption_file": "caption.txt",
                "script_file": "script.md",
                "audio_style_section": bool(item.audio_ref),
            }

        elif item.format == ContentFormat.CAROUSEL:
            # Carousel: generate caption + N slide images
            caption = text.get("caption", item.copy_draft + "\n\n" + _hashtag_string(item))
            caption_path = asset_dir / "caption.txt"
            caption_path.write_text(caption, encoding="utf-8")

            slide_count = item.slide_count or 1
            from instagram_manager.image_client import get_image_client, ImageGenerationError, resize_to_instagram
            from instagram_manager.media import get_media_for_slot

            for slide_num in range(1, slide_count + 1):
                slides = text.get("slides", [])
                slide_data = slides[slide_num - 1] if slide_num <= len(slides) else {}
                slide_theme = slide_data.get("headline", item.theme)

                # Creator-media-first: check for assigned media on first slide
                creator_media = None
                if slide_num == 1:
                    creator_media = get_media_for_slot(item.id)

                if creator_media and creator_media.get("type") in ("photo", "video"):
                    creator_path = Path(creator_media["path"])
                    if creator_path.exists():
                        raw = creator_path.read_bytes()
                        img_bytes = resize_to_instagram(raw, format=item.format.value)
                        filename = f"image_{slide_num:02d}.jpg"
                        (asset_dir / filename).write_bytes(img_bytes)
                        manifest_images.append({
                            "filename": filename,
                            "asset_source": "creator",
                            "creator_media_id": creator_media["id"],
                            "prompt": None,
                            "style_profile_used": False,
                            "width": 1080,
                            "height": 1350,
                        })
                        # Mark creator media as used
                        from instagram_manager.storage import load_media_index, save_media_index
                        idx = load_media_index()
                        for f in idx.get("files", []):
                            if f["id"] == creator_media["id"]:
                                f["used"] = True
                        save_media_index(idx)
                        continue

                # AI generation fallback
                img_client = get_image_client()
                prompt = f"{item.theme} — {slide_theme}"
                if style_suffix:
                    prompt += f", {style_suffix}"
                try:
                    img_bytes = img_client.generate(prompt, size=(1080, 1350))
                    filename = f"image_{slide_num:02d}.jpg"
                    (asset_dir / filename).write_bytes(img_bytes)
                    manifest_images.append({
                        "filename": filename,
                        "asset_source": "ai-generated",
                        "creator_media_id": None,
                        "prompt": prompt,
                        "style_profile_used": bool(style_suffix),
                        "width": 1080,
                        "height": 1350,
                    })
                except ImageGenerationError as e:
                    logger.append_event(
                        skill="instagram-generate",
                        item_id=item.id,
                        plan_week=week,
                        event_type="generation_failed",
                        outcome="failure",
                        error=str(e),
                        slide=slide_num,
                    )
                    update_item_status(week, item.id, ItemStatus.BLOCKED)
                    return False

            manifest = {
                "item_id": item.id,
                "format": item.format.value,
                "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
                "images": manifest_images,
                "caption_file": "caption.txt",
                "script_file": None,
                "audio_style_section": False,
            }

        else:
            # feed or story: single image
            caption = text.get("caption", item.copy_draft + "\n\n" + _hashtag_string(item))
            caption_path = asset_dir / "caption.txt"
            caption_path.write_text(caption, encoding="utf-8")

            from instagram_manager.image_client import get_image_client, ImageGenerationError, resize_to_instagram
            from instagram_manager.media import get_media_for_slot

            # Creator-media-first: check for assigned media
            creator_media = get_media_for_slot(item.id)
            if creator_media and creator_media.get("type") in ("photo", "video"):
                creator_path = Path(creator_media["path"])
                if creator_path.exists():
                    raw = creator_path.read_bytes()
                    img_bytes = resize_to_instagram(raw, format=item.format.value)
                    (asset_dir / "image_01.jpg").write_bytes(img_bytes)
                    manifest_images.append({
                        "filename": "image_01.jpg",
                        "asset_source": "creator",
                        "creator_media_id": creator_media["id"],
                        "prompt": None,
                        "style_profile_used": False,
                        "width": 1080,
                        "height": 1080,
                    })
                    # Mark creator media as used
                    from instagram_manager.storage import load_media_index, save_media_index
                    idx = load_media_index()
                    for f in idx.get("files", []):
                        if f["id"] == creator_media["id"]:
                            f["used"] = True
                    save_media_index(idx)
                else:
                    # Fall through to AI generation if file is missing
                    creator_media = None

            if not creator_media or creator_media.get("type") not in ("photo", "video"):
                # AI generation fallback
                img_client = get_image_client()
                prompt = item.theme
                if style_suffix:
                    prompt += f", {style_suffix}"
                try:
                    img_bytes = img_client.generate(prompt)
                    (asset_dir / "image_01.jpg").write_bytes(img_bytes)
                    manifest_images.append({
                        "filename": "image_01.jpg",
                        "asset_source": "ai-generated",
                        "creator_media_id": None,
                        "prompt": prompt,
                        "style_profile_used": bool(style_suffix),
                        "width": 1080,
                        "height": 1080,
                    })
                except ImageGenerationError as e:
                    logger.append_event(
                        skill="instagram-generate",
                        item_id=item.id,
                        plan_week=week,
                        event_type="generation_failed",
                        outcome="failure",
                        error=str(e),
                    )
                    update_item_status(week, item.id, ItemStatus.BLOCKED)
                    return False

            manifest = {
                "item_id": item.id,
                "format": item.format.value,
                "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
                "images": manifest_images,
                "caption_file": "caption.txt",
                "script_file": None,
                "audio_style_section": False,
            }

    except Exception as e:
        logger.append_event(
            skill="instagram-generate",
            item_id=item.id,
            plan_week=week,
            event_type="generation_error",
            outcome="failure",
            error=str(e),
        )
        update_item_status(week, item.id, ItemStatus.FAILED)
        raise

    # Write manifest
    from instagram_manager.storage import write_manifest
    write_manifest(item.id, week, manifest)

    # Update status
    update_item_status(week, item.id, ItemStatus.GENERATED, assets=[str(asset_dir)])

    logger.append_event(
        skill="instagram-generate",
        item_id=item.id,
        plan_week=week,
        event_type="generated",
        outcome="success",
        format=item.format.value,
        asset_dir=str(asset_dir),
    )
    return True


def generate_plan_assets(
    week: str,
    item_id: Optional[str] = None,
    format_filter: Optional[str] = None,
) -> dict:
    """Generate assets for all approved items in a plan (or a single item)."""
    from rich.console import Console

    console = Console()
    plan = load_plan(week)
    items = plan.items

    if item_id:
        items = [i for i in items if i.id == item_id]
    if format_filter:
        items = [i for i in items if i.format.value == format_filter]

    eligible = [i for i in items if i.status in (ItemStatus.PENDING, ItemStatus.BLOCKED)]

    if not eligible:
        console.print(f"[yellow]No eligible items to generate in plan {week}[/yellow]")
        return {"succeeded": 0, "blocked": 0, "failed": 0}

    console.print(f"\n[bold]Generating assets for plan {week} ({len(eligible)} items)...[/bold]\n")

    succeeded = blocked = failed = 0
    for idx, item in enumerate(eligible, 1):
        prefix = f"[{idx}/{len(eligible)}] {item.id} {item.format.value:10s}"
        try:
            ok = generate_item(item, week)
            if ok:
                succeeded += 1
                console.print(f"  {prefix} [green]✓ generated[/green]")
            else:
                blocked += 1
                console.print(
                    f"  {prefix} [yellow]✗ BLOCKED[/yellow]\n"
                    f"      → Retry with: instagram-manager generate --item {item.id}"
                )
        except Exception as e:
            failed += 1
            console.print(f"  {prefix} [red]✗ FAILED: {e}[/red]")

    console.print(
        f"\n[bold]Generation complete:[/bold] "
        f"[green]{succeeded}[/green] succeeded, "
        f"[yellow]{blocked}[/yellow] blocked, "
        f"[red]{failed}[/red] failed"
    )
    if succeeded > 0:
        console.print(f"Assets saved to .instagram/memory/assets/{week}/")

    return {"succeeded": succeeded, "blocked": blocked, "failed": failed}
