"""Unit tests for models.py."""
import pytest
from instagram_manager.models import (
    HashtagSet, ContentItem, ContentPlan, ContentFormat, ItemStatus, PlanStatus,
    BrandProfile, CreatorMedia, MediaType,
)


class TestHashtagSet:
    def test_valid_set(self):
        h = HashtagSet(broad=["#a"] * 10, niche=["#b"] * 15, branded=["#c"] * 5)
        assert h.total == 30

    def test_exceeds_30_raises(self):
        with pytest.raises(ValueError, match="30-hashtag limit"):
            HashtagSet(broad=["#a"] * 20, niche=["#b"] * 11, branded=[])

    def test_all_tags_order(self):
        h = HashtagSet(broad=["#broad"], niche=["#niche"], branded=["#brand"])
        assert h.all_tags() == ["#broad", "#niche", "#brand"]

    def test_empty_set(self):
        h = HashtagSet()
        assert h.total == 0


class TestContentItem:
    def _make_item(self, **kwargs):
        defaults = dict(
            id="2026-23-001",
            day="2026-06-01",
            intended_time="09:00",
            format=ContentFormat.FEED,
            theme="test",
            copy_draft="test copy",
        )
        defaults.update(kwargs)
        return ContentItem(**defaults)

    def test_feed_item_created(self):
        item = self._make_item()
        assert item.status == ItemStatus.PENDING
        assert item.format == ContentFormat.FEED

    def test_carousel_requires_slide_count(self):
        with pytest.raises(ValueError, match="slide_count"):
            self._make_item(format=ContentFormat.CAROUSEL, slide_count=None)

    def test_carousel_slide_count_bounds(self):
        with pytest.raises(ValueError, match="slide_count"):
            self._make_item(format=ContentFormat.CAROUSEL, slide_count=1)
        with pytest.raises(ValueError, match="slide_count"):
            self._make_item(format=ContentFormat.CAROUSEL, slide_count=11)

    def test_carousel_valid_slide_count(self):
        item = self._make_item(format=ContentFormat.CAROUSEL, slide_count=5)
        assert item.slide_count == 5

    def test_status_values(self):
        for status in ItemStatus:
            item = self._make_item(status=status)
            assert item.status == status


class TestContentPlan:
    def test_default_status_is_draft(self):
        plan = ContentPlan(week="2026-23", week_start="2026-06-01", week_end="2026-06-07")
        assert plan.status == PlanStatus.DRAFT
        assert plan.approved_at is None

    def test_items_default_empty(self):
        plan = ContentPlan(week="2026-23", week_start="2026-06-01", week_end="2026-06-07")
        assert plan.items == []


class TestBrandProfile:
    def test_valid_brand(self):
        brand = BrandProfile(
            account_handle="@testbrand",
            niche="tech",
            tone_of_voice="professional",
            target_audience="developers",
            content_pillars=["tutorials", "news"],
        )
        assert brand.account_handle == "@testbrand"

    def test_handle_must_start_with_at(self):
        with pytest.raises(ValueError, match="'@'"):
            BrandProfile(
                account_handle="testbrand",
                niche="tech",
                tone_of_voice="pro",
                target_audience="devs",
                content_pillars=["a", "b"],
            )

    def test_minimum_two_pillars(self):
        with pytest.raises(ValueError, match="content_pillars"):
            BrandProfile(
                account_handle="@brand",
                niche="tech",
                tone_of_voice="pro",
                target_audience="devs",
                content_pillars=["only_one"],
            )
