"""Structured JSONL event logger."""
from __future__ import annotations
import json
import os
import datetime
from pathlib import Path


_LOG_PATH = Path(".instagram/memory/logs/events.jsonl")


def append_event(
    skill: str,
    item_id: str | None,
    plan_week: str | None,
    event_type: str,
    outcome: str,
    **kwargs,
) -> None:
    """Append a structured event to the JSONL event log."""
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "skill": skill,
        "item_id": item_id,
        "plan_week": plan_week,
        "event_type": event_type,
        "outcome": outcome,
        **kwargs,
    }
    with open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
