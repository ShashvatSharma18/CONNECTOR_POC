import base64
import json
import logging
import os
from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.chat_history import db
from app.connectors.jira import JiraConnector
from app.connectors.servicenow import ServiceNowConnector
from app.connectors.github import GitHubConnector
from app.connectors.azure_devops import AzureDevOpsConnector
from app.connectors.sharepoint import SharePointConnector
from app.connectors.teams import TeamsConnector
from app.connectors.slack import SlackConnector
from app.connectors.postgres import DatabaseConnector
from app.connectors.notion import NotionConnector
from app.connectors.universal_parser import get_universal_parser_connector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Chat & History"])


class CreateSessionRequest(BaseModel):
    title: str = Field(default="New chat")


class UpdateSessionRequest(BaseModel):
    title: str


class AddMessageRequest(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    rich_cards: list[dict[str, Any]] | None = None
    sources_accessed: list[dict[str, Any]] | None = None
    summary_block: dict[str, Any] | None = None
    suggested_followups: list[str] | None = None


class ConfigureConnectorRequest(BaseModel):
    connector_id: str
    credentials: dict[str, str]


class DisconnectConnectorRequest(BaseModel):
    connector_id: str


def update_env_file(key_values: dict[str, str | None]):
    """Update or remove key-value pairs in the .env file and in-memory os.environ."""
    env_path = os.path.join(os.getcwd(), ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updated_keys = set()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        if "=" in stripped:
            k, _ = stripped.split("=", 1)
            k = k.strip()
            if k in key_values:
                val = key_values[k]
                updated_keys.add(k)
                if val is not None and str(val).strip() != "":
                    new_lines.append(f"{k}={val}\n")
                    os.environ[k] = str(val)
                else:
                    os.environ.pop(k, None)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    for k, val in key_values.items():
        if k not in updated_keys and val is not None and str(val).strip() != "":
            new_lines.append(f"{k}={val}\n")
            os.environ[k] = str(val)

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def get_gmail_account():
    if os.path.exists(".gmail_token.json"):
        try:
            with open(".gmail_token.json") as f:
                d = json.load(f)
            idt = d.get("id_token")
            if idt:
                body = idt.split(".")[1]
                body += "=" * (-len(body) % 4)
                info = json.loads(base64.urlsafe_b64decode(body.encode()))
                return info.get("email")
        except Exception:
            pass
        return "Connected"
    return None


def get_google_drive_account():
    if os.path.exists(".google_drive_token.json"):
        return get_gmail_account() or "Connected"
    return None


def get_google_chat_account():
    if os.path.exists(".google_chat_token.json"):
        return get_gmail_account() or "Connected"
    return None


# ---------------- Connectors Status & Configuration ----------------
@router.get("/connectors/status")
def get_connectors_status():
    """Return live status of all enterprise connected sources with metadata and auth options."""
    gmail_token_file = os.path.exists(".gmail_token.json")
    github_token = bool(os.getenv("GITHUB_ACCESS_TOKEN") or os.getenv("GH_TOKEN") or os.path.exists(os.path.expanduser("~/.config/gh/hosts.yml")))
    file_share_configured = bool(os.getenv("FILE_SHARE_ROOT"))
    ms_configured = bool(
        os.getenv("MICROSOFT_TENANT_ID")
        and os.getenv("MICROSOFT_CLIENT_ID")
        and os.getenv("MICROSOFT_CLIENT_SECRET")
    )
    ado_configured = bool(os.getenv("AZURE_DEVOPS_ORG_URL") and os.getenv("AZURE_DEVOPS_PAT"))
    google_drive_token_file = os.path.exists(".google_drive_token.json")
    google_chat_token_file = os.path.exists(".google_chat_token.json")
    slack_token = bool(os.getenv("SLACK_BOT_TOKEN"))
    db_configured = bool(os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL") or os.path.exists("data/chat_history.db"))
    notion_configured = bool(os.getenv("NOTION_API_KEY"))

    parser_st = get_universal_parser_connector().get_status()
    parser_connected = parser_st.get("is_connected", False)

    slack_account = None
    if slack_token:
        try:
            st = SlackConnector().get_status()
            if st.get("authenticated"):
                slack_account = f"@{st.get('user', 'bot')} ({st.get('team', 'Workspace')})"
            else:
                slack_account = "Configured"
        except Exception:
            slack_account = "Configured"

    db_account = None
    if db_configured:
        try:
            st = DatabaseConnector().get_status()
            if st.get("authenticated"):
                db_account = f"{st.get('database_type')} ({st.get('table_count')} tables)"
            else:
                db_account = "Connected"
        except Exception:
            db_account = "Connected"

    notion_account = None
    if notion_configured:
        try:
            st = NotionConnector().get_status()
            if st.get("authenticated"):
                notion_account = "Connected"
            else:
                notion_account = "Configured"
        except Exception:
            notion_account = "Configured"

    gh_account = None
    if github_token:
        try:
            status = GitHubConnector().get_status()
            if status.get("authenticated"):
                gh_account = status.get("username")
        except Exception:
            gh_account = "Connected"

    sources = [
        {
            "id": "gmail",
            "name": "Gmail",
            "type": "email",
            "status": "Live" if gmail_token_file else "Not Connected",
            "is_connected": bool(gmail_token_file),
            "badge_color": "green" if gmail_token_file else "gray",
            "account": get_gmail_account(),
            "auth_type": "oauth",
            "auth_url": "http://localhost:8000/gmail/auth/login",
            "description": "Access your inbox, search emails, view threads, and download attachments.",
            "config_fields": [],
        },
        {
            "id": "google_drive",
            "name": "Google Drive",
            "type": "documents",
            "status": "Live" if google_drive_token_file else "Not Connected",
            "is_connected": bool(google_drive_token_file),
            "badge_color": "green" if google_drive_token_file else "gray",
            "account": get_google_drive_account(),
            "auth_type": "oauth",
            "auth_url": "http://localhost:8000/google-drive/auth/login",
            "description": "Read, search, and export Google Docs, Sheets, and drive files.",
            "config_fields": [],
        },
        {
            "id": "google_chat",
            "name": "Google Chat",
            "type": "chat",
            "status": "Live" if google_chat_token_file else "Not Connected",
            "is_connected": bool(google_chat_token_file),
            "badge_color": "green" if google_chat_token_file else "gray",
            "account": get_google_chat_account(),
            "auth_type": "oauth",
            "auth_url": "http://localhost:8000/google-chat/auth/login",
            "description": "Access direct messages, spaces, and team conversations across Google Workspace.",
            "config_fields": [],
        },
        {
            "id": "slack",
            "name": "Slack",
            "type": "chat",
            "status": "Live" if slack_token else "Not Connected",
            "is_connected": bool(slack_token),
            "badge_color": "green" if slack_token else "gray",
            "account": slack_account,
            "auth_type": "credentials",
            "description": "Search Slack channels, conversation history, and discussions via Bot Token.",
            "config_fields": [
                {
                    "key": "slack_bot_token",
                    "label": "Bot User OAuth Token",
                    "placeholder": "xoxb-...",
                    "type": "password",
                    "required": True,
                    "default_value": os.getenv("SLACK_BOT_TOKEN", ""),
                    "help_url": "https://api.slack.com/apps",
                    "help_text": "Create a Slack App with channels:read and groups:read scopes.",
                },
            ],
        },
        {
            "id": "postgres",
            "name": "SQL Database",
            "type": "database",
            "status": "Live" if db_configured else "Not Connected",
            "is_connected": bool(db_configured),
            "badge_color": "green" if db_configured else "gray",
            "account": db_account,
            "auth_type": "credentials",
            "description": "PostgreSQL or SQLite database for read-only analytical queries and schemas.",
            "config_fields": [
                {
                    "key": "postgres_url",
                    "label": "Database Connection URL",
                    "placeholder": "postgresql://user:pass@localhost:5432/dbname or sqlite:///data/db.sqlite",
                    "type": "password",
                    "required": True,
                    "default_value": os.getenv("POSTGRES_URL", ""),
                    "help_text": "PostgreSQL connection string or path to a SQLite database file.",
                },
            ],
        },
        {
            "id": "notion",
            "name": "Notion",
            "type": "documents",
            "status": "Live" if notion_configured else "Not Connected",
            "is_connected": bool(notion_configured),
            "badge_color": "green" if notion_configured else "gray",
            "account": notion_account,
            "auth_type": "credentials",
            "description": "Notion workspace pages, knowledge bases, and team documentation.",
            "config_fields": [
                {
                    "key": "notion_api_key",
                    "label": "Internal Integration Secret",
                    "placeholder": "secret_...",
                    "type": "password",
                    "required": True,
                    "default_value": os.getenv("NOTION_API_KEY", ""),
                    "help_url": "https://www.notion.so/my-integrations",
                    "help_text": "Create an integration at notion.so/my-integrations and share pages with it.",
                },
            ],
        },
        {
            "id": "github",
            "name": "GitHub",
            "type": "code",
            "status": "Live" if github_token else "Not Connected",
            "is_connected": bool(github_token),
            "badge_color": "green" if github_token else "gray",
            "account": gh_account,
            "auth_type": "credentials",
            "description": "Explore GitHub repositories, branches, and commits with Personal Access Token.",
            "config_fields": [
                {
                    "key": "github_token",
                    "label": "Personal Access Token (PAT)",
                    "placeholder": "ghp_...",
                    "type": "password",
                    "required": True,
                    "help_url": "https://github.com/settings/tokens",
                    "help_text": "Create a classic token with 'repo' scope, or use GitHub CLI.",
                },
            ],
        },
        {
            "id": "sharepoint",
            "name": "SharePoint",
            "type": "documents",
            "status": "Live" if ms_configured else "Not Connected",
            "is_connected": bool(ms_configured),
            "badge_color": "green" if ms_configured else "gray",
            "auth_type": "credentials",
            "description": "Microsoft 365 SharePoint sites and document drives via Microsoft Graph API.",
            "config_fields": [
                {
                    "key": "microsoft_tenant_id",
                    "label": "Azure AD Directory (Tenant) ID",
                    "placeholder": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                    "type": "text",
                    "required": True,
                    "default_value": os.getenv("MICROSOFT_TENANT_ID", ""),
                },
                {
                    "key": "microsoft_client_id",
                    "label": "Application (Client) ID",
                    "placeholder": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                    "type": "text",
                    "required": True,
                    "default_value": os.getenv("MICROSOFT_CLIENT_ID", ""),
                },
                {
                    "key": "microsoft_client_secret",
                    "label": "Client Secret",
                    "placeholder": "••••••••",
                    "type": "password",
                    "required": True,
                },
            ],
        },
        {
            "id": "teams",
            "name": "Microsoft Teams",
            "type": "chat",
            "status": "Live" if ms_configured else "Not Connected",
            "is_connected": bool(ms_configured),
            "badge_color": "green" if ms_configured else "gray",
            "auth_type": "credentials",
            "description": "Microsoft Teams channels and chat messages via Microsoft Graph API.",
            "config_fields": [
                {
                    "key": "microsoft_tenant_id",
                    "label": "Azure AD Directory (Tenant) ID",
                    "placeholder": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                    "type": "text",
                    "required": True,
                    "default_value": os.getenv("MICROSOFT_TENANT_ID", ""),
                },
                {
                    "key": "microsoft_client_id",
                    "label": "Application (Client) ID",
                    "placeholder": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                    "type": "text",
                    "required": True,
                    "default_value": os.getenv("MICROSOFT_CLIENT_ID", ""),
                },
                {
                    "key": "microsoft_client_secret",
                    "label": "Client Secret",
                    "placeholder": "••••••••",
                    "type": "password",
                    "required": True,
                },
            ],
        },
        {
            "id": "azure_devops",
            "name": "Azure DevOps Repos",
            "type": "code",
            "status": "Live" if ado_configured else "Not Connected",
            "is_connected": bool(ado_configured),
            "badge_color": "green" if ado_configured else "gray",
            "auth_type": "credentials",
            "description": "Azure DevOps Git repositories, code items, and projects.",
            "config_fields": [
                {
                    "key": "azure_devops_org_url",
                    "label": "Organization URL",
                    "placeholder": "https://dev.azure.com/your-org",
                    "type": "text",
                    "required": True,
                    "default_value": os.getenv("AZURE_DEVOPS_ORG_URL", ""),
                },
                {
                    "key": "azure_devops_pat",
                    "label": "Personal Access Token",
                    "placeholder": "••••••••",
                    "type": "password",
                    "required": True,
                },
            ],
        },
        {
            "id": "file_share",
            "name": "File Share",
            "type": "files",
            "status": "Live" if file_share_configured else "Not Connected",
            "is_connected": bool(file_share_configured),
            "badge_color": "blue" if file_share_configured else "gray",
            "account": os.path.basename(os.getenv("FILE_SHARE_ROOT", "")) or None,
            "auth_type": "credentials",
            "description": "Local or network shared directory for file searches.",
            "config_fields": [
                {
                    "key": "file_share_root",
                    "label": "Local Folder Path",
                    "placeholder": "/home/appinventiv/source-systems-poc/test-share",
                    "type": "text",
                    "required": True,
                    "default_value": os.getenv("FILE_SHARE_ROOT", ""),
                },
            ],
        },
        {
            "id": "universal_parser",
            "name": "Universal Document Parser",
            "type": "document_parser",
            "status": "Live" if parser_connected else "Offline",
            "is_connected": bool(parser_connected),
            "badge_color": "green" if parser_connected else "gray",
            "account": f"Ensemble Engine (PDF, OCR, Office, Tables)",
            "auth_type": "info",
            "description": "High-precision multimodal parsing for PDF, Word, Excel, PPTX, and structured tables with RAG chunking.",
            "config_fields": [
                {
                    "key": "universal_parser_mode",
                    "label": "Parsing Mode",
                    "placeholder": "balanced",
                    "type": "text",
                    "required": False,
                    "default_value": os.getenv("UNIVERSAL_PARSER_MODE", "balanced"),
                    "help_text": "Modes available: fast, balanced, max_accuracy, offline.",
                },
            ],
        },
        {
            "id": "lms",
            "name": "LMS",
            "type": "learning",
            "status": "Mock",
            "is_connected": True,
            "badge_color": "yellow",
            "account": "Active",
            "auth_type": "info",
            "description": "Enterprise Learning Management System demo connector.",
            "config_fields": [],
        },
    ]

    return {
        "connected_count": len([s for s in sources if s["is_connected"]]),
        "total_count": len(sources),
        "sources": sources,
    }


@router.post("/connectors/configure")
def configure_connector(payload: ConfigureConnectorRequest):
    """Dynamically configure and live-test credentials for a connector."""
    cid = payload.connector_id.lower().strip()
    creds = {k.strip(): str(v).strip() for k, v in payload.credentials.items()}

    # Slack
    if cid == "slack":
        bot_token = creds.get("slack_bot_token") or ""
        if not bot_token:
            raise HTTPException(400, "Slack Bot User OAuth Token is required.")
        conn = SlackConnector(token=bot_token)
        status = conn.get_status()
        if not status.get("authenticated"):
            err_msg = status.get("error") or "Invalid Slack Bot Token"
            raise HTTPException(400, f"Slack connection failed: {err_msg}")
        update_env_file({"SLACK_BOT_TOKEN": bot_token})
        return {"status": "connected", "message": f"Successfully connected to Slack workspace '{status.get('team')}' as @{status.get('user')}!"}

    # SQL Database / Postgres
    elif cid in ["postgres", "database"]:
        db_url = creds.get("postgres_url") or ""
        if not db_url:
            raise HTTPException(400, "Database URL is required.")
        conn = DatabaseConnector(db_url=db_url)
        status = conn.get_status()
        if not status.get("authenticated"):
            err_msg = status.get("error") or "Connection failed"
            raise HTTPException(400, f"Database connection failed: {err_msg}")
        update_env_file({"POSTGRES_URL": db_url})
        return {"status": "connected", "message": f"Connected to {status.get('database_type')} ({status.get('table_count')} tables detected)!"}

    # Notion
    elif cid == "notion":
        token = creds.get("notion_api_key") or ""
        if not token:
            raise HTTPException(400, "Notion Integration Secret is required.")
        conn = NotionConnector(token=token)
        status = conn.get_status()
        if not status.get("authenticated"):
            err_msg = status.get("error") or "Invalid Notion token"
            raise HTTPException(400, f"Notion authentication failed: {err_msg}")
        update_env_file({"NOTION_API_KEY": token})
        return {"status": "connected", "message": "Successfully connected to Notion workspace!"}

    # Legacy: Jira
    elif cid == "jira":
        base_url = creds.get("jira_base_url") or ""
        email = creds.get("jira_email") or ""
        api_token = creds.get("jira_api_token") or ""
        if not (base_url and email and api_token):
            raise HTTPException(400, "All Jira fields (URL, email, and API token) are required.")

        # Test live
        connector = JiraConnector(base_url=base_url, email=email, api_token=api_token)
        status = connector.get_status()
        if not status.get("authenticated"):
            err_msg = status.get("error") or status.get("message") or "Authentication failed"
            raise HTTPException(400, f"Failed to authenticate with Jira: {err_msg}")

        # Save
        update_env_file({
            "JIRA_BASE_URL": base_url,
            "JIRA_EMAIL": email,
            "JIRA_API_TOKEN": api_token,
        })
        return {"status": "connected", "message": f"Successfully connected to Jira ({email})!"}

    # 2. ServiceNow
    elif cid == "servicenow":
        instance_url = creds.get("servicenow_instance_url") or ""
        username = creds.get("servicenow_username") or ""
        password = creds.get("servicenow_password") or ""
        if not (instance_url and username and password):
            raise HTTPException(400, "All ServiceNow fields (instance URL, username, and password) are required.")

        connector = ServiceNowConnector(instance_url=instance_url, username=username, password=password)
        status = connector.get_status()
        if not status.get("reachable"):
            err_msg = status.get("message") or "Instance unreachable or bad credentials"
            raise HTTPException(400, f"ServiceNow connection failed: {err_msg}")

        update_env_file({
            "SERVICENOW_INSTANCE_URL": instance_url,
            "SERVICENOW_USERNAME": username,
            "SERVICENOW_PASSWORD": password,
        })
        return {"status": "connected", "message": f"Successfully connected to ServiceNow ({username})!"}

    # 3. GitHub
    elif cid == "github":
        token = creds.get("github_token") or ""
        if not token:
            raise HTTPException(400, "GitHub Personal Access Token is required.")

        update_env_file({"GITHUB_ACCESS_TOKEN": token})
        connector = GitHubConnector()
        status = connector.get_status()
        if not status.get("authenticated"):
            update_env_file({"GITHUB_ACCESS_TOKEN": None})
            raise HTTPException(400, f"GitHub authentication failed: {status.get('error')}")

        return {"status": "connected", "message": f"Successfully connected to GitHub ({status.get('username')})!"}

    # 4. Salesforce
    elif cid == "salesforce":
        instance_url = creds.get("salesforce_instance_url") or "https://login.salesforce.com"
        client_id = creds.get("salesforce_client_id") or ""
        client_secret = creds.get("salesforce_client_secret") or ""
        if not (client_id and client_secret):
            raise HTTPException(400, "Consumer Key and Consumer Secret are required.")

        update_env_file({
            "SALESFORCE_INSTANCE_URL": instance_url,
            "SALESFORCE_CLIENT_ID": client_id,
            "SALESFORCE_CLIENT_SECRET": client_secret,
        })
        return {
            "status": "configured",
            "message": "Salesforce Connected App configured! Click Connect to authenticate via OAuth.",
            "auth_url": "http://localhost:8000/salesforce/auth/login",
        }

    # 5. SharePoint & Teams (Microsoft 365)
    elif cid in ["sharepoint", "teams"]:
        tenant_id = creds.get("microsoft_tenant_id") or ""
        client_id = creds.get("microsoft_client_id") or ""
        client_secret = creds.get("microsoft_client_secret") or ""
        if not (tenant_id and client_id and client_secret):
            raise HTTPException(400, "Tenant ID, Client ID, and Client Secret are all required.")

        update_env_file({
            "MICROSOFT_TENANT_ID": tenant_id,
            "MICROSOFT_CLIENT_ID": client_id,
            "MICROSOFT_CLIENT_SECRET": client_secret,
        })
        return {"status": "connected", "message": "Microsoft Graph credentials saved successfully!"}

    # 6. Azure DevOps
    elif cid == "azure_devops":
        org_url = creds.get("azure_devops_org_url") or ""
        pat = creds.get("azure_devops_pat") or ""
        if not (org_url and pat):
            raise HTTPException(400, "Organization URL and PAT are required.")

        update_env_file({
            "AZURE_DEVOPS_ORG_URL": org_url,
            "AZURE_DEVOPS_PAT": pat,
        })
        return {"status": "connected", "message": "Azure DevOps credentials saved successfully!"}

    # 7. File Share
    elif cid == "file_share":
        path = creds.get("file_share_root") or ""
        if not path or not os.path.isdir(path):
            raise HTTPException(400, f"Directory '{path}' does not exist on the server.")

        update_env_file({"FILE_SHARE_ROOT": path})
        return {"status": "connected", "message": f"File Share path set to {path}."}

    else:
        raise HTTPException(400, f"Unknown connector '{cid}'.")


@router.post("/connectors/disconnect")
def disconnect_connector(payload: DisconnectConnectorRequest):
    """Disconnect a connector by clearing tokens or removing credentials."""
    cid = payload.connector_id.lower().strip()

    if cid == "gmail":
        if os.path.exists(".gmail_token.json"):
            os.remove(".gmail_token.json")
        return {"status": "disconnected", "message": "Gmail account disconnected."}

    elif cid == "google_drive":
        if os.path.exists(".google_drive_token.json"):
            os.remove(".google_drive_token.json")
        return {"status": "disconnected", "message": "Google Drive disconnected."}

    elif cid in ["google_chat", "googlechat"]:
        if os.path.exists(".google_chat_token.json"):
            os.remove(".google_chat_token.json")
        return {"status": "disconnected", "message": "Google Chat disconnected."}
 
    elif cid == "slack":
        update_env_file({"SLACK_BOT_TOKEN": None})
        return {"status": "disconnected", "message": "Slack disconnected."}

    elif cid in ["postgres", "database"]:
        update_env_file({"POSTGRES_URL": None, "DATABASE_URL": None})
        return {"status": "disconnected", "message": "Database disconnected."}

    elif cid == "notion":
        update_env_file({"NOTION_API_KEY": None})
        return {"status": "disconnected", "message": "Notion disconnected."}

    elif cid == "salesforce":
        if os.path.exists(".salesforce_token.json"):
            os.remove(".salesforce_token.json")
        update_env_file({
            "SALESFORCE_CLIENT_ID": None,
            "SALESFORCE_CLIENT_SECRET": None,
        })
        return {"status": "disconnected", "message": "Salesforce disconnected."}

    elif cid == "jira":
        update_env_file({
            "JIRA_BASE_URL": None,
            "JIRA_EMAIL": None,
            "JIRA_API_TOKEN": None,
        })
        return {"status": "disconnected", "message": "Jira disconnected."}

    elif cid == "servicenow":
        update_env_file({
            "SERVICENOW_INSTANCE_URL": None,
            "SERVICENOW_USERNAME": None,
            "SERVICENOW_PASSWORD": None,
        })
        return {"status": "disconnected", "message": "ServiceNow disconnected."}

    elif cid == "github":
        update_env_file({"GITHUB_ACCESS_TOKEN": None, "GH_TOKEN": None})
        return {"status": "disconnected", "message": "GitHub token cleared."}

    elif cid in ["sharepoint", "teams"]:
        update_env_file({
            "MICROSOFT_TENANT_ID": None,
            "MICROSOFT_CLIENT_ID": None,
            "MICROSOFT_CLIENT_SECRET": None,
        })
        return {"status": "disconnected", "message": "Microsoft 365 credentials cleared."}

    elif cid == "azure_devops":
        update_env_file({
            "AZURE_DEVOPS_ORG_URL": None,
            "AZURE_DEVOPS_PAT": None,
        })
        return {"status": "disconnected", "message": "Azure DevOps credentials cleared."}

    elif cid == "file_share":
        update_env_file({"FILE_SHARE_ROOT": None})
        return {"status": "disconnected", "message": "File Share path removed."}

    return {"status": "disconnected", "message": f"Connector {cid} disconnected."}


# ---------------- Chat Sessions & Messages ----------------
@router.post("/chat/sessions")
def create_chat_session(payload: CreateSessionRequest | None = None):
    title = payload.title if payload and payload.title else "New chat"
    return db.create_session(title=title)


@router.get("/chat/sessions")
def list_chat_sessions(limit: int = Query(default=50, ge=1, le=100)):
    return {"sessions": db.list_sessions(limit=limit)}


@router.get("/chat/sessions/{session_id}")
def get_chat_session(session_id: str):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


@router.patch("/chat/sessions/{session_id}")
def update_chat_session(session_id: str, payload: UpdateSessionRequest):
    updated = db.update_session_title(session_id, payload.title)
    if not updated:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"status": "success", "session_id": session_id, "title": payload.title}


@router.delete("/chat/sessions/{session_id}")
def delete_chat_session(session_id: str):
    deleted = db.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"status": "deleted", "session_id": session_id}


@router.post("/chat/sessions/{session_id}/messages")
def add_chat_message(session_id: str, payload: AddMessageRequest):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    msg = db.add_message(
        session_id=session_id,
        role=payload.role,
        content=payload.content,
        rich_cards=payload.rich_cards,
        sources_accessed=payload.sources_accessed,
        summary_block=payload.summary_block,
        suggested_followups=payload.suggested_followups,
    )
    return msg


class ChatQueryRequest(BaseModel):
    message: str


@router.post("/chat/sessions/{session_id}/chat")
def chat_turn_endpoint(session_id: str, payload: ChatQueryRequest):
    """
    Process an AI conversational turn:
    1. Greeting detection (no unnecessary searches)
    2. Multi-source live retrieval (Gmail, GitHub, SharePoint status, etc.)
    3. Multi-turn chat context
    4. Groq LLM synthesis
    5. Persistence in SQLite
    """
    from app.chat_service import process_chat_turn

    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return process_chat_turn(session_id=session_id, user_text=payload.message)


class SetSessionDocumentRequest(BaseModel):
    filename: str
    text: str
    elements_count: int = 0
    tables: list[dict[str, Any]] | None = None
    duration_ms: float = 0.0


@router.post("/chat/sessions/{session_id}/document")
def set_session_active_document(session_id: str, payload: SetSessionDocumentRequest):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    doc_data = payload.dict()
    db.set_session_document(session_id, doc_data)
    return {"status": "ok", "active_document": doc_data}


@router.delete("/chat/sessions/{session_id}/document")
def clear_session_active_document(session_id: str):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    db.set_session_document(session_id, None)
    return {"status": "ok", "message": "Active document detached from session"}


