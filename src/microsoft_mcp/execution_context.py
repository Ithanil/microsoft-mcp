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


def _build_oauth_identity() -> RequestIdentity | None:
    access_token = get_access_token()
    if access_token is None:
        return None

    claims = dict(access_token.claims or {})
    return RequestIdentity(
        auth_mode=get_settings().auth_mode,
        tenant_id=claims.get("tid"),
        principal_id=claims.get("oid") or claims.get("sub"),
        username=(
            claims.get("preferred_username")
            or claims.get("upn")
            or claims.get("email")
        ),
        claims=claims,
    )


def _resolve_cached_account_identity(require_account: bool) -> RequestIdentity:
    settings = get_settings()
    headers = get_http_headers(include_all=True)
    account_id = headers.get(settings.normalized_account_header_name) or None
    accounts = cache_auth.list_accounts()

    if account_id:
        account = next((acc for acc in accounts if acc.account_id == account_id), None)
        if account is None:
            if require_account:
                raise RuntimeError(
                    f"Trusted account header '{settings.account_header_name}' references an unknown cached account"
                )
            return RequestIdentity(
                auth_mode=settings.auth_mode,
                account_id=account_id,
            )
        return RequestIdentity(
            auth_mode=settings.auth_mode,
            username=account.username,
            account_id=account.account_id,
        )

    # In HTTP mode, the trusted header is mandatory. In stdio/local mode there is no
    # active HTTP request, so we preserve the legacy shared-cache fallback behavior.
    if headers:
        if require_account:
            raise RuntimeError(
                f"Missing required trusted account header '{settings.account_header_name}'"
            )
        return RequestIdentity(auth_mode=settings.auth_mode)

    if accounts:
        account = accounts[0]
        return RequestIdentity(
            auth_mode=settings.auth_mode,
            username=account.username,
            account_id=account.account_id,
        )

    if require_account:
        raise RuntimeError("No authenticated Microsoft account is available in the shared cache")
    return RequestIdentity(auth_mode=settings.auth_mode)


def get_auth_status() -> dict[str, Any]:
    settings = get_settings()

    if settings.is_oauth_obo:
        access_token = get_access_token()
        if access_token is None:
            return {
                "auth_mode": settings.auth_mode,
                "authenticated": False,
                "graph_ready": False,
                "reason": "no_authenticated_mcp_user_token",
            }

        identity = _build_oauth_identity()
        assert identity is not None
        status: dict[str, Any] = {
            "auth_mode": settings.auth_mode,
            "authenticated": True,
            "graph_ready": True,
            "username": identity.username,
            "principal_id": identity.principal_id,
            "tenant_id": identity.tenant_id,
        }
        try:
            _exchange_graph_access_token(access_token.token)
        except Exception as exc:
            status["graph_ready"] = False
            status["reason"] = str(exc)
        return status

    identity = _resolve_cached_account_identity(require_account=False)
    authenticated = identity.account_id is not None
    status = {
        "auth_mode": settings.auth_mode,
        "authenticated": authenticated,
        "graph_ready": authenticated,
        "username": identity.username,
    }
    if not authenticated:
        status["reason"] = (
            f"missing '{settings.account_header_name}' header or no cached account available"
        )
    return status


def resolve_execution_context() -> ExecutionContext:
    settings = get_settings()

    if settings.is_oauth_obo:
        access_token = get_access_token()
        if access_token is None:
            raise RuntimeError(
                "No authenticated MCP user token is available for Graph OBO exchange"
            )

        identity = _build_oauth_identity()
        assert identity is not None
        return ExecutionContext(
            identity=identity,
            graph_access_token=_exchange_graph_access_token(access_token.token),
        )

    if settings.is_trusted_header_account:
        identity = _resolve_cached_account_identity(require_account=True)
        return ExecutionContext(
            identity=identity,
            graph_access_token=cache_auth.get_token(
                identity.account_id, allow_interactive=False
            ),
        )

    raise RuntimeError(f"Unsupported authentication mode: {settings.auth_mode}")


def resolve_graph_access_token() -> str:
    return resolve_execution_context().graph_access_token


def CurrentExecutionContext() -> ExecutionContext:
    return cast(ExecutionContext, Depends(resolve_execution_context))


def CurrentGraphAccessToken() -> str:
    return cast(str, Depends(resolve_graph_access_token))
