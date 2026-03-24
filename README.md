# Microsoft MCP

Microsoft Graph MCP server for Outlook, Calendar, OneDrive, and Contacts.

## Credits

Fork of https://github.com/inconceivablelabs/microsoft-mcp/tree/master, which is itself a fork of https://github.com/elyxlz/microsoft-mcp.

This repository is maintained as a manual fork for a customer deployment, independent of upstream repo visibility changes. MIT licensed.

## What Changed in This Fork

This fork no longer relies on end users passing `account_id` into business tools.

- All Graph-backed tools run as the request-scoped caller.
- The default mode is single-tenant OAuth 2.1 plus On-Behalf-Of (`oauth_obo`) for HTTP MCP deployments such as Open WebUI.
- A compatibility mode (`trusted_header_account`) remains available for shared-cache deployments behind a trusted upstream that injects the current cached Microsoft account ID.

## Features

- Email management for Outlook mailboxes
- Calendar scheduling and event management
- OneDrive file listing, download, upload, and search
- Contact listing, lookup, and updates
- Unified search across multiple Microsoft Graph resources
- Request-scoped authentication with no `account_id` tool argument
- `get_auth_status` diagnostics in both auth modes

## Authentication Modes

### `oauth_obo` (default)

Use this mode for HTTP MCP frontends such as Open WebUI.

- Open WebUI authenticates each user to the MCP server with OAuth 2.1.
- The MCP server validates that bearer token.
- The server exchanges it for a Microsoft Graph token on behalf of the same user.
- Business tools run against `/me/...` resources for that authenticated caller.
- `authenticate_account` and `complete_authentication` are not exposed in this mode.

This mode is single-tenant only.

### `trusted_header_account`

Use this only when a trusted upstream injects the current cached Microsoft `account_id` into a request header.

- HTTP requests must include the trusted header configured by `MICROSOFT_MCP_ACCOUNT_HEADER_NAME`.
- The default header name is `x-microsoft-account-id`.
- The server resolves that cached account internally and uses the shared MSAL token cache.
- `authenticate_account` and `complete_authentication` stay available in this mode.
- `list_accounts` is not exposed as an MCP tool.

This mode is not safe for a directly internet-facing MCP server.

## Quick Start for Open WebUI

The default deployment path is `oauth_obo` over HTTP.

### 1. Create a Microsoft Entra app registration

1. Go to Microsoft Entra ID -> App registrations.
2. Create a new app registration for this MCP server.
3. Choose single-tenant only.
4. Under "Expose an API", create a scope such as `access_as_user`.
5. Under Microsoft Graph delegated permissions, grant the permissions your deployment needs.
6. Create a client secret.
7. Record the application ID, tenant ID, client secret, and identifier URI.

Common delegated Graph permissions for this server are:

- `User.Read`
- `Mail.ReadWrite`
- `Mail.Send`
- `Calendars.ReadWrite`
- `Files.ReadWrite`
- `Contacts.ReadWrite`

### 2. Install this fork

```bash
git clone https://github.com/Ithanil/microsoft-mcp.git
cd microsoft-mcp
uv sync
```

### 3. Configure the server for `oauth_obo`

```bash
export MICROSOFT_MCP_AUTH_MODE="oauth_obo"
export MICROSOFT_MCP_CLIENT_ID="your-app-id"
export MICROSOFT_MCP_CLIENT_SECRET="your-client-secret"
export MICROSOFT_MCP_TENANT_ID="your-single-tenant-id"
export MICROSOFT_MCP_BASE_URL="https://your-mcp-server.example.com"

# Optional overrides
# export MICROSOFT_MCP_IDENTIFIER_URI="api://your-app-id"
# export MICROSOFT_MCP_API_SCOPE="access_as_user"
# export MICROSOFT_MCP_GRAPH_AUTHORIZE_SCOPES="User.Read Mail.ReadWrite Mail.Send Calendars.ReadWrite Files.ReadWrite Contacts.ReadWrite"
# export MICROSOFT_MCP_GRAPH_OBO_SCOPES="https://graph.microsoft.com/.default"
# export MICROSOFT_MCP_REQUIRE_AUTHORIZATION_CONSENT="true"
```

Start the server with your normal FastMCP HTTP transport configuration. The application entry point is:

```bash
uv run microsoft-mcp
```

### 4. Configure Open WebUI

1. Add the MCP server in Open WebUI as an HTTP MCP integration.
2. Select OAuth 2.1 as the authentication method.
3. Use Open WebUI's "Register client" flow so Open WebUI becomes a client of this MCP server.
4. Have a user enable the MCP integration in chat and complete the browser-based login flow.

After that, Open WebUI sends per-user bearer tokens to the MCP server, and this server performs the Microsoft Graph On-Behalf-Of exchange internally.

## Trusted Header Mode

