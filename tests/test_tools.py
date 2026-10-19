import json

import httpx
import pytest
from dify_plugin import DifyPluginEnv
from dify_plugin.core.plugin_registration import PluginRegistration

from common.client import BufferClient


@pytest.fixture
def plugin():
    return PluginRegistration(DifyPluginEnv())


def variables(messages):
    return {
        m.message.variable_name: m.message.variable_value
        for m in messages
        if m.type.value == "variable"
    }


def test_real_sdk_loads_provider_and_eight_tool_manifests(plugin):
    assert len(plugin.tools_mapping["buffer"][2]) == 8
    assert plugin.configuration.name == "buffer"


def test_tool_lifecycle_through_sdk_messages(plugin, monkeypatch):
    calls = []

    def handle(request):
        body = json.loads(request.content)
        calls.append(body)
        query, inputs = body["query"], body["variables"]
        post = {"id": "p1", "status": "draft", "text": "Hello"}
        if "BufferOrganizations" in query:
            data = {"account": {"organizations": [{"id": "org", "name": "Team"}]}}
        elif "BufferChannels" in query:
            assert inputs == {"input": {"organizationId": "org"}}
            data = {"channels": [{"id": "c", "service": "bluesky"}]}
        elif "BufferCreatePost" in query:
            assert inputs["input"]["channelId"] == "c"
            assert inputs["input"]["saveToDraft"] is (len(calls) == 3)
            data = {"createPost": {"__typename": "PostActionSuccess", "post": post}}
        elif "BufferEditPost" in query:
            assert inputs["input"]["id"] == "p1"
            assert inputs["input"]["saveToDraft"] is False
            assert inputs["input"]["dueAt"] == "2099-01-01T10:00:00.000Z"
            data = {"editPost": {"__typename": "PostActionSuccess", "post": post}}
        elif "BufferPosts(" in query:
            assert inputs["after"] == "page-1"
            assert inputs["input"]["filter"] == {"channelIds": ["c"], "status": ["scheduled"]}
            data = {
                "posts": {
                    "edges": [{"node": post}],
                    "pageInfo": {"hasNextPage": True, "endCursor": "page-2"},
                }
            }
        elif "BufferPost(" in query:
            assert inputs == {"input": {"id": "p1"}}
            data = {"post": post}
        else:
            assert "BufferDeletePost" in query
            assert inputs == {"input": {"id": "p1"}}
            data = {"deletePost": {"__typename": "DeletePostSuccess", "id": "p1"}}
        return httpx.Response(200, json={"data": data})

    http = httpx.Client(transport=httpx.MockTransport(handle))
    monkeypatch.setattr(
        "common.tool.BufferClient", lambda credentials: BufferClient(credentials, http=http)
    )

    def run(name, params):
        tool = plugin.get_tool_cls("buffer", name).from_credentials({"api_key": "secret"})
        result = list(tool._invoke(params))
        assert result[0].type.value == "json"
        output = variables(result)
        declared = plugin.tools_mapping["buffer"][2][name][0].output_schema["properties"]
        assert set(output) == set(declared)
        return output

    assert run("list_organizations", {})["organizations"][0]["id"] == "org"
    assert run("list_channels", {"organization_id": "org"})["channels"][0]["id"] == "c"
    assert run("create_post", {"channel_id": "c", "text": "Hello"})["post_id"] == "p1"
    run(
        "update_post",
        {"post_id": "p1", "mode": "customScheduled", "due_at": "2099-01-01T18:00:00+08:00"},
    )
    run("get_post", {"post_id": "p1"})
    page = run(
        "list_posts",
        {
            "organization_id": "org",
            "channel_ids_json": '["c"]',
            "status": "scheduled",
            "after": "page-1",
        },
    )
    assert page["has_next_page"] is True
    assert page["end_cursor"] == "page-2"
    run("schedule_post", {"channel_id": "c", "text": "Hello", "mode": "addToQueue"})
    assert run("delete_post", {"post_id": "p1"}) == {"post_id": "p1", "deleted": True}
    assert len(calls) == 8


def test_invalid_schedule_does_not_make_network_request(plugin, monkeypatch):
    monkeypatch.setattr("common.tool.BufferClient", lambda *a, **kw: pytest.fail("network"))
    tool = plugin.get_tool_cls("buffer", "schedule_post").from_credentials({"api_key": "secret"})
    with pytest.raises(RuntimeError, match="timezone"):
        list(tool._invoke({"channel_id": "c", "text": "Hello", "due_at": "2099-01-01T10:00"}))


def test_mutation_errors_propagate_to_workflow_failure(plugin, monkeypatch):
    http = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "data": {
                        "deletePost": {"__typename": "InvalidInputError", "message": "Invalid"}
                    }
                },
            )
        )
    )
    monkeypatch.setattr(
        "common.tool.BufferClient", lambda credentials: BufferClient(credentials, http=http)
    )
    tool = plugin.get_tool_cls("buffer", "delete_post").from_credentials({"api_key": "secret"})
    with pytest.raises(RuntimeError, match="Invalid"):
        list(tool._invoke({"post_id": "p1"}))
