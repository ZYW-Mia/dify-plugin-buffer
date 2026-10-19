import json
import math
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

POST_STATUSES = {"draft", "scheduled", "sent", "error", "sending", "needs_approval"}
MODES = {"draft", "addToQueue", "customScheduled", "shareNext", "shareNow"}


def required_string(params: dict, name: str) -> str:
    value = params.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required.")
    return value.strip()


def choice(params: dict, name: str, allowed: set[str], default: str) -> str:
    value = params.get(name) or default
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{name} must be one of: {', '.join(sorted(allowed))}.")
    return value


def boolean(params: dict, name: str, default: bool = False) -> bool:
    value = params.get(name)
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise ValueError(f"{name} must be true or false.")


def json_value(value: Any, expected: type, name: str):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError as exc:
            raise ValueError(f"{name} must contain valid JSON.") from exc
    if not isinstance(value, expected):
        raise ValueError(f"{name} must be a JSON {expected.__name__}.")
    return value


def utc_time(value: Any, name: str, *, future: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an ISO 8601 timestamp with a timezone.")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO 8601 timestamp with a timezone.") from exc
    if parsed.utcoffset() is None:
        raise ValueError(f"{name} requires a timezone, e.g. 2026-11-01T18:00:00+08:00.")
    parsed = parsed.astimezone(UTC)
    if future and parsed <= datetime.now(UTC):
        raise ValueError(f"{name} must be in the future.")
    return parsed.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def page_size(value: Any) -> int:
    try:
        number = float(value if value is not None and value != "" else 20)
    except (TypeError, ValueError) as exc:
        raise ValueError("first must be an integer between 1 and 100.") from exc
    if isinstance(value, bool) or not math.isfinite(number) or not number.is_integer():
        raise ValueError("first must be an integer between 1 and 100.")
    if not 1 <= number <= 100:
        raise ValueError("first must be an integer between 1 and 100.")
    return int(number)


def string_list(value: Any, name: str) -> list[str]:
    result = json_value(value, list, name)
    if not all(isinstance(item, str) and item.strip() for item in result):
        raise ValueError(f"{name} must be a JSON array of non-empty strings.")
    return [item.strip() for item in result]


def _url(value: Any, name: str) -> None:
    try:
        parsed = urlsplit(value) if isinstance(value, str) else None
        if not parsed or parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise ValueError
        if parsed.username or parsed.password:
            raise ValueError
    except ValueError as exc:
        raise ValueError(f"{name} must be a public HTTP(S) URL without credentials.") from exc


def assets(value: Any) -> list[dict]:
    result = json_value(value, list, "assets_json")
    for item in result:
        if not isinstance(item, dict) or len(item) != 1:
            raise ValueError("Each asset must contain exactly one image, video, or document.")
        kind = next(iter(item))
        if kind not in {"image", "video", "document"} or not isinstance(item[kind], dict):
            raise ValueError("Supported asset types: image, video, document.")
        data = item[kind]
        _url(data.get("url"), "Asset URL")
        if kind == "video" and "thumbnailUrl" in data:
            raise ValueError("Video thumbnails must use metadata.thumbnailOffset.")
        if "thumbnailUrl" in data:
            _url(data["thumbnailUrl"], "Thumbnail URL")
        if kind == "document":
            if not data.get("title") or not data.get("thumbnailUrl"):
                raise ValueError("Documents require title, url, and thumbnailUrl.")
    return result


def post_input(params: dict, *, editing: bool = False, scheduling: bool = False) -> dict:
    result = {}
    if editing:
        result["id"] = required_string(params, "post_id")
    else:
        result["channelId"] = required_string(params, "channel_id")
        result.update(assets=[], needsApproval=False)

    allowed = MODES | {"keep"} if editing else MODES
    if scheduling:
        allowed = {"addToQueue", "customScheduled", "shareNext"}
    default = "keep" if editing else "customScheduled" if scheduling else "draft"
    mode = choice(params, "mode", allowed, default)
    if mode != "keep":
        result["mode"] = "addToQueue" if mode == "draft" else mode
        result["saveToDraft"] = mode == "draft"
        result["schedulingType"] = choice(
            params, "scheduling_type", {"automatic", "notification"}, "automatic"
        )
    elif params.get("scheduling_type"):
        result["schedulingType"] = choice(
            params, "scheduling_type", {"automatic", "notification"}, "automatic"
        )

    due_at = params.get("due_at")
    if mode == "customScheduled":
        result["dueAt"] = utc_time(due_at, "due_at", future=True)
    elif due_at:
        raise ValueError("Set mode=customScheduled when providing due_at.")

    text = params.get("text")
    if text is not None and text != "":
        if not isinstance(text, str):
            raise ValueError("text must be a string.")
        result["text"] = text
    elif editing and boolean(params, "clear_text"):
        result["text"] = ""

    for param, field, parser in (
        ("assets_json", "assets", assets),
        ("metadata_json", "metadata", lambda v: json_value(v, dict, "metadata_json")),
        ("tag_ids_json", "tagIds", lambda v: string_list(v, "tag_ids_json")),
    ):
        if params.get(param) not in (None, ""):
            result[field] = parser(params[param])
    if not editing and not str(result.get("text", "")).strip() and not result["assets"]:
        raise ValueError("Provide non-empty text or at least one media asset.")
    if params.get("ai_assisted") not in (None, ""):
        result["aiAssisted"] = boolean(params, "ai_assisted")
    if not editing:
        result["source"] = "dify"
    if editing and len(result) == 1:
        raise ValueError("Provide text, assets, metadata, tags, or a scheduling change to update.")
    return result
