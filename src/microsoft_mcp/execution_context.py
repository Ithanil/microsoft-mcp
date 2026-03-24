from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, cast

import msal
from fastmcp.dependencies import Depends
from fastmcp.server.auth.providers.azure import AzureProvider
from fastmcp.server.dependencies import get_access_token, get_http_headers

from . import auth as cache_auth
from .settings import Settings, get_settings, validate_runtime_settings


@dataclass(frozen=True)
class RequestIdentity:
    auth_mode: str
    tenant_id: str | None = None
    principal_id: str | None = None
    username: str | None = None
    account_id: str | None = None
    claims: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionContext:
    identity: RequestIdentity
    graph_access_token: str


def should_expose_cached_account_tools(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return settings.is_trusted_header_account


def build_auth_provider(settings: Settings | None = None) -> AzureProvider | None:
    settings = settings or get_settings()
    if not settings.is_oauth_obo:
        return None

    if validate_runtime_settings(settings):
        return None

    return AzureProvider(
        client_id=settings.client_id or "",
        client_secret=settings.client_secret or "",
        tenant_id=settings.tenant_id or "",
        required_scopes=[settings.api_scope],
        additional_authorize_scopes=list(settings.graph_authorize_scopes),
        base_url=settings.base_url or "",
        identifier_uri=settings.effective_identifier_uri,
        require_authorization_consent=settings.require_authorization_consent,
    )


@lru_cache(maxsize=1)
def _get_obo_app() -> msal.ConfidentialClientApplication:
    settings = get_settings()
    authority = f"https://login.microsoftonline.com/{settings.tenant_id}"
    return msal.ConfidentialClientApplication(
        settings.client_id or "",
        authority=authority,
        client_credential=settings.client_secret,
    )


def _exchange_graph_access_token(user_assertion: str) -> str:
    settings = get_settings()
    result = _get_obo_app().acquire_token_on_behalf_of(
        user_assertion=user_assertion,
        scopes=list(settings.graph_obo_scopes),
    )

    if not result:
        raise RuntimeError("Microsoft Graph OBO exchange returned no result")

    if "error" in result:
        raise RuntimeError(
            "Microsoft Graph OBO exchange failed: "
            f"{result.get('error_description', result['error'])}"
        )

    return result["access_token"]


def resolve_execution_context() -> ExecutionContext:
    settings = get_settings()

    if settings.is_oauth_obo:
        access_token = get_access_token()
        if access_token is None:
            raise RuntimeError(
                "No authenticated MCP user token is available for Graph OBO exchange"
            )

        claims = dict(access_token.claims or {})
        identity = RequestIdentity(
            auth_mode=settings.auth_mode,
            tenant_id=claims.get("tid"),
            principal_id=claims.get("oid") or claims.get("sub"),
            username=(
                claims.get("preferred_username")
                or claims.get("upn")
                or claims.get("email")
            ),
            claims=claims,
        )
        return ExecutionContext(
            identity=identity,
            graph_access_token=_exchange_graph_access_token(access_token.token),
        )

    if settings.is_trusted_header_account:
        headers = get_http_headers(include_all=True)
        account_id = headers.get(settings.normalized_account_header_name) or None

        identity = RequestIdentity(
            auth_mode=settings.auth_mode,
            account_id=account_id,
        )
        return ExecutionContext(
            identity=identity,
            graph_access_token=cache_auth.get_token(account_id),
        )

    raise RuntimeError(f"Unsupported authentication mode: {settings.auth_mode}")


def resolve_graph_access_token() -> str:
    return resolve_execution_context().graph_access_token


def CurrentExecutionContext() -> ExecutionContext:
    return cast(ExecutionContext, Depends(resolve_execution_context))


def CurrentGraphAccessToken() -> str:
    return cast(str, Depends(resolve_graph_access_token))
