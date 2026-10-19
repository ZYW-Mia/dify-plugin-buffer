import gevent
import pytest
from dify_plugin.entities.oauth import ToolOAuthCredentials
from dify_plugin.errors.tool import ToolProviderOAuthError

from common.oauth import RefreshCoordinator


def credentials():
    return ToolOAuthCredentials(
        credentials={"access_token": "access", "refresh_token": "rotated"}, expires_at=2000000000
    )


def test_simultaneous_refreshes_consume_old_token_only_once():
    coordinator = RefreshCoordinator()
    calls = []

    def exchange():
        calls.append(True)
        gevent.sleep(0.01)
        return credentials()

    tasks = [gevent.spawn(coordinator.run, "fingerprint", exchange) for _ in range(5)]
    gevent.joinall(tasks, raise_error=True)
    assert len(calls) == 1
    assert all(task.value.credentials["refresh_token"] == "rotated" for task in tasks)
    tasks[0].value.credentials["refresh_token"] = "changed"
    assert tasks[1].value.credentials["refresh_token"] == "rotated"


def test_interrupted_refresh_is_not_retried_with_the_same_token():
    coordinator = RefreshCoordinator()
    calls = []

    def exchange():
        calls.append(True)
        raise ToolProviderOAuthError("Connect Buffer again.")

    for _ in range(2):
        with pytest.raises(ToolProviderOAuthError, match="Connect"):
            coordinator.run("fingerprint", exchange)
    assert len(calls) == 1


def test_different_fingerprints_have_independent_results():
    coordinator = RefreshCoordinator()
    assert coordinator.run("first", credentials)
    assert coordinator.run("second", credentials)
    assert len(coordinator._states) == 2


def test_old_cache_entries_expire(monkeypatch):
    monkeypatch.setattr("common.oauth.time.monotonic", lambda: 100)
    coordinator = RefreshCoordinator(ttl=10)
    coordinator.run("first", credentials)
    monkeypatch.setattr("common.oauth.time.monotonic", lambda: 111)
    coordinator.run("second", credentials)
    assert set(coordinator._states) == {"second"}
