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
    servicenow_configured = bool(
        os.getenv("SERVICENOW_INSTANCE_URL")
        and os.getenv("SERVICENOW_USERNAME")
        and os.getenv("SERVICENOW_PASSWORD")
    )
    salesforce_token_file = os.path.exists(".salesforce_token.json")
    salesforce_configured = bool(
        salesforce_token_file
        or (os.getenv("SALESFORCE_CLIENT_ID") and os.getenv("SALESFORCE_CLIENT_SECRET"))
    )
    google_drive_token_file = os.path.exists(".google_drive_token.json")
    jira_configured = bool(
        os.getenv("JIRA_BASE_URL")
        and os.getenv("JIRA_EMAIL")
        and os.getenv("JIRA_API_TOKEN")
    )

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
            "id": "jira",
            "name": "Jira",
            "type": "project_management",
            "status": "Live" if jira_configured else "Not Connected",
            "is_connected": bool(jira_configured),
            "badge_color": "green" if jira_configured else "gray",
            "account": os.getenv("JIRA_EMAIL") if jira_configured else None,
            "auth_type": "credentials",
            "description": "Search Atlassian Jira Cloud issues, sprint backlogs, and project tickets.",
            "config_fields": [
                {
                    "key": "jira_base_url",
                    "label": "Jira Domain URL",
                    "placeholder": "https://your-domain.atlassian.net",
                    "type": "text",
                    "required": True,
                    "default_value": os.getenv("JIRA_BASE_URL", ""),
                },
                {
                    "key": "jira_email",
                    "label": "Atlassian Account Email",
                    "placeholder": "name@example.com",
                    "type": "text",
                    "required": True,
                    "default_value": os.getenv("JIRA_EMAIL", ""),
                },
                {
                    "key": "jira_api_token",
                    "label": "Atlassian API Token",
                    "placeholder": "Paste your Jira API Token",
                    "type": "password",
                    "required": True,
                    "help_url": "https://id.atlassian.com/manage-profile/security/api-tokens",
                    "help_text": "Create a token from Atlassian Account Security > API Tokens.",
                },
            ],
        },
        {
            "id": "servicenow",
            "name": "ServiceNow",
            "type": "itsm",
            "status": "Live" if servicenow_configured else "Not Connected",
            "is_connected": bool(servicenow_configured),
            "badge_color": "green" if servicenow_configured else "gray",
            "account": os.getenv("SERVICENOW_USERNAME") if servicenow_configured else None,
            "auth_type": "credentials",
            "description": "Query ServiceNow incidents, IT service requests, and knowledge articles.",
            "config_fields": [
                {
                    "key": "servicenow_instance_url",
                    "label": "Instance URL",
                    "placeholder": "https://devXXXXX.service-now.com",
                    "type": "text",
                    "required": True,
                    "default_value": os.getenv("SERVICENOW_INSTANCE_URL", ""),
                    "help_text": "Your ServiceNow Developer or company instance URL.",
                },
                {
                    "key": "servicenow_username",
                    "label": "Username",
                    "placeholder": "admin",
                    "type": "text",
                    "required": True,
                    "default_value": os.getenv("SERVICENOW_USERNAME", ""),
                },
                {
                    "key": "servicenow_password",
                    "label": "Password",
                    "placeholder": "••••••••",
                    "type": "password",
                    "required": True,
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
            "id": "salesforce",
            "name": "Salesforce",
            "type": "crm",
            "status": "Live" if salesforce_token_file else "Not Connected",
            "is_connected": bool(salesforce_token_file),
            "badge_color": "green" if salesforce_token_file else "gray",
            "account": "Connected" if salesforce_token_file else None,
            "auth_type": "oauth" if (os.getenv("SALESFORCE_CLIENT_ID") and os.getenv("SALESFORCE_CLIENT_SECRET")) else "credentials",
            "auth_url": "http://localhost:8000/salesforce/auth/login",
            "description": "Salesforce CRM Connected App OAuth configuration.",
            "config_fields": [
                {
                    "key": "salesforce_instance_url",
                    "label": "MyDomain URL",
                    "placeholder": "https://your-org.my.salesforce.com",
                    "type": "text",
                    "required": False,
                    "default_value": os.getenv("SALESFORCE_INSTANCE_URL", "https://login.salesforce.com"),
                },
                {
                    "key": "salesforce_client_id",
                    "label": "Connected App Consumer Key",
                    "placeholder": "3MVG9...",
                    "type": "text",
                    "required": True,
                    "default_value": os.getenv("SALESFORCE_CLIENT_ID", ""),
                },
                {
                    "key": "salesforce_client_secret",
                    "label": "Connected App Consumer Secret",
                    "placeholder": "••••••••",
                    "type": "password",
                    "required": True,
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

    # 1. Jira
    if cid == "jira":
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

