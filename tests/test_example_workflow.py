"""Behavioral checks for a single-generation, single-review Buffer workflow."""

import json
import re
from pathlib import Path
from uuid import UUID

import pytest
import yaml

from common.inputs import post_input


@pytest.fixture
def workflow():
    return yaml.safe_load(
        (Path(__file__).parents[1] / "examples/buffer-social-copilot.yml").read_text()
    )["workflow"]["graph"]


def function(workflow, node_id):
    data = next(node["data"] for node in workflow["nodes"] if node["id"] == node_id)
    namespace = {}
    exec(compile(data["code"], node_id, "exec"), namespace)
    return namespace["main"]


def account_choices(workflow):
    return function(workflow, "accounts")(
        [
            {
                "channels": [
                    {
                        "id": "x-1",
                        "name": "Dify",
                        "service": "twitter",
                        "organizationId": "team-1",
                        "timezone": "Asia/Singapore",
                    },
                    {
                        "id": "linkedin-1",
                        "name": "Dify",
                        "service": "linkedin",
                        "organizationId": "team-1",
                        "timezone": "America/New_York",
                    },
                    {
                        "id": "instagram-1",
                        "name": "Dify",
                        "service": "instagram",
                        "organizationId": "team-1",
                    },
                    {
                        "id": "disconnected",
                        "service": "twitter",
                        "organizationId": "team-1",
                        "isDisconnected": True,
                    },
                    {
                        "id": "locked",
                        "service": "twitter",
                        "organizationId": "team-1",
                        "isLocked": True,
                    },
                    {"id": "unknown-workspace", "service": "twitter", "organizationId": "unknown"},
                ]
            },
            [
                {
                    "channels": [
                        {"id": "x-2", "name": "Dify", "service": "x", "organizationId": "team-2"},
                        {
                            "id": "bluesky-1",
                            "name": "Dify",
                            "service": "bluesky",
                            "organizationId": "team-2",
                        },
                    ]
                }
            ],
        ],
        {"team-1": "Dify", "team-2": "Dify"},
    )


def approve(
    workflow,
    method="Save Draft",
    scheduled="",
    text="Dify content.",
    account_id="x-1",
    content_mode="AI Assistant",
    images=None,
):
    choices = account_choices(workflow)
    label = next(k for k, v in choices["account_map"].items() if v["id"] == account_id)
    return function(workflow, "approved")(
        label, text, method, scheduled, choices["account_map"], content_mode, images or []
    )


def test_one_model_and_one_human_review_keep_the_workflow_short(workflow):
    nodes = {n["id"]: n["data"] for n in workflow["nodes"]}
    assert sum(n["type"] == "llm" for n in nodes.values()) == 1
    assert sum(n["type"] == "human-input" for n in nodes.values()) == 1
    assert len([n for n in workflow["nodes"] if n["type"] != "custom-note"]) == 16
    routes = {
        e["sourceHandle"]: e["target"] for e in workflow["edges"] if e["source"] == "content_route"
    }
    assert routes == {"true": "merge", "false": "write"}
    assert nodes["merge"]["variables"] == [["write", "text"], ["start", "source_material"]]
    assert nodes["merge"]["output_type"] == "string"


def test_character_target_is_user_input_and_not_a_hard_platform_cap(workflow):
    nodes = {n["id"]: n["data"] for n in workflow["nodes"]}
    fields = {f["variable"]: f for f in nodes["start"]["variables"]}
    assert fields["max_characters"]["type"] == "number"
    assert fields["max_characters"]["default"] == ""
    assert fields["max_characters"]["label"] == "Maximum characters"
    assert fields["max_characters"]["required"] is False
    assert "limit_enabled" not in fields
    assert not {"platform", "organization_id", "channel_id", "tone"}.intersection(fields)
    prompt = "\n".join(p["text"] for p in nodes["write"]["prompt_template"])
    assert "{{#start.max_characters#}}" in prompt
    assert "limit_enabled" not in prompt
    assert "If it is 0, blank, or omitted, there is no preset character limit" in prompt
    assert "Return only the content text" in prompt
    assert "character_limit" not in nodes["approved"]["code"]
    for purpose in fields["purpose"]["options"]:
        assert purpose + ":" in prompt


def test_connected_account_choices_have_readable_names_and_timezones(workflow):
    result = account_choices(workflow)
    assert {a["id"] for a in result["account_map"].values()} == {
        "x-1",
        "x-2",
        "linkedin-1",
        "bluesky-1",
    }
    assert len(set(result["account_options"])) == 4
    assert "Instagram" in result["connected_accounts_report"]
    assert "Asia/Singapore" in result["connected_accounts_report"]
    assert not any(s.startswith("Instagram") for s in result["account_options"])
    assert all("x-1" not in s and "team-1" not in s for s in result["account_options"])


