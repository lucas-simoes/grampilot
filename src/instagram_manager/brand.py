"""Brand profile reader and writer."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

from instagram_manager.models import BrandProfile


BRAND_PATH = Path(".instagram/memory/brand.md")


class BrandNotFound(Exception):
    pass


def init_directory_structure() -> None:
    """Create the full .instagram/ directory tree."""
    dirs = [
        Path(".instagram/memory/plans"),
        Path(".instagram/memory/assets"),
        Path(".instagram/memory/insights"),
        Path(".instagram/memory/logs"),
        Path(".instagram/media"),
        Path(".instagram/scripts/bash"),
        Path(".instagram/templates/prompts"),
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def load_brand() -> BrandProfile:
    """Load and parse .instagram/memory/brand.md into a BrandProfile."""
    if not BRAND_PATH.exists():
        raise BrandNotFound(
            "Brand profile not found. Run /instagram-init to create it."
        )
    text = BRAND_PATH.read_text(encoding="utf-8")
    return _parse_brand_md(text)


def _parse_brand_md(text: str) -> BrandProfile:
    """Parse a brand.md file into a BrandProfile dataclass."""
    def extract(key: str) -> str:
        m = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
        return m.group(1).strip() if m else ""

    def extract_list(key: str) -> list[str]:
        # Find section header and collect following `- item` lines
        pattern = rf"^{re.escape(key)}:\s*\n((?:\s+- .+\n?)*)"
        m = re.search(pattern, text, re.MULTILINE)
        if not m:
            return []
        return [
            line.strip().lstrip("- ").strip()
            for line in m.group(1).splitlines()
            if line.strip().startswith("- ")
        ]

    handle = extract("account_handle")
    niche = extract("niche")
    tone = extract("tone_of_voice")
    audience = extract("target_audience")
    language = extract("language") or "en-US"
    frequency = extract("post_frequency") or "7 posts/week"
    pillars = extract_list("content_pillars")
    branded_hashtags = extract_list("branded_hashtags")
    restrictions = extract_list("content_restrictions")
    image_style = extract("image_style")

    return BrandProfile(
        account_handle=handle,
        niche=niche,
        tone_of_voice=tone,
        target_audience=audience,
        language=language,
        post_frequency=frequency,
        content_pillars=pillars,
        branded_hashtags=branded_hashtags,
        content_restrictions=restrictions,
        image_style=image_style,
    )


def save_brand(brand: BrandProfile, template_path: Optional[Path] = None) -> None:
    """Write a BrandProfile to .instagram/memory/brand.md."""
    BRAND_PATH.parent.mkdir(parents=True, exist_ok=True)
    pillars_md = "\n".join(f"  - {p}" for p in brand.content_pillars)
    hashtags_md = "\n".join(f"  - {h}" for h in brand.branded_hashtags)
    restrictions_md = "\n".join(f"  - {r}" for r in brand.content_restrictions)
    content = f"""# Brand Profile

account_handle: {brand.account_handle}
niche: {brand.niche}
tone_of_voice: {brand.tone_of_voice}
target_audience: {brand.target_audience}
language: {brand.language}
post_frequency: {brand.post_frequency}
content_pillars:
{pillars_md}
branded_hashtags:
{hashtags_md}
content_restrictions:
{restrictions_md}
image_style: {brand.image_style}
"""
    BRAND_PATH.write_text(content, encoding="utf-8")
