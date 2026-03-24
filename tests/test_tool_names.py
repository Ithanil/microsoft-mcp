"""Tests that MCP tool registration matches the active auth mode."""

import asyncio
import importlib

import microsoft_mcp.settings as settings_module
import microsoft_mcp.tools as tools_module


def _load_tool_registry(monkeypatch, mode: str):
    monkeypatch.setenv("MICROSOFT_MCP_AUTH_MODE", mode)
    importlib.reload(settings_module)
    importlib.reload(tools_module)
    tools = asyncio.run(tools_module.mcp.list_tools(run_middleware=False))
    return {tool.name: tool for tool in tools}


def _assert_core_tools_exist(tool_registry):
    expected = [
        "list_emails",
        "get_email",
        "search_emails",
        "reply_to_email",
        "move_email",
        "update_email",
        "list_events",
        "get_event",
        "create_event",
        "update_event",
        "delete_event",
        "list_files",
        "get_file",
        "create_file",
        "delete_file",
        "search_files",
        "list_contacts",
        "get_contact",
        "create_contact",
    ]
    for name in expected:
        assert name in tool_registry, f"Expected tool '{name}' not found"


def test_no_tools_have_ms365_prefix(monkeypatch):
    """Gateway-level prefixing should remain the only prefixing mechanism."""
    tool_registry = _load_tool_registry(monkeypatch, "oauth_obo")
    assert len(tool_registry) > 0, "No tools registered"
    violations = [name for name in tool_registry if name.startswith("ms365_")]
    assert violations == [], f"Tools still have ms365_ prefix: {violations}"


def test_oauth_obo_mode_hides_cached_account_tools(monkeypatch):
    """OBO mode should not expose shared-cache bootstrap tools."""
    tool_registry = _load_tool_registry(monkeypatch, "oauth_obo")
    _assert_core_tools_exist(tool_registry)

    for name in ["list_accounts", "authenticate_account", "complete_authentication"]:
        assert name not in tool_registry, f"Tool '{name}' should not be exposed"

    assert len(tool_registry) == 31, (
        f"Expected 31 tools in oauth_obo mode, found {len(tool_registry)}: "
        f"{sorted(tool_registry.keys())}"
    )


def test_trusted_header_mode_keeps_cached_account_tools(monkeypatch):
    """Cached-account mode should continue exposing bootstrap tools."""
    tool_registry = _load_tool_registry(monkeypatch, "trusted_header_account")
    _assert_core_tools_exist(tool_registry)

    for name in ["list_accounts", "authenticate_account", "complete_authentication"]:
        assert name in tool_registry, f"Expected tool '{name}' not found"

    assert len(tool_registry) == 34, (
        f"Expected 34 tools in trusted_header_account mode, found {len(tool_registry)}: "
        f"{sorted(tool_registry.keys())}"
    )