@pytest.mark.parametrize(
    "method,mode",
    [("Save Draft", "draft"), ("Add to Queue", "addToQueue"), ("Publish Now", "shareNow")],
)
@pytest.mark.parametrize("scheduled", ["", "not a date", "2000-01-01 09:00"])
def test_non_scheduled_methods_never_require_or_use_publish_time(workflow, method, mode, scheduled):
    result = approve(workflow, method, scheduled)
    assert result["mode"] == mode
    assert result["due_at"] == ""


@pytest.mark.parametrize("text", ["x" * 121, "x" * 280, "x" * 1000, "发布 Dify 内容 🚀" * 30])
def test_human_text_is_never_rejected_by_an_artificial_template_budget(workflow, text):
    result = approve(workflow, "Publish Now", text=text)
    assert result["approved_text"] == text
    payload = post_input(
        {
            "channel_id": result["channel_id"],
            "text": result["approved_text"],
            "mode": result["mode"],
            "due_at": result["due_at"],
        }
    )
    assert payload["text"] == text
    assert payload["mode"] == "shareNow"
    assert not payload.get("dueAt")


def test_original_content_preserves_whitespace_and_is_not_marked_ai(workflow):
    text = "  Original Dify content.\n\nKeep this wording.  "
    result = approve(workflow, text=text, content_mode="Original Content")
    assert result["approved_text"] == text
    assert result["ai_assisted"] is False


def test_schedule_uses_account_timezone_and_media_form_a_valid_buffer_payload(workflow):
    result = approve(
        workflow,
        "Schedule",
        "2035-01-02 09:30",
        images=[{"type": "image", "url": "https://files.example.com/post.png?sign=test"}],
    )
    assert result["due_at"] == "2035-01-02T01:30:00.000Z"
    assert result["image_count"] == 1
    payload = post_input(
        {
            "channel_id": result["channel_id"],
            "text": result["approved_text"],
            "mode": result["mode"],
            "due_at": result["due_at"],
            "assets_json": result["assets_json"],
        }
    )
    assert payload["dueAt"] == result["due_at"]
    assert payload["assets"][0]["image"]["url"].startswith("https:")
    assert json.loads(result["assets_json"])[0]["image"]["url"].endswith("sign=test")


def test_schedule_explicit_offset_overrides_account_timezone(workflow):
    result = approve(workflow, "Schedule", "2035-01-02T09:30:00+09:00")
    assert result["due_at"] == "2035-01-02T00:30:00.000Z"


@pytest.mark.parametrize("scheduled", ["", "not a date", "2000-01-01 09:00"])
def test_schedule_requires_a_valid_future_time(workflow, scheduled):
    with pytest.raises(ValueError):
        approve(workflow, "Schedule", scheduled)


@pytest.mark.parametrize("scheduled", ["2027-03-14 02:30", "2027-11-07 01:30"])
def test_dst_gap_and_ambiguity_require_an_unambiguous_timestamp(workflow, scheduled):
    with pytest.raises(ValueError):
        approve(workflow, "Schedule", scheduled, account_id="linkedin-1")


@pytest.mark.parametrize("text", ["", "  \n"])
def test_empty_content_is_still_rejected(workflow, text):
    with pytest.raises(ValueError):
        approve(workflow, text=text)


def test_only_confirmation_can_reach_buffer_and_write_retries_are_off(workflow):
    nodes = {n["id"]: n["data"] for n in workflow["nodes"]}
    routes = {e["sourceHandle"]: e["target"] for e in workflow["edges"] if e["source"] == "review"}
    assert routes == {"confirm_send": "approved", "cancel": "cancelled", "__timeout": "expired"}
    assert nodes["review"]["inputs"][0]["default"]["selector"] == ["merge", "output"]
    assert nodes["review"]["inputs"][1]["option_source"]["selector"] == [
        "accounts",
        "account_options",
    ]
    assert "Leave blank for other methods." in nodes["review"]["form_content"]
    for method in nodes["review"]["delivery_methods"]:
        UUID(method["id"])
    params = nodes["draft"]["tool_parameters"]
    assert params["text"]["value"] == ["approved", "approved_text"]
    assert params["mode"]["value"] == ["approved", "mode"]
    assert params["due_at"]["value"] == ["approved", "due_at"]
    assert not nodes["draft"]["retry_config"]["retry_enabled"]


def test_all_code_nodes_have_languages_and_no_deleted_node_references(workflow):
    ids = {n["id"] for n in workflow["nodes"]}
    output_names = [
        field["variable"]
        for node in workflow["nodes"]
        if node["data"]["type"] == "end"
        for field in node["data"]["outputs"]
    ]
    assert len(output_names) == len(set(output_names))
    for node in workflow["nodes"]:
        data = node["data"]
        if data["type"] == "code":
            assert data["code_language"] == "python3"
            compile(data["code"], node["id"], "exec")
        for source_id in re.findall(r"\{\{#([^.$][^.]*?)\.", json.dumps(data)):
            assert source_id in ids or source_id == "sys"
        for field in data.get("variables", []):
            if isinstance(field, dict) and field.get("value_selector"):
                assert field["value_selector"][0] in ids
    for edge in workflow["edges"]:
        assert edge["source"] in ids and edge["target"] in ids
