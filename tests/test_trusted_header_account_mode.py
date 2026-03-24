from unittest.mock import Mock

import pytest

from microsoft_mcp import auth as cache_auth
from microsoft_mcp import execution_context
from microsoft_mcp import settings as settings_module


def _set_trusted_header_mode(
    monkeypatch,
    *,
    trusted_secret: str | None = None,
    trusted_secret_name: str | None = None,
):
    monkeypatch.setenv("MICROSOFT_MCP_AUTH_MODE", "trusted_header_account")
    monkeypatch.setenv("MICROSOFT_MCP_CLIENT_ID", "client-id")
    monkeypatch.setenv("MICROSOFT_MCP_TENANT_ID", "tenant-id")
    if trusted_secret is None:
        monkeypatch.delenv("MICROSOFT_MCP_TRUSTED_HEADER_SECRET", raising=False)
    else:
        monkeypatch.setenv("MICROSOFT_MCP_TRUSTED_HEADER_SECRET", trusted_secret)
    if trusted_secret_name is None:
        monkeypatch.delenv("MICROSOFT_MCP_TRUSTED_HEADER_SECRET_NAME", raising=False)
    else:
        monkeypatch.setenv(
            "MICROSOFT_MCP_TRUSTED_HEADER_SECRET_NAME", trusted_secret_name
        )
    settings_module.get_settings.cache_clear()
    execution_context.get_settings.cache_clear()


def test_get_auth_status_true_for_known_header_and_cached_token(monkeypatch):
    _set_trusted_header_mode(monkeypatch)
    monkeypatch.setattr(
        execution_context,
        "get_http_headers",
        lambda include_all=True: {"x-microsoft-account-id": "acct-1"},
    )
    monkeypatch.setattr(
        cache_auth,
        "list_accounts",
        lambda: [cache_auth.Account(username="user@example.com", account_id="acct-1")],
    )
    get_token = Mock(return_value="graph-token")
    monkeypatch.setattr(cache_auth, "get_token", get_token)

    status = execution_context.get_auth_status()

    assert status == {
        "auth_mode": "trusted_header_account",
        "authenticated": True,
        "graph_ready": True,
        "username": "user@example.com",
    }
    get_token.assert_called_once_with("acct-1", allow_interactive=False)


def test_get_auth_status_false_when_http_header_missing(monkeypatch):
    _set_trusted_header_mode(monkeypatch)
    monkeypatch.setattr(
        execution_context,
        "get_http_headers",
        lambda include_all=True: {"x-forwarded-for": "203.0.113.5"},
    )
    monkeypatch.setattr(
        cache_auth,
        "list_accounts",
        lambda: [cache_auth.Account(username="user@example.com", account_id="acct-1")],
    )

    status = execution_context.get_auth_status()

    assert status["authenticated"] is False
    assert status["graph_ready"] is False
    assert "missing required trusted account header" in status["reason"]


def test_get_auth_status_false_when_header_account_unknown(monkeypatch):
    _set_trusted_header_mode(monkeypatch)
    monkeypatch.setattr(
        execution_context,
        "get_http_headers",
        lambda include_all=True: {"x-microsoft-account-id": "acct-missing"},
    )
    monkeypatch.setattr(
        cache_auth,
        "list_accounts",
        lambda: [cache_auth.Account(username="user@example.com", account_id="acct-1")],
    )

    status = execution_context.get_auth_status()

    assert status["authenticated"] is False
    assert status["graph_ready"] is False
    assert "unknown cached account" in status["reason"]


def test_get_auth_status_graph_not_ready_when_cached_token_missing(monkeypatch):
    _set_trusted_header_mode(monkeypatch)
    monkeypatch.setattr(
        execution_context,
        "get_http_headers",
        lambda include_all=True: {"x-microsoft-account-id": "acct-1"},
    )
    monkeypatch.setattr(
        cache_auth,
        "list_accounts",
        lambda: [cache_auth.Account(username="user@example.com", account_id="acct-1")],
    )
    monkeypatch.setattr(
        cache_auth,
        "get_token",
        Mock(side_effect=RuntimeError("No cached access token is available for account 'acct-1'")),
    )

    status = execution_context.get_auth_status()

    assert status["authenticated"] is True
    assert status["graph_ready"] is False
    assert "No cached access token is available" in status["reason"]


def test_get_auth_status_true_for_trusted_http_request(monkeypatch):
    _set_trusted_header_mode(monkeypatch, trusted_secret="expected-secret")
    monkeypatch.setattr(
        execution_context,
        "get_http_headers",
        lambda include_all=True: {
            "x-microsoft-account-id": "acct-1",
            "x-microsoft-mcp-trusted-secret": "expected-secret",
        },
    )
    monkeypatch.setattr(
        cache_auth,
        "list_accounts",
        lambda: [cache_auth.Account(username="user@example.com", account_id="acct-1")],
    )
    get_token = Mock(return_value="graph-token")
    monkeypatch.setattr(cache_auth, "get_token", get_token)

    status = execution_context.get_auth_status()

    assert status == {
        "auth_mode": "trusted_header_account",
        "authenticated": True,
        "graph_ready": True,
        "username": "user@example.com",
    }
    get_token.assert_called_once_with("acct-1", allow_interactive=False)


