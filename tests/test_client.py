import json

import httpx
import pytest

from common.client import API_URL, BufferClient, BufferError
from common.queries import CREATE_POST


def with_response(response):
    return httpx.Client(transport=httpx.MockTransport(lambda request: response))


def test_variables_are_not_interpolated_and_bearer_token_is_used():
    text = 'Quotes " and newlines\n中文 } mutation { deletePost }'

    def handle(request):
        assert str(request.url) == API_URL
        assert request.headers["Authorization"] == "Bearer secret"
        body = json.loads(request.content)
        assert body["variables"]["input"]["text"] == text
        assert text not in body["query"]
        return httpx.Response(200, json={"data": {"ok": True}})

    http = httpx.Client(transport=httpx.MockTransport(handle))
    assert BufferClient({"api_key": "secret"}, http=http).execute(
        CREATE_POST, {"input": {"text": text}}
    ) == {"ok": True}


@pytest.mark.parametrize("status,match", [(401, "Reconnect"), (403, "scopes"), (500, "HTTP 500")])
def test_http_errors_are_actionable(status, match):
    client = BufferClient({"access_token": "secret"}, http=with_response(httpx.Response(status)))
    with pytest.raises(BufferError, match=match):
        client.execute("query { account { id } }")


def test_rate_limit_exposes_retry_after():
    http = with_response(httpx.Response(429, headers={"Retry-After": "45"}))
    with pytest.raises(BufferError, match="Wait 45 seconds"):
        BufferClient({"api_key": "secret"}, http=http).execute("query { x }")


def test_graphql_errors_with_http_200_are_failures_and_secrets_are_redacted():
    http = with_response(
        httpx.Response(
            200,
            json={
                "data": {"partial": True},
                "errors": [
                    {"message": "token secret expired", "extensions": {"code": "UNAUTHORIZED"}}
                ],
            },
        )
    )
    with pytest.raises(BufferError, match="UNAUTHORIZED") as error:
        BufferClient({"api_key": "secret"}, http=http).execute("query { x }")
    assert "secret" not in str(error.value)


def test_typed_mutation_error_is_a_failure():
    http = with_response(
        httpx.Response(
            200,
            json={
                "data": {
                    "createPost": {
                        "__typename": "InvalidInputError",
                        "message": "Text too long",
                    }
                }
            },
        )
    )
    with pytest.raises(BufferError, match="Text too long"):
        BufferClient({"api_key": "secret"}, http=http).mutation(
            CREATE_POST, "createPost", {}, "PostActionSuccess"
        )


@pytest.mark.parametrize("payload", [[], {"data": None}, {}])
def test_invalid_result_shapes_are_failures(payload):
    with pytest.raises(BufferError):
        BufferClient(
            {"api_key": "secret"}, http=with_response(httpx.Response(200, json=payload))
        ).execute("query { x }")


def test_html_success_response_is_not_json():
    with pytest.raises(BufferError, match="JSON"):
        BufferClient(
            {"api_key": "secret"},
            http=with_response(httpx.Response(200, text="<html>proxy</html>")),
        ).execute("query { x }")


def test_ambiguous_timeout_is_never_retried():
    requests = []

    def timeout(request):
        requests.append(request)
        raise httpx.ReadTimeout("timeout", request=request)

    client = BufferClient(
        {"api_key": "secret"}, http=httpx.Client(transport=httpx.MockTransport(timeout))
    )
    with pytest.raises(BufferError, match="may already have succeeded"):
        client.mutation(CREATE_POST, "createPost", {}, "PostActionSuccess")
    assert len(requests) == 1
