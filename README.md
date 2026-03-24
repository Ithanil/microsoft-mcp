# Microsoft MCP

Powerful MCP server for Microsoft Graph API - a complete AI assistant toolkit for Outlook, Calendar, OneDrive, and Contacts.

# Credits
Fork of https://github.com/inconceivablelabs/microsoft-mcp/tree/master, which is a fork of https://github.com/elyxlz/microsoft-mcp
Kept as manual fork to provide this to a customer, irrespective of visibility changes of the original repo(s). MIT-Licensed. 

## Features

- **Email Management**: Read, send, reply, manage attachments, organize folders
- **Calendar Intelligence**: Create, update, check availability, respond to invitations
- **OneDrive Files**: Upload, download, browse with pagination
- **Contacts**: Search and list contacts from your address book
- **Per-User OAuth/OBO**: Run Graph calls as the authenticated MCP caller in single-tenant Entra deployments
- **Shared Cache Fallback**: Optional trusted-header/shared-cache mode for legacy account mapping workflows
- **Unified Search**: Search across emails, files, events, and people

## Quick Start with Claude Desktop

```bash
# Add Microsoft MCP server (replace with your Azure app ID)
claude mcp add microsoft-mcp -e MICROSOFT_MCP_CLIENT_ID=your-app-id-here -- uvx --from git+https://github.com/elyxlz/microsoft-mcp.git microsoft-mcp

# Start Claude Desktop
claude
```

### Usage Examples

```bash
# Email examples
> read my latest emails with full content
> reply to the email from John saying "I'll review this today"
> send an email with attachment to alice@example.com

# Calendar examples  
> show my calendar for next week
> check if I'm free tomorrow at 2pm
> create a meeting with Bob next Monday at 10am

# File examples
> list files in my OneDrive
> upload this report to OneDrive
> search for "project proposal" across all my files

# Multi-account
> list all my Microsoft accounts
> send email from my work account
```

## Available Tools

### Email Tools
- **`list_emails`** - List emails with optional body content
- **`get_email`** - Get specific email with attachments
- **`create_email_draft`** - Create email draft with attachments support
- **`send_email`** - Send email immediately with CC/BCC and attachments
- **`reply_to_email`** - Reply maintaining thread context
- **`reply_all_email`** - Reply to all recipients in thread
- **`update_email`** - Mark emails as read/unread
- **`move_email`** - Move emails between folders
- **`delete_email`** - Delete emails
- **`get_attachment`** - Get email attachment content
- **`search_emails`** - Search emails by query

### Calendar Tools
- **`list_events`** - List calendar events with details
- **`get_event`** - Get specific event details
- **`create_event`** - Create events with location and attendees
- **`update_event`** - Reschedule or modify events
- **`delete_event`** - Cancel events
- **`respond_event`** - Accept/decline/tentative response to invitations
- **`check_availability`** - Check free/busy times for scheduling

### Contact Tools
- **`list_contacts`** - List all contacts
- **`get_contact`** - Get specific contact details
- **`create_contact`** - Create new contact
- **`update_contact`** - Update contact information
- **`delete_contact`** - Delete contact
- **`search_contacts`** - Search contacts by query

### File Tools
- **`list_files`** - Browse OneDrive files and folders
- **`get_file`** - Download file content
- **`create_file`** - Upload files to OneDrive
- **`update_file`** - Update existing file content
- **`delete_file`** - Delete files or folders
- **`search_files`** - Search files in OneDrive

### Utility Tools
- **`unified_search`** - Search across emails, events, and files
- **`list_accounts`** - Show authenticated Microsoft accounts in `trusted_header_account` mode only
- **`authenticate_account`** - Start device-flow authentication in `trusted_header_account` mode only
- **`complete_authentication`** - Complete device-flow authentication in `trusted_header_account` mode only

## Manual Setup

### 1. Azure App Registration