`trusted_header_account` exists for deployments that still rely on the shared token cache, but want to remove `account_id` from the tool interface.

### Required configuration

```bash
export MICROSOFT_MCP_AUTH_MODE="trusted_header_account"
export MICROSOFT_MCP_CLIENT_ID="your-app-id"
export MICROSOFT_MCP_TENANT_ID="your-single-tenant-id"

# Optional overrides
# export MICROSOFT_MCP_ACCOUNT_HEADER_NAME="x-microsoft-account-id"
# export MICROSOFT_MCP_TOKEN_CACHE="/path/to/token-cache.json"
```

### Bootstrap the shared cache

Use either of these:

- `uv run authenticate.py`
- The MCP tools `authenticate_account` and `complete_authentication`

### Request routing requirements

- Your trusted upstream must inject the current cached Microsoft `account_id` into the configured header for every HTTP request.
- HTTP requests without that trusted header are rejected for business-tool execution.
- If the header points at an unknown cached account, the request is not considered authenticated.
- In non-HTTP local/stdin contexts only, the server keeps a compatibility fallback to the first cached account.

## Tool Surface

Business tools no longer accept `account_id`.

Core categories:

- Email: `list_emails`, `get_email`, `create_email_draft`, `send_email`, `reply_to_email`, `reply_all_email`, `update_email`, `move_email`, `delete_email`, `get_attachment`, `search_emails`
- Calendar: `list_events`, `get_event`, `create_event`, `update_event`, `delete_event`, `respond_event`, `check_availability`
- Contacts: `list_contacts`, `get_contact`, `create_contact`, `update_contact`, `delete_contact`, `search_contacts`
- Files: `list_files`, `get_file`, `create_file`, `update_file`, `delete_file`, `search_files`
- Utility: `unified_search`, `get_auth_status`

Auth-specific tools:

- `authenticate_account` and `complete_authentication` are exposed only in `trusted_header_account`
- `get_auth_status` is exposed in both modes

## Usage Examples

```text
read my latest emails with full content
reply to the email from John saying "I'll review this today"
show my calendar for next week
check if I'm free tomorrow at 2pm
list files in my OneDrive
search for "project proposal" across all my files
```

## Identity Model

- The tool caller never supplies `account_id`.
- In `oauth_obo`, the effective Microsoft identity comes from the authenticated MCP bearer token.
- In `trusted_header_account`, the effective Microsoft identity comes from the trusted request header and the local MSAL cache.
- `get_auth_status` reports the active auth mode and whether the current request is authenticated and Graph-ready.

Typical `get_auth_status` fields include:

- `auth_mode`
- `authenticated`
- `graph_ready`
- `username`
- `principal_id`
- `tenant_id`
- `reason`

## Environment Variables

Primary settings:

- `MICROSOFT_MCP_AUTH_MODE`: `oauth_obo` or `trusted_header_account`
- `MICROSOFT_MCP_CLIENT_ID`: Entra application ID
- `MICROSOFT_MCP_TENANT_ID`: single-tenant Entra tenant ID

Required in `oauth_obo`:

- `MICROSOFT_MCP_CLIENT_SECRET`
- `MICROSOFT_MCP_BASE_URL`

Optional overrides:

- `MICROSOFT_MCP_IDENTIFIER_URI`
- `MICROSOFT_MCP_API_SCOPE`
- `MICROSOFT_MCP_GRAPH_AUTHORIZE_SCOPES`
- `MICROSOFT_MCP_GRAPH_OBO_SCOPES`
- `MICROSOFT_MCP_REQUIRE_AUTHORIZATION_CONSENT`
- `MICROSOFT_MCP_ACCOUNT_HEADER_NAME`
- `MICROSOFT_MCP_TOKEN_CACHE`

## Development

```bash
uv run pytest tests -q
uv run pyright
uvx ruff format .
uvx ruff check --fix --unsafe-fixes .
```

## Security Notes

- `oauth_obo` is the recommended production mode.
- `trusted_header_account` should only run behind a trusted upstream that fully owns the configured account header.
- Do not trust prompt content for account selection.
- Do not expose the shared-cache mode directly to the internet.
- Only grant the Microsoft Graph permissions your deployment actually needs.

## Troubleshooting

- `no_authenticated_mcp_user_token`: the request reached the MCP server without a valid authenticated MCP user token
- `Microsoft Graph OBO exchange failed`: verify client secret, tenant ID, Graph permissions, and consent in Entra
- `missing required trusted account header`: your trusted upstream did not send `MICROSOFT_MCP_ACCOUNT_HEADER_NAME`
- `unknown cached account`: the trusted header value does not match any account in the local MSAL cache
- `No cached access token is available`: re-run `authenticate.py` or the shared-cache auth tools to refresh the cached account

## License

MIT
