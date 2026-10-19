from datetime import UTC, datetime, timedelta

import pytest

from common.inputs import assets, page_size, post_input, utc_time


def future():
    return (datetime.now(UTC) + timedelta(days=30)).isoformat()


def test_draft_is_the_default():
    result = post_input({"channel_id": "channel", "text": "Hello"})
    assert result == {
        "channelId": "channel",
        "text": "Hello",
        "mode": "addToQueue",
        "saveToDraft": True,
        "schedulingType": "automatic",
        "needsApproval": False,
        "assets": [],
        "source": "dify",
    }


def test_timezone_is_converted_to_utc():
    assert utc_time("2030-11-01T18:00:00+08:00", "due_at") == "2030-11-01T10:00:00.000Z"


@pytest.mark.parametrize("value", [None, "tomorrow", "2030-11-01T18:00:00", ""])
def test_ambiguous_dates_are_rejected(value):
    with pytest.raises(ValueError):
        utc_time(value, "due_at")


def test_schedule_requires_a_future_date():
    with pytest.raises(ValueError, match="future"):
        post_input(
            {"channel_id": "c", "text": "Hello", "due_at": "2000-01-01T00:00:00Z"},
            scheduling=True,
        )


def test_schedule_can_use_the_queue_without_a_date():
    result = post_input({"channel_id": "c", "text": "Hello", "mode": "addToQueue"}, scheduling=True)
    assert result["saveToDraft"] is False
    assert "dueAt" not in result


def test_schedule_new_post_maps_custom_date():
    result = post_input({"channel_id": "c", "text": "Hello", "due_at": future()}, scheduling=True)
    assert result["mode"] == "customScheduled"
    assert result["dueAt"].endswith("Z")


def test_edit_preserves_schedule_assets_and_tags_by_omission():
    assert post_input({"post_id": "p", "text": "Edited"}, editing=True) == {
        "id": "p",
        "text": "Edited",
    }


def test_edit_can_schedule_existing_draft():
    result = post_input(
        {"post_id": "draft", "mode": "customScheduled", "due_at": future()}, editing=True
    )
    assert result["id"] == "draft"
    assert result["saveToDraft"] is False
    assert "channelId" not in result


def test_edit_can_explicitly_clear_fields():
    assert post_input(
        {"post_id": "p", "clear_text": True, "assets_json": "[]", "tag_ids_json": "[]"},
        editing=True,
    ) == {"id": "p", "text": "", "assets": [], "tagIds": []}


def test_empty_edit_is_rejected():
    with pytest.raises(ValueError, match="Provide"):
        post_input({"post_id": "p", "text": "", "mode": "keep"}, editing=True)


@pytest.mark.parametrize("mode", ["shareNow", "draft"])
def test_schedule_tool_does_not_accept_draft_or_publish_now(mode):
    with pytest.raises(ValueError):
        post_input({"channel_id": "c", "text": "Hello", "mode": mode}, scheduling=True)


def test_media_only_post_and_platform_metadata():
    result = post_input(
        {
            "channel_id": "c",
            "assets_json": '[{"image":{"url":"https://example.com/image.png"}}]',
            "metadata_json": '{"instagram":{"type":"post","shouldShareToFeed":true}}',
        }
    )
    assert result["assets"][0]["image"]["url"].endswith("image.png")
    assert result["metadata"] == {"instagram": {"type": "post", "shouldShareToFeed": True}}


@pytest.mark.parametrize(
    "value",
    [
        "not json",
        "{}",
        '[{"link":{}}]',
        '[{"image":{"url":"file:///tmp/x"}}]',
        '[{"image":{"url":"https://user:password@example.com/x"}}]',
        '[{"image":{},"video":{}}]',
        '[{"video":{"url":"https://x/v","thumbnailUrl":"https://x/t"}}]',
    ],
)
def test_invalid_assets_are_rejected(value):
    with pytest.raises(ValueError):
        assets(value)


@pytest.mark.parametrize("value", [0, 101, 1.5, True, "nan", "inf", "ten"])
def test_invalid_page_sizes_are_rejected(value):
    with pytest.raises(ValueError):
        page_size(value)


def test_page_size_accepts_dify_number_values():
    assert page_size(20.0) == 20
    assert page_size("100") == 100


def test_date_cannot_silently_override_mode():
    with pytest.raises(ValueError, match="customScheduled"):
        post_input({"channel_id": "c", "text": "Hello", "due_at": future()})
