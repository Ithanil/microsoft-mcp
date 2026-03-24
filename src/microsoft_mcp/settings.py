from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

AuthMode = Literal["oauth_obo", "trusted_header_account"]

_DEFAULT_GRAPH_AUTHORIZE_SCOPES = (
    "User.Read",
    "Mail.ReadWrite",
    "Mail.Send",
    "Calendars.ReadWrite",
    "Files.ReadWrite",
    "Contacts.ReadWrite",
)
_DEFAULT_GRAPH_OBO_SCOPES = ("https://graph.microsoft.com/.default",)
_SINGLE_TENANT_DISALLOWED = {"common", "organizations", "consumers"}


def _normalize_auth_mode(value: str | None) -> AuthMode:
    if value in (None, "", "oauth_obo"):
        return "oauth_obo"
    if value == "trusted_header_account":
        return "trusted_header_account"
    raise ValueError(
        "MICROSOFT_MCP_AUTH_MODE must be 'oauth_obo' or 'trusted_header_account'"
    )


def _parse_scopes(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    scopes = tuple(scope for scope in value.replace(",", " ").split() if scope)
    return scopes or default


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


@dataclass(frozen=True)
class Settings:
    auth_mode: AuthMode
    client_id: str | None
    client_secret: str | None
    tenant_id: str | None
    base_url: str | None
    identifier_uri: str | None
    api_scope: str
    graph_authorize_scopes: tuple[str, ...]
    graph_obo_scopes: tuple[str, ...]
    account_header_name: str
    require_authorization_consent: bool

    @property
    def is_oauth_obo(self) -> bool:
        return self.auth_mode == "oauth_obo"

    @property
    def is_trusted_header_account(self) -> bool:
        return self.auth_mode == "trusted_header_account"

    @property
    def normalized_account_header_name(self) -> str:
        return self.account_header_name.strip().lower()

    @property
    def effective_identifier_uri(self) -> str | None:
        if self.identifier_uri:
            return self.identifier_uri
        if self.client_id:
            return f"api://{self.client_id}"
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        auth_mode=_normalize_auth_mode(os.getenv("MICROSOFT_MCP_AUTH_MODE")),
        client_id=os.getenv("MICROSOFT_MCP_CLIENT_ID"),
        client_secret=os.getenv("MICROSOFT_MCP_CLIENT_SECRET"),
        tenant_id=os.getenv("MICROSOFT_MCP_TENANT_ID"),
        base_url=os.getenv("MICROSOFT_MCP_BASE_URL"),
        identifier_uri=os.getenv("MICROSOFT_MCP_IDENTIFIER_URI"),
        api_scope=os.getenv("MICROSOFT_MCP_API_SCOPE", "access_as_user"),
        graph_authorize_scopes=_parse_scopes(
            os.getenv("MICROSOFT_MCP_GRAPH_AUTHORIZE_SCOPES"),
            _DEFAULT_GRAPH_AUTHORIZE_SCOPES,
        ),
        graph_obo_scopes=_parse_scopes(
            os.getenv("MICROSOFT_MCP_GRAPH_OBO_SCOPES"),
            _DEFAULT_GRAPH_OBO_SCOPES,
        ),
        account_header_name=os.getenv(
            "MICROSOFT_MCP_ACCOUNT_HEADER_NAME", "x-microsoft-account-id"
        ),
        require_authorization_consent=_parse_bool(
            os.getenv("MICROSOFT_MCP_REQUIRE_AUTHORIZATION_CONSENT"), True
        ),
    )


def validate_runtime_settings(settings: Settings | None = None) -> list[str]:
    settings = settings or get_settings()
    errors: list[str] = []

    if not settings.client_id:
        errors.append("MICROSOFT_MCP_CLIENT_ID environment variable is required")

    if not settings.tenant_id:
        errors.append("MICROSOFT_MCP_TENANT_ID environment variable is required")
    elif settings.tenant_id in _SINGLE_TENANT_DISALLOWED:
        errors.append(
            "MICROSOFT_MCP_TENANT_ID must be a specific tenant ID for single-tenant deployments"
        )

    if settings.is_oauth_obo:
        if not settings.client_secret:
            errors.append(
                "MICROSOFT_MCP_CLIENT_SECRET environment variable is required in oauth_obo mode"
            )
        if not settings.base_url:
            errors.append(
                "MICROSOFT_MCP_BASE_URL environment variable is required in oauth_obo mode"
            )

    return errors
