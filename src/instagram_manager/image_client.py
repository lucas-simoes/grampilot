"""Pluggable image generation client."""
from __future__ import annotations
import io
import os
import time
from abc import ABC, abstractmethod
from typing import Optional

from PIL import Image


class ImageGenerationError(Exception):
    pass


class ImageClient(ABC):
    """Abstract base class for image generation backends."""

    @abstractmethod
    def generate(self, prompt: str, size: tuple[int, int] = (1080, 1080)) -> bytes:
        """Generate an image and return raw JPEG bytes."""
        ...


def resize_to_instagram(image_bytes: bytes, format: str = "feed") -> bytes:
    """Resize image to Instagram-required dimensions.

    feed/story: 1080×1080
    carousel portrait: 1080×1350
    """
    target = (1080, 1350) if format == "carousel" else (1080, 1080)
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # Smart crop: resize to fill then center-crop
    ratio = max(target[0] / img.width, target[1] / img.height)
    new_size = (int(img.width * ratio), int(img.height * ratio))
    img = img.resize(new_size, Image.LANCZOS)
    left = (img.width - target[0]) // 2
    top = (img.height - target[1]) // 2
    img = img.crop((left, top, left + target[0], top + target[1]))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


class HuggingFaceImageClient(ImageClient):
    """Image generation via HuggingFace huggingface_hub InferenceClient."""

    DEFAULT_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"

    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv("HF_MODEL", self.DEFAULT_MODEL)
        self.token = os.getenv("HF_API_TOKEN", "") or None

    def generate(self, prompt: str, size: tuple[int, int] = (1080, 1080)) -> bytes:
        try:
            from huggingface_hub import InferenceClient
        except ImportError:
            raise ImageGenerationError("huggingface_hub not installed. Run: uv add huggingface_hub")

        client = InferenceClient(token=self.token)
        last_error: Optional[Exception] = None
        for attempt in range(3):
            try:
                result = client.text_to_image(prompt, model=self.model)
                buf = io.BytesIO()
                result.save(buf, format="JPEG", quality=90)
                raw = buf.getvalue()
                return resize_to_instagram(raw, format="feed")
            except Exception as e:
                msg = str(e)
                if "429" in msg or "rate limit" in msg.lower():
                    raise ImageGenerationError("HuggingFace rate limit exceeded (429)")
                last_error = ImageGenerationError(f"HuggingFace error: {msg[:200]}")
                time.sleep(2 ** attempt)
        raise last_error or ImageGenerationError("Max retries exceeded")


class ReplicateImageClient(ImageClient):
    """Image generation via Replicate API."""

    DEFAULT_MODEL = "stability-ai/sdxl:39ed52f2319f9b29e8f679c82c4e9d65b4b7b72a3c79b6e9f8cb4d4fc1d84dcf"

    def __init__(self, model: Optional[str] = None):
        self.model = model or self.DEFAULT_MODEL
        self.token = os.getenv("REPLICATE_API_TOKEN", "")
        if not self.token:
            raise ImageGenerationError("REPLICATE_API_TOKEN not set")

    def generate(self, prompt: str, size: tuple[int, int] = (1080, 1080)) -> bytes:
        import requests
        headers = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }
        # Start prediction
        resp = requests.post(
            "https://api.replicate.com/v1/predictions",
            headers=headers,
            json={"version": self.model.split(":")[-1], "input": {"prompt": prompt}},
            timeout=30,
        )
        if not resp.ok:
            raise ImageGenerationError(f"Replicate start error {resp.status_code}: {resp.text[:200]}")
        prediction = resp.json()
        pred_url = prediction["urls"]["get"]
        # Poll for completion
        for _ in range(30):
            time.sleep(2)
            poll = requests.get(pred_url, headers=headers, timeout=10)
            data = poll.json()
            if data["status"] == "succeeded":
                output_url = data["output"][0] if isinstance(data["output"], list) else data["output"]
                img_resp = requests.get(output_url, timeout=30)
                if not img_resp.ok:
                    raise ImageGenerationError(f"Failed to download image: {img_resp.status_code}")
                return resize_to_instagram(img_resp.content)
            if data["status"] in ("failed", "canceled"):
                raise ImageGenerationError(f"Replicate prediction {data['status']}: {data.get('error', '')}")
        raise ImageGenerationError("Replicate prediction timed out after 60s")


def get_image_client() -> ImageClient:
    """Factory: return the configured image client based on IMAGE_PROVIDER env / config."""
    provider = os.getenv("IMAGE_PROVIDER", "huggingface").lower()
    if provider == "replicate":
        return ReplicateImageClient()
    # Default: huggingface
    return HuggingFaceImageClient()
