import base64
import hashlib
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
import pytest
from dify_plugin.errors.tool import ToolProviderOAuthError
from werkzeug import Request

from provider.buffer import AUTH_URL, SCOPES, TOKEN_URL, BufferProvider

CLIENT = {"client_id": "client-id", "client_secret": "server-side-secret"}
REDIRECT = "https://dify.example/console/api/oauth/plugin/tenten/buffer/buffer/tool/callback"


@pytest.fixture(autouse=True)
def fresh_refresh_coordinator(monkeypatch):
    from common.oauth import RefreshCoordinator

    monkeypatch.setattr("provider.buffer.refresh_coordinator", RefreshCoordinator())


def start(provider=None):
    url = (provider or BufferProvider())._oauth_get_authorization_url(REDIRECT, CLIENT)
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


def callback(params):
    return Request.from_values(query_string=urlencode(params))


def tokens(**overrides):
    return {
        "access_token": "access",
        "refresh_token": "new-refresh",
        "expires_in": 3600,
        **overrides,
    }


def test_authorization_url_requests_minimal_scopes_and_s256():
    provider = BufferProvider()
    url = provider._oauth_get_authorization_url(REDIRECT, CLIENT)
    params = start(provider)
    assert url.startswith(AUTH_URL + "?")
    assert params["scope"] == SCOPES
    assert set(SCOPES.split()) == {"account:read", "posts:read", "posts:write", "offline_access"}
    assert params["code_challenge_method"] == "S256"
    assert params["redirect_uri"] == REDIRECT
    assert "server-side-secret" not in url
    assert "code_verifier" not in params


def test_pkce_survives_different_provider_workers(monkeypatch):
    params = start()
    sent = []

    def exchange(url, *, data, timeout):
        assert url == TOKEN_URL
        assert timeout == 30
        sent.append(data)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(data["code_verifier"].encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        assert challenge == params["code_challenge"]
        assert 43 <= len(data["code_verifier"]) <= 128
        assert data["redirect_uri"] == REDIRECT
        assert data["client_secret"] == CLIENT["client_secret"]
        return httpx.Response(200, json=tokens())

    monkeypatch.setattr("provider.buffer.httpx.post", exchange)
    result = BufferProvider()._oauth_get_credentials(
        REDIRECT, CLIENT, callback({"state": params["state"], "code": "code"})
    )
    assert result.credentials == {"access_token": "access", "refresh_token": "new-refresh"}
    assert "client_secret" not in result.credentials
    assert len(sent) == 1


def test_parallel_authorizations_have_different_challenges():
    first, second = start(), start()
    assert first["state"] != second["state"]
    assert first["code_challenge"] != second["code_challenge"]


@pytest.mark.parametrize("tamper", ["missing", "signature", "redirect", "client", "expired"])
def test_invalid_state_is_rejected_before_token_request(monkeypatch, tamper):
    monkeypatch.setattr("provider.buffer.time.time", lambda: 1_800_000_000)
    params = start()
    state = params["state"]
    redirect, client = REDIRECT, CLIENT
    if tamper == "missing":
        state = ""
    elif tamper == "signature":
        state = state[:-1] + ("A" if state[-1] != "A" else "B")
    elif tamper == "redirect":
        redirect += "/other"
    elif tamper == "client":
        client = {**CLIENT, "client_id": "other"}
    else:
        monkeypatch.setattr("provider.buffer.time.time", lambda: 1_800_000_601)
    monkeypatch.setattr("provider.buffer.httpx.post", lambda *a, **kw: pytest.fail("token request"))
    with pytest.raises(ToolProviderOAuthError, match="state"):
        BufferProvider()._oauth_get_credentials(
            redirect, client, callback({"state": state, "code": "code"})
        )


def test_denied_authorization_is_reported(monkeypatch):
    params = start()
    with pytest.raises(ToolProviderOAuthError, match="denied"):
        BufferProvider()._oauth_get_credentials(
            REDIRECT, CLIENT, callback({"state": params["state"], "error": "access_denied"})
        )


def test_refresh_saves_rotated_token_and_absolute_expiry(monkeypatch):
    monkeypatch.setattr("provider.buffer.time.time", lambda: 1_800_000_000)

    def refresh(url, *, data, timeout):
        assert data["grant_type"] == "refresh_token"
        assert data["refresh_token"] == "old-refresh"
        return httpx.Response(200, json=tokens())

    monkeypatch.setattr("provider.buffer.httpx.post", refresh)
    result = BufferProvider()._oauth_refresh_credentials(
        REDIRECT, CLIENT, {"refresh_token": "old-refresh"}
    )
    assert result.credentials["refresh_token"] == "new-refresh"
    assert result.expires_at == 1_800_003_540


@pytest.mark.parametrize(
    "data",
    [
        tokens(refresh_token=None),
        tokens(expires_in=None),
        tokens(access_token=""),
        tokens(expires_in=0),
    ],
)
def test_incomplete_tokens_are_rejected(monkeypatch, data):
    monkeypatch.setattr(
        "provider.buffer.httpx.post", lambda *a, **kw: httpx.Response(200, json=data)
    )
    with pytest.raises(ToolProviderOAuthError, match="incomplete"):
        BufferProvider()._oauth_refresh_credentials(REDIRECT, CLIENT, {"refresh_token": "old"})


def test_token_error_does_not_expose_secrets(monkeypatch):
    monkeypatch.setattr(
        "provider.buffer.httpx.post",
        lambda *a, **kw: httpx.Response(
            400, text="client_secret=server-side-secret refresh_token=old"
        ),
    )
    with pytest.raises(ToolProviderOAuthError) as error:
        BufferProvider()._oauth_refresh_credentials(REDIRECT, CLIENT, {"refresh_token": "old"})
    assert "server-side-secret" not in str(error.value)
    assert "refresh_token=old" not in str(error.value)
