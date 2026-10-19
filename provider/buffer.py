import base64
import hashlib
import hmac
import re
import secrets
import time
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode

import httpx
from dify_plugin import ToolProvider
from dify_plugin.entities.oauth import ToolOAuthCredentials
from dify_plugin.errors.tool import ToolProviderCredentialValidationError, ToolProviderOAuthError
from werkzeug import Request

from common.client import BufferClient, BufferError
from common.oauth import refresh_coordinator
from common.queries import ACCOUNT

AUTH_URL = "https://auth.buffer.com/auth"
TOKEN_URL = "https://auth.buffer.com/token"
SCOPES = "account:read posts:read posts:write offline_access"
STATE_LIFETIME = 600


def _base64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _client(credentials: Mapping[str, Any]) -> tuple[str, str]:
    values = []
    for key in ("client_id", "client_secret"):
        value = credentials.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ToolProviderOAuthError(f"Configure the Buffer private app {key} first.")
        values.append(value.strip())
    return values[0], values[1]


def _digest(secret: str, purpose: str, *parts: str) -> str:
    # Length-delimited components avoid ambiguous concatenation.
    data = "".join(f"{len(p)}:{p}" for p in (purpose, *parts))
    return _base64(hmac.digest(secret.encode(), data.encode(), "sha256"))


class BufferProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict) -> None:
        try:
            with BufferClient(credentials) as client:
                client.execute(ACCOUNT)
        except BufferError as exc:
            raise ToolProviderCredentialValidationError(str(exc)) from exc

    def _oauth_get_authorization_url(
        self, redirect_uri: str, system_credentials: Mapping[str, Any]
    ) -> str:
        client_id, secret = _client(system_credentials)
        stamp, nonce = str(int(time.time())), secrets.token_urlsafe(32)
        signature = _digest(secret, "state", client_id, redirect_uri, stamp, nonce)
        state = f"{stamp}.{nonce}.{signature}"
        # ToolProvider has no persistent session API. Derive the secret verifier with
        # HMAC so any plugin worker can finish the flow; only its S256 hash is exposed.
        # Dify owns the HttpOnly context cookie and single-use callback context.
        verifier = _digest(secret, "pkce", client_id, redirect_uri, state)
        challenge = _base64(hashlib.sha256(verifier.encode()).digest())
        return f"{AUTH_URL}?{
            urlencode(
                {
                    'client_id': client_id,
                    'redirect_uri': redirect_uri,
                    'response_type': 'code',
                    'scope': SCOPES,
                    'state': state,
                    'code_challenge': challenge,
                    'code_challenge_method': 'S256',
                    'prompt': 'consent',
                }
            )
        }"

    def _oauth_get_credentials(
        self, redirect_uri: str, system_credentials: Mapping[str, Any], request: Request
    ) -> ToolOAuthCredentials:
        client_id, secret = _client(system_credentials)
        state = request.args.get("state", "")
        if not re.fullmatch(r"[0-9]{1,12}\.[A-Za-z0-9_-]{43}\.[A-Za-z0-9_-]{43}", state):
            raise ToolProviderOAuthError("Invalid OAuth state. Start the connection again.")
        stamp, nonce, signature = state.split(".")
        expected = _digest(secret, "state", client_id, redirect_uri, stamp, nonce)
        age = time.time() - int(stamp)
        if not hmac.compare_digest(signature, expected) or not -30 <= age <= STATE_LIFETIME:
            raise ToolProviderOAuthError("Invalid or expired OAuth state. Connect Buffer again.")
        if request.args.get("error"):
            raise ToolProviderOAuthError(
                "Buffer authorization was denied or could not be completed."
            )
        code = request.args.get("code")
        if not code:
            raise ToolProviderOAuthError("Buffer returned no authorization code.")
        return self._tokens(
            {
                "client_id": client_id,
                "client_secret": secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": _digest(secret, "pkce", client_id, redirect_uri, state),
            }
        )

    def _oauth_refresh_credentials(
        self,
        redirect_uri: str,
        system_credentials: Mapping[str, Any],
        credentials: Mapping[str, Any],
    ) -> ToolOAuthCredentials:
        client_id, secret = _client(system_credentials)
        refresh_token = credentials.get("refresh_token")
        if not isinstance(refresh_token, str) or not refresh_token:
            raise ToolProviderOAuthError("No refresh token available. Connect Buffer again.")
        # Coalesce same-token refreshes within a worker. Dify must persist the new
        # pair and coordinate across separate worker processes or replicas.
        fingerprint = _digest(secret, "refresh-cache", client_id, refresh_token)
        return refresh_coordinator.run(
            fingerprint,
            lambda: self._tokens(
                {
                    "client_id": client_id,
                    "client_secret": secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                }
            ),
        )

    @staticmethod
    def _tokens(data: dict) -> ToolOAuthCredentials:
        try:
            response = httpx.post(TOKEN_URL, data=data, timeout=30)
        except httpx.RequestError as exc:
            raise ToolProviderOAuthError(
                "Buffer token request failed. Connect Buffer again if a refresh was interrupted."
            ) from exc
        if not response.is_success:
            # Never echo the token endpoint body, request, or secret.
            raise ToolProviderOAuthError(
                f"Buffer token request returned HTTP {response.status_code}. Connect Buffer again."
            )
        try:
            tokens = response.json()
            if not isinstance(tokens, dict) or tokens.get("error"):
                raise ValueError
            access = tokens.get("access_token")
            refresh = tokens.get("refresh_token")
            if not isinstance(access, str) or not access:
                raise ValueError
            if not isinstance(refresh, str) or not refresh:
                raise ValueError
            lifetime = int(tokens["expires_in"])
            if lifetime <= 0:
                raise ValueError
        except (ValueError, TypeError, KeyError) as exc:
            raise ToolProviderOAuthError(
                "Buffer returned incomplete OAuth tokens. Check offline_access and reconnect."
            ) from exc
        return ToolOAuthCredentials(
            credentials={"access_token": access, "refresh_token": refresh},
            expires_at=int(time.time()) + lifetime - min(60, lifetime // 10),
        )