def test_get_auth_status_uses_configured_trust_header_name(monkeypatch):
    _set_trusted_header_mode(
        monkeypatch,
        trusted_secret="expected-secret",
        trusted_secret_name="x-upstream-proof",
    )
    monkeypatch.setattr(
        execution_context,
        "get_http_headers",
        lambda include_all=True: {
            "x-microsoft-account-id": "acct-1",
            "x-upstream-proof": "expected-secret",
        },
    )
    monkeypatch.setattr(
        cache_auth,
        "list_accounts",
        lambda: [cache_auth.Account(username="user@example.com", account_id="acct-1")],
    )
    get_token = Mock(return_value="graph-token")
    monkeypatch.setattr(cache_auth, "get_token", get_token)

    status = execution_context.get_auth_status()

    assert status == {
        "auth_mode": "trusted_header_account",
        "authenticated": True,
        "graph_ready": True,
        "username": "user@example.com",
    }
    get_token.assert_called_once_with("acct-1", allow_interactive=False)


def test_get_auth_status_false_when_trust_header_missing(monkeypatch):
    _set_trusted_header_mode(monkeypatch, trusted_secret="expected-secret")
    monkeypatch.setattr(
        execution_context,
        "get_http_headers",
        lambda include_all=True: {"x-microsoft-account-id": "acct-1"},
    )
    monkeypatch.setattr(
        cache_auth,
        "list_accounts",
        lambda: [cache_auth.Account(username="user@example.com", account_id="acct-1")],
    )
    get_token = Mock(return_value="graph-token")
    monkeypatch.setattr(cache_auth, "get_token", get_token)

    status = execution_context.get_auth_status()

    assert status["authenticated"] is False
    assert status["graph_ready"] is False
    assert "missing required trusted upstream header" in status["reason"]
    get_token.assert_not_called()


def test_get_auth_status_false_when_trust_header_wrong(monkeypatch):
    _set_trusted_header_mode(monkeypatch, trusted_secret="expected-secret")
    monkeypatch.setattr(
        execution_context,
        "get_http_headers",
        lambda include_all=True: {
            "x-microsoft-account-id": "acct-1",
            "x-microsoft-mcp-trusted-secret": "wrong-secret",
        },
    )
    monkeypatch.setattr(
        cache_auth,
        "list_accounts",
        lambda: [cache_auth.Account(username="user@example.com", account_id="acct-1")],
    )
    get_token = Mock(return_value="graph-token")
    monkeypatch.setattr(cache_auth, "get_token", get_token)

    status = execution_context.get_auth_status()

    assert status["authenticated"] is False
    assert status["graph_ready"] is False
    assert "invalid trusted upstream header" in status["reason"]
    get_token.assert_not_called()


def test_stdio_fallback_still_uses_first_cached_account(monkeypatch):
    _set_trusted_header_mode(monkeypatch, trusted_secret="expected-secret")
    monkeypatch.setattr(execution_context, "get_http_headers", lambda include_all=True: {})
    monkeypatch.setattr(
        cache_auth,
        "list_accounts",
        lambda: [cache_auth.Account(username="user@example.com", account_id="acct-1")],
    )
    get_token = Mock(return_value="graph-token")
    monkeypatch.setattr(cache_auth, "get_token", get_token)

    status = execution_context.get_auth_status()

    assert status == {
        "auth_mode": "trusted_header_account",
        "authenticated": True,
        "graph_ready": True,
        "username": "user@example.com",
    }
    get_token.assert_called_once_with("acct-1", allow_interactive=False)


def test_resolve_execution_context_raises_when_trust_header_missing(monkeypatch):
    _set_trusted_header_mode(monkeypatch, trusted_secret="expected-secret")
    monkeypatch.setattr(
        execution_context,
        "get_http_headers",
        lambda include_all=True: {"x-microsoft-account-id": "acct-1"},
    )
    monkeypatch.setattr(
        cache_auth,
        "list_accounts",
        lambda: [cache_auth.Account(username="user@example.com", account_id="acct-1")],
    )
    get_token = Mock(return_value="graph-token")
    monkeypatch.setattr(cache_auth, "get_token", get_token)

    with pytest.raises(RuntimeError, match="missing required trusted upstream header"):
        execution_context.resolve_execution_context()

    get_token.assert_not_called()


def test_resolve_execution_context_raises_when_trust_header_wrong(monkeypatch):
    _set_trusted_header_mode(monkeypatch, trusted_secret="expected-secret")
    monkeypatch.setattr(
        execution_context,
        "get_http_headers",
        lambda include_all=True: {
            "x-microsoft-account-id": "acct-1",
            "x-microsoft-mcp-trusted-secret": "wrong-secret",
        },
    )
    monkeypatch.setattr(
        cache_auth,
        "list_accounts",
        lambda: [cache_auth.Account(username="user@example.com", account_id="acct-1")],
    )
    get_token = Mock(return_value="graph-token")
    monkeypatch.setattr(cache_auth, "get_token", get_token)

    with pytest.raises(RuntimeError, match="invalid trusted upstream header"):
        execution_context.resolve_execution_context()

    get_token.assert_not_called()
