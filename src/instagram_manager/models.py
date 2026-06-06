"""Data model dataclasses for Instagram Manager."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import datetime


class PlanStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ItemStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    GENERATED = "generated"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    BLOCKED = "blocked"


class ContentFormat(str, Enum):
    FEED = "feed"
    CAROUSEL = "carousel"
    REEL = "reel"
    STORY = "story"


class MediaType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    AUDIO = "audio"


@dataclass
class HashtagSet:
    broad: list[str] = field(default_factory=list)
    niche: list[str] = field(default_factory=list)
    branded: list[str] = field(default_factory=list)

    def __post_init__(self):
        total = len(self.broad) + len(self.niche) + len(self.branded)
        if total > 30:
            raise ValueError(f"HashtagSet total ({total}) exceeds 30-hashtag limit")

    @property
    def total(self) -> int:
        return len(self.broad) + len(self.niche) + len(self.branded)

    def all_tags(self) -> list[str]:
        return self.broad + self.niche + self.branded


@dataclass
class ContentAsset:
    item_id: str
    format: ContentFormat
    generated_at: str  # ISO 8601
    images: list[dict] = field(default_factory=list)  # list of image manifest dicts
    caption_file: Optional[str] = None
    script_file: Optional[str] = None
    audio_style_section: bool = False


@dataclass
class ContentItem:
    id: str
    day: str  # YYYY-MM-DD
    intended_time: str  # HH:MM
    format: ContentFormat
    theme: str
    copy_draft: str
    hashtags: HashtagSet = field(default_factory=HashtagSet)
    slide_count: Optional[int] = None
    audio_ref: Optional[str] = None  # media-index id
    status: ItemStatus = ItemStatus.PENDING
    assets: list[str] = field(default_factory=list)  # asset directory paths
    meta_post_id: Optional[str] = None
    publish_event: Optional[dict] = None
    insights: Optional[dict] = None

    def __post_init__(self):
        if self.format == ContentFormat.CAROUSEL:
            if self.slide_count is None or not (2 <= self.slide_count <= 10):
                raise ValueError(
                    f"carousel slide_count must be 2–10, got {self.slide_count}"
                )


@dataclass
class ContentPlan:
    week: str  # YYYY-WW
    week_start: str  # YYYY-MM-DD
    week_end: str  # YYYY-MM-DD
    status: PlanStatus = PlanStatus.DRAFT
    created_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    approved_at: Optional[str] = None
    items: list[ContentItem] = field(default_factory=list)


@dataclass
class CreatorMedia:
    id: str
    filename: str
    path: str
    type: MediaType
    format: str  # jpg, png, mp4, mp3, etc.
    description: str = ""
    assigned_item: Optional[str] = None
    added_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    used: bool = False
    included_in_style_profile: bool = False


@dataclass
class StyleProfile:
    generated_at: str  # ISO 8601
    photo_sample_count: int
    photos_analyzed: list[str] = field(default_factory=list)
    style_description: str = ""
    generation_prompt_suffix: str = ""


@dataclass
class PublishEvent:
    event_id: str
    timestamp: str  # ISO 8601
    skill: str
    item_id: str
    plan_week: str
    event_type: str  # published | scheduled | failed | retry
    outcome: str  # success | failure
    meta_post_id: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class PostInsights:
    item_id: str
    meta_post_id: str
    format: ContentFormat
    asset_source: str  # "creator" | "ai-generated"
    published_at: str  # ISO 8601
    reach: int = 0
    impressions: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saved: int = 0
    engagement_rate: float = 0.0
    data_available: bool = True
    top_performer: bool = False


@dataclass
class BrandProfile:
    account_handle: str
    niche: str
    tone_of_voice: str
    target_audience: str
    language: str = "en-US"
    post_frequency: str = "7 posts/week"
    content_pillars: list[str] = field(default_factory=list)
    branded_hashtags: list[str] = field(default_factory=list)
    content_restrictions: list[str] = field(default_factory=list)
    image_style: str = ""

    def __post_init__(self):
        if not self.account_handle.startswith("@"):
            raise ValueError("account_handle must start with '@'")
        if len(self.content_pillars) < 2:
            raise ValueError("BrandProfile must have at least 2 content_pillars")
