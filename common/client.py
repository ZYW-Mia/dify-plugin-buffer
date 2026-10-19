from collections.abc import Mapping
from typing import Any

import httpx

API_URL = "https://api.buffer.com"


class BufferError(Exception):
    """A safe, actionable error for Dify tool callers."""


class BufferClient:
    def __init__(self, credentials: Mapping[str, Any], *, http: httpx.Client | None = None):
        token = credentials.get("access_token") or credentials.get("api_key")
        if not isinstance(token, str) or not token.strip():
            raise BufferError("Connect Buffer through OAuth or configure a personal API key first.")
        self._token = token.strip()
        self._owns_http = http is None
        self._http = http or httpx.Client(timeout=httpx.Timeout(30, connect=10))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        if self._owns_http:
            self._http.close()

    def _safe(self, message: Any) -> str:
        return str(message).replace(self._token, "[redacted]")[:800]

    def execute(self, query: str, variables: dict | None = None) -> dict:
        # Never retry mutations: a timeout may occur after Buffer has created the post.
        try:
            response = self._http.post(
                API_URL,
                headers={"Authorization": f"Bearer {self._token}"},
                json={"query": query, "variables": variables or {}},
            )
        except httpx.TimeoutException as exc:
            raise BufferError(
                "Buffer request timed out. For writes, check list_posts before trying again; "
                "the operation may already have succeeded."
            ) from exc
        except httpx.RequestError as exc:
            raise BufferError("Unable to reach Buffer. Check your network and try again.") from exc
        if response.status_code == 401:
            raise BufferError("Buffer authorization expired or was revoked. Reconnect Buffer.")
        if response.status_code == 403:
            raise BufferError("Buffer denied access. Check the account, channel, and OAuth scopes.")
        if response.status_code == 429:
            retry = response.headers.get("Retry-After", "")
            wait = f" Wait {retry} seconds." if retry.isdigit() else " Try again later."
            raise BufferError(f"Buffer rate limit reached.{wait}")
        if not response.is_success:
            raise BufferError(
                f"Buffer returned HTTP {response.status_code}. "
                "For writes, verify the post status before retrying."
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise BufferError("Buffer returned an invalid JSON response.") from exc
        if not isinstance(payload, dict):
            raise BufferError("Buffer returned an unexpected response shape.")
        if payload.get("errors"):
            messages = []
            for error in payload["errors"]:
                if isinstance(error, dict):
                    code = (error.get("extensions") or {}).get("code", "GRAPHQL_ERROR")
                    messages.append(f"{code}: {error.get('message', 'Request failed')}")
            raise BufferError(self._safe("; ".join(messages) or "Buffer GraphQL request failed."))
        data = payload.get("data")
        if not isinstance(data, dict):
            raise BufferError("Buffer returned no result data.")
        return data

    def mutation(self, query: str, field: str, input_data: dict, success_type: str) -> dict:
        result = self.execute(query, {"input": input_data}).get(field)
        if not isinstance(result, dict):
            raise BufferError(f"Buffer returned no {field} result.")
        if result.get("__typename") != success_type:
            kind = result.get("__typename", "MutationError")
            raise BufferError(self._safe(f"{kind}: {result.get('message', 'Operation failed')}"))
        return result