1. Go to [Azure Portal](https://portal.azure.com) → Microsoft Entra ID → App registrations
2. New registration → Name: `microsoft-mcp`
3. Supported account types: Single tenant only
4. Authentication → Add a Web redirect URI for your MCP server callback, e.g. `https://your-server.example.com/auth/callback`
5. Expose an API → add a custom scope such as `access_as_user`
6. API permissions → Add these delegated Microsoft Graph permissions:
   - Mail.ReadWrite
   - Mail.Send
   - Calendars.ReadWrite
   - Files.ReadWrite
   - Contacts.ReadWrite
   - User.Read
7. Create a client secret
8. Copy Application ID, Directory (tenant) ID, and client secret

### 2. Installation

```bash
git clone https://github.com/elyxlz/microsoft-mcp.git
cd microsoft-mcp
uv sync
```

### 3. Server Configuration

```bash
# Required for both modes
export MICROSOFT_MCP_CLIENT_ID="your-app-id-here"
export MICROSOFT_MCP_TENANT_ID="your-single-tenant-id"

# Primary mode: per-user OAuth 2.1 + OBO
export MICROSOFT_MCP_AUTH_MODE="oauth_obo"
export MICROSOFT_MCP_CLIENT_SECRET="your-client-secret"
export MICROSOFT_MCP_BASE_URL="https://your-server.example.com"

# Optional legacy/shared-cache mode
# export MICROSOFT_MCP_AUTH_MODE="trusted_header_account"
# uv run authenticate.py
```

### 4. Claude Desktop Configuration

Add to your Claude Desktop configuration:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "microsoft": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/elyxlz/microsoft-mcp.git", "microsoft-mcp"],
      "env": {
        "MICROSOFT_MCP_CLIENT_ID": "your-app-id-here"
      }
    }
  }
}
```

Or for local development:

```json
{
  "mcpServers": {
    "microsoft": {
      "command": "uv",
      "args": ["--directory", "/path/to/microsoft-mcp", "run", "microsoft-mcp"],
      "env": {
        "MICROSOFT_MCP_CLIENT_ID": "your-app-id-here"
      }
    }
  }
}
```

## Identity Model

Business tools no longer take `account_id`.

- In `oauth_obo` mode, the authenticated MCP caller is used automatically.
- In `trusted_header_account` mode, the server resolves the effective account internally from a trusted header or the local shared cache flow.

```python
send_email("user@example.com", "Subject", "Body")
list_emails(limit=10, include_body=True)
create_event("Meeting", "2024-01-15T10:00:00Z", "2024-01-15T11:00:00Z")
```

## Development

```bash
# Run tests
uv run pytest tests/ -v

# Type checking
uv run pyright

# Format code
uvx ruff format .

# Lint
uvx ruff check --fix --unsafe-fixes .
```

## Example: AI Assistant Scenarios

### Smart Email Management
```python
# List latest emails with full content
emails = list_emails(limit=10, include_body=True)

# Reply maintaining thread
reply_to_email(email_id, "Thanks for your message. I'll review and get back to you.")

# Forward with attachments
email = get_email(email_id)
attachments = [get_attachment(email_id, att["id"], f"/tmp/{att['name']}") for att in email["attachments"]]
send_email("boss@company.com", f"FW: {email['subject']}", email["body"]["content"], attachments=attachments)
```

### Intelligent Scheduling
```python
# Check availability before scheduling
availability = check_availability("2024-01-15T10:00:00Z", "2024-01-15T18:00:00Z", ["colleague@company.com"])

# Create meeting with details
create_event(
    "Project Review",
    "2024-01-15T14:00:00Z", 
    "2024-01-15T15:00:00Z",
    location="Conference Room A",
    body="Quarterly review of project progress",
    attendees=["colleague@company.com", "manager@company.com"]
)
```

## Security Notes

- `oauth_obo` mode validates per-user MCP access tokens and exchanges them for Graph tokens on behalf of the caller
- `trusted_header_account` mode uses the local token cache and should only be used behind a trusted upstream boundary
- Shared-cache tokens are stored locally in `~/.microsoft_mcp_token_cache.json`
- Only request permissions your app actually needs
- Consider using a dedicated app registration for production

## Troubleshooting

- **Authentication fails**: Check your CLIENT_ID is correct
- **Missing client secret/base URL**: Required in `oauth_obo` mode
- **Missing permissions**: Ensure all required API permissions are granted in Azure
- **Token errors**: Delete `~/.microsoft_mcp_token_cache.json` and re-authenticate

## License

MIT
