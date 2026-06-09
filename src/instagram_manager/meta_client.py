"""Meta Graph API HTTP client."""
from __future__ import annotations
import os
import time
import requests
from typing import Optional


META_BASE = "https://graph.facebook.com"
META_VERSION = "v18.0"


class AuthError(Exception):
    pass


class RateLimitError(Exception):
    pass


class MetaAPIError(Exception):
    def __init__(self, message: str, code: int = 0):
        super().__init__(message)
        self.code = code


def _get_token() -> str:
    token = os.getenv("META_ACCESS_TOKEN", "")
    if not token:
        raise AuthError("META_ACCESS_TOKEN not set in environment")
    return token


def _get_ig_user_id() -> str:
    uid = os.getenv("META_IG_USER_ID", "")
    if not uid:
        raise AuthError("META_IG_USER_ID not set in environment")
    return uid


def validate_credentials() -> dict:
    """Validate META_ACCESS_TOKEN by calling GET /{IG_USER_ID}?fields=id,username.
    Returns account info dict or raises AuthError.
    """
    token = _get_token()
    ig_user_id = _get_ig_user_id()
    url = f"{META_BASE}/{META_VERSION}/{ig_user_id}"
    params = {"fields": "id,username", "access_token": token}
    try:
        resp = requests.get(url, params=params, timeout=10)
    except requests.RequestException as e:
        raise MetaAPIError(f"Network error: {e}")
    if resp.status_code == 401:
        raise AuthError("META_ACCESS_TOKEN invalid or expired (HTTP 401)")
    if not resp.ok:
        data = resp.json() if resp.content else {}
        msg = data.get("error", {}).get("message", resp.text)
        raise MetaAPIError(f"Meta API error {resp.status_code}: {msg}", code=resp.status_code)
    return resp.json()


def create_media_container(
    media_type: str,
    image_url: Optional[str] = None,
    video_url: Optional[str] = None,
    caption: str = "",
    children: Optional[list[str]] = None,
) -> str:
    """Create a media container. Returns container ID.
    media_type: IMAGE | VIDEO | REELS | CAROUSEL_ALBUM | STORIES
    """
    token = _get_token()
    ig_user_id = _get_ig_user_id()
    url = f"{META_BASE}/{META_VERSION}/{ig_user_id}/media"
    payload: dict = {
        "media_type": media_type,
        "caption": caption,
        "access_token": token,
    }
    if image_url:
        payload["image_url"] = image_url
    if video_url:
        payload["video_url"] = video_url
    if children:
        payload["children"] = ",".join(children)

    return _post_with_retry(url, payload)


def publish_container(container_id: str) -> str:
    """Publish a media container. Returns post ID."""
    token = _get_token()
    ig_user_id = _get_ig_user_id()
    url = f"{META_BASE}/{META_VERSION}/{ig_user_id}/media_publish"
    payload = {"creation_id": container_id, "access_token": token}
    return _post_with_retry(url, payload)


def _post_with_retry(url: str, payload: dict, max_retries: int = 3, backoff: float = 10.0) -> str:
    """POST with exponential retry on 5xx; raise RateLimitError on 429."""
    last_error: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, data=payload, timeout=30)
        except requests.RequestException as e:
            last_error = MetaAPIError(f"Network error: {e}")
            time.sleep(backoff * (2 ** attempt))
            continue
        if resp.status_code == 429:
            raise RateLimitError("Meta API rate limit hit (429)")
        if resp.status_code == 401:
            raise AuthError("META_ACCESS_TOKEN invalid or expired during API call")
        if resp.status_code >= 500:
            last_error = MetaAPIError(f"Server error {resp.status_code}", code=resp.status_code)
            time.sleep(backoff * (2 ** attempt))
            continue
        if not resp.ok:
            data = resp.json() if resp.content else {}
            msg = data.get("error", {}).get("message", resp.text)
            raise MetaAPIError(f"Meta API error {resp.status_code}: {msg}", code=resp.status_code)
        data = resp.json()
        return data.get("id", "")
    raise last_error or MetaAPIError("Max retries exceeded")


def get_post_insights(media_id: str) -> dict:
    """GET /{media_id}/insights for a published post."""
    token = _get_token()
    url = f"{META_BASE}/{META_VERSION}/{media_id}/insights"
    params = {
        "metric": "reach,impressions,likes,comments,shares,saved",
        "access_token": token,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
    except requests.RequestException as e:
        raise MetaAPIError(f"Network error: {e}")
    if resp.status_code == 401:
        raise AuthError("META_ACCESS_TOKEN invalid or expired")
    if not resp.ok:
        data = resp.json() if resp.content else {}
        # 400 with code 100 = data not yet available
        error = data.get("error", {})
        if error.get("code") == 100:
            return {"data_available": False}
        msg = error.get("message", resp.text)
        raise MetaAPIError(f"Insights error {resp.status_code}: {msg}")
    raw = resp.json().get("data", [])
    result: dict = {"data_available": True}
    for entry in raw:
        result[entry["name"]] = entry.get("values", [{}])[0].get("value", 0)
    return result


def get_token_info() -> dict:
    """Get token debug info from Meta API to check expiry.
    Returns dict with 'expires_at' (Unix timestamp), 'is_valid' (bool), 'app_id'.
    Raises AuthError if token is invalid.
    """
    token = _get_token()
    url = f"{META_BASE}/debug_token"
    params = {
        "input_token": token,
        "access_token": token,  # Self-inspect (works for user tokens)
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
    except requests.RequestException as e:
        raise MetaAPIError(f"Network error: {e}")
    if resp.status_code == 401:
        raise AuthError("META_ACCESS_TOKEN invalid or expired")
    if not resp.ok:
        raise MetaAPIError(f"Token debug error {resp.status_code}: {resp.text[:200]}")
    data = resp.json().get("data", {})
    return {
        "expires_at": data.get("expires_at"),
        "is_valid": data.get("is_valid", False),
        "app_id": data.get("app_id"),
    }
