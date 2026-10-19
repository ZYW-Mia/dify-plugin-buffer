"""Coalesce refresh requests in a Dify plugin worker without retrying consumed tokens."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from dify_plugin.entities.oauth import ToolOAuthCredentials
from dify_plugin.errors.tool import ToolProviderOAuthError
from gevent.lock import Semaphore


@dataclass
class _Refresh:
    expires_at: float
    lock: Semaphore = field(default_factory=Semaphore)
    result: ToolOAuthCredentials | None = None
    error: str | None = None


class RefreshCoordinator:
    """A short in-memory cache keyed by a token fingerprint, never the raw old token.

    This covers the daemon's concurrent greenlets. Separate processes/replicas still
    require shared coordination in the Dify credential store.
    """

    def __init__(self, ttl: int = 600, capacity: int = 512):
        self._ttl = ttl
        self._capacity = capacity
        self._states: dict[str, _Refresh] = {}
        self._lock = Semaphore()

    def run(self, fingerprint: str, exchange: Callable[[], ToolOAuthCredentials]):
        now = time.monotonic()
        with self._lock:
            self._states = {
                key: value for key, value in self._states.items() if value.expires_at > now
            }
            state = self._states.get(fingerprint)
            if state is None:
                if len(self._states) >= self._capacity:
                    raise ToolProviderOAuthError(
                        "Too many Buffer token refreshes. Try again later."
                    )
                state = _Refresh(expires_at=now + self._ttl)
                self._states[fingerprint] = state
        with state.lock:
            if state.error is not None:
                raise ToolProviderOAuthError(state.error)
            if state.result is None:
                try:
                    state.result = exchange()
                except ToolProviderOAuthError as exc:
                    # A lost response can mean Buffer has already consumed the token.
                    # Repeated callers must not retry that same token automatically.
                    state.error = str(exc)
                    raise
            return state.result.model_copy(deep=True)


refresh_coordinator = RefreshCoordinator()
