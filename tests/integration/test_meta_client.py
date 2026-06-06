"""Integration tests for meta_client.py (HTTP mocked with responses)."""
import json
import pytest
import responses as resp_lib
from unittest.mock import patch

from instagram_manager.meta_client import (
    create_media_container,
    publish_container,
    validate_credentials,
    get_post_insights,
    AuthError,
    MetaAPIError,
    RateLimitError,
)


MOCK_IG_USER_ID = "123456789"
MOCK_TOKEN = "test_token_abc"
BASE = "https://graph.facebook.com/v18.0"


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", MOCK_TOKEN)
    monkeypatch.setenv("META_IG_USER_ID", MOCK_IG_USER_ID)


class TestValidateCredentials:
    @resp_lib.activate
    def test_valid_credentials(self):
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/{MOCK_IG_USER_ID}",
            json={"id": MOCK_IG_USER_ID, "username": "testaccount"},
            status=200,
        )
        result = validate_credentials()
        assert result["username"] == "testaccount"

    @resp_lib.activate
    def test_invalid_token_raises_auth_error(self):
        resp_lib.add(resp_lib.GET, f"{BASE}/{MOCK_IG_USER_ID}", status=401)
        with pytest.raises(AuthError):
            validate_credentials()


class TestCreateMediaContainer:
    @resp_lib.activate
    def test_creates_container(self):
        resp_lib.add(
            resp_lib.POST,
            f"{BASE}/{MOCK_IG_USER_ID}/media",
            json={"id": "container-789"},
            status=200,
        )
        container_id = create_media_container(
            media_type="IMAGE",
            image_url="https://example.com/image.jpg",
            caption="Test caption",
        )
        assert container_id == "container-789"

    @resp_lib.activate
    def test_rate_limit_raises(self):
        resp_lib.add(resp_lib.POST, f"{BASE}/{MOCK_IG_USER_ID}/media", status=429)
        with pytest.raises(RateLimitError):
            create_media_container(media_type="IMAGE", image_url="https://example.com/img.jpg")

    @resp_lib.activate
    def test_retry_on_5xx(self):
        resp_lib.add(resp_lib.POST, f"{BASE}/{MOCK_IG_USER_ID}/media", status=503)
        resp_lib.add(resp_lib.POST, f"{BASE}/{MOCK_IG_USER_ID}/media", status=503)
        resp_lib.add(
            resp_lib.POST,
            f"{BASE}/{MOCK_IG_USER_ID}/media",
            json={"id": "container-retry"},
            status=200,
        )
        with patch("time.sleep"):  # Speed up test
            container_id = create_media_container(
                media_type="IMAGE",
                image_url="https://example.com/img.jpg",
            )
        assert container_id == "container-retry"

    @resp_lib.activate
    def test_exhausted_retries_raises(self):
        for _ in range(3):
            resp_lib.add(resp_lib.POST, f"{BASE}/{MOCK_IG_USER_ID}/media", status=500)
        with patch("time.sleep"):
            with pytest.raises(MetaAPIError):
                create_media_container(media_type="IMAGE", image_url="https://example.com/img.jpg")


class TestPublishContainer:
    @resp_lib.activate
    def test_publishes_and_returns_post_id(self):
        resp_lib.add(
            resp_lib.POST,
            f"{BASE}/{MOCK_IG_USER_ID}/media_publish",
            json={"id": "post-12345"},
            status=200,
        )
        post_id = publish_container("container-789")
        assert post_id == "post-12345"

    @resp_lib.activate
    def test_401_raises_auth_error(self):
        resp_lib.add(resp_lib.POST, f"{BASE}/{MOCK_IG_USER_ID}/media_publish", status=401)
        with pytest.raises(AuthError):
            publish_container("container-789")


class TestGetPostInsights:
    MEDIA_ID = "media-111"

    @resp_lib.activate
    def test_returns_metrics(self):
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/{self.MEDIA_ID}/insights",
            json={
                "data": [
                    {"name": "reach", "values": [{"value": 1000}]},
                    {"name": "impressions", "values": [{"value": 1500}]},
                    {"name": "likes", "values": [{"value": 80}]},
                ]
            },
            status=200,
        )
        result = get_post_insights(self.MEDIA_ID)
        assert result["reach"] == 1000
        assert result["data_available"] is True

    @resp_lib.activate
    def test_data_not_available_returns_flag(self):
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/{self.MEDIA_ID}/insights",
            json={"error": {"code": 100, "message": "Data not available"}},
            status=400,
        )
        result = get_post_insights(self.MEDIA_ID)
        assert result["data_available"] is False
