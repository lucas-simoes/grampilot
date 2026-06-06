"""Integration tests for image_client.py (HTTP mocked)."""
import io
import pytest
import responses as resp_lib
from PIL import Image
from unittest.mock import patch

from instagram_manager.image_client import (
    HuggingFaceImageClient,
    ReplicateImageClient,
    ImageGenerationError,
    resize_to_instagram,
)


def _make_jpeg(w=200, h=200) -> bytes:
    img = Image.new("RGB", (w, h), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestResizeToInstagram:
    def test_feed_is_1080x1080(self):
        raw = _make_jpeg(500, 700)
        result = resize_to_instagram(raw, format="feed")
        img = Image.open(io.BytesIO(result))
        assert img.size == (1080, 1080)

    def test_carousel_is_1080x1350(self):
        raw = _make_jpeg(500, 400)
        result = resize_to_instagram(raw, format="carousel")
        img = Image.open(io.BytesIO(result))
        assert img.size == (1080, 1350)

    def test_output_is_jpeg(self):
        raw = _make_jpeg()
        result = resize_to_instagram(raw)
        img = Image.open(io.BytesIO(result))
        assert img.format == "JPEG"


class TestHuggingFaceImageClient:
    HF_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

    @resp_lib.activate
    def test_successful_generation(self):
        resp_lib.add(resp_lib.POST, self.HF_URL, body=_make_jpeg(), status=200, content_type="image/jpeg")
        client = HuggingFaceImageClient()
        result = client.generate("a beautiful sunset")
        assert isinstance(result, bytes)
        img = Image.open(io.BytesIO(result))
        assert img.format == "JPEG"

    @resp_lib.activate
    def test_rate_limit_raises(self):
        resp_lib.add(resp_lib.POST, self.HF_URL, status=429)
        client = HuggingFaceImageClient()
        with pytest.raises(ImageGenerationError, match="rate limit"):
            client.generate("test prompt")

    @resp_lib.activate
    def test_retry_on_server_error(self):
        resp_lib.add(resp_lib.POST, self.HF_URL, status=500)
        resp_lib.add(resp_lib.POST, self.HF_URL, status=500)
        resp_lib.add(resp_lib.POST, self.HF_URL, body=_make_jpeg(), status=200, content_type="image/jpeg")
        client = HuggingFaceImageClient()
        with patch("time.sleep"):  # Speed up test
            result = client.generate("test prompt")
        assert isinstance(result, bytes)

    @resp_lib.activate
    def test_exhausted_retries_raises(self):
        for _ in range(3):
            resp_lib.add(resp_lib.POST, self.HF_URL, status=500)
        client = HuggingFaceImageClient()
        with patch("time.sleep"):
            with pytest.raises(ImageGenerationError):
                client.generate("test prompt")
