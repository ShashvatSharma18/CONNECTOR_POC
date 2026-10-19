import os
from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.chat_history import db

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


# ---------------- Connectors Status ----------------
@router.get("/connectors/status")
def get_connectors_status():
    """Return live status of all 7 connected source systems."""
    # Check Gmail
    gmail_token_file = os.path.exists(".gmail_token.json")
    # Check GitHub
    github_token = os.path.exists(os.path.expanduser("~/.config/gh/hosts.yml")) or os.getenv("GH_TOKEN")
    # Check File Share
    file_share_configured = bool(os.getenv("FILE_SHARE_ROOT"))
    # Check SharePoint & Teams
    ms_configured = bool(
        os.getenv("MICROSOFT_TENANT_ID")
        and os.getenv("MICROSOFT_CLIENT_ID")
        and os.getenv("MICROSOFT_CLIENT_SECRET")
    )
    # Check Azure DevOps
    ado_configured = bool(os.getenv("AZURE_DEVOPS_ORG_URL") and os.getenv("AZURE_DEVOPS_PAT"))
    # Check ServiceNow
    servicenow_configured = bool(
        os.getenv("SERVICENOW_INSTANCE_URL")
        and os.getenv("SERVICENOW_USERNAME")
        and os.getenv("SERVICENOW_PASSWORD")
    )
    # Check Salesforce
    salesforce_token_file = os.path.exists(".salesforce_token.json")
    salesforce_configured = bool(
        salesforce_token_file
        or (os.getenv("SALESFORCE_CLIENT_ID") and os.getenv("SALESFORCE_CLIENT_SECRET"))
    )
    # Check Google Drive
    google_drive_token_file = os.path.exists(".google_drive_token.json")
    # Check Jira
    jira_configured = bool(
        os.getenv("JIRA_BASE_URL")
        and os.getenv("JIRA_EMAIL")
        and os.getenv("JIRA_API_TOKEN")
    )

    sources = [
        {
            "id": "gmail",
            "name": "Gmail",
            "type": "email",
            "status": "Live" if gmail_token_file else "Not Connected",
            "is_connected": gmail_token_file,
            "badge_color": "green" if gmail_token_file else "gray",
            "account": "shashvat1@appinventiv.com" if gmail_token_file else None,
        },
        {
            "id": "github",
            "name": "GitHub",
            "type": "code",
            "status": "Live",
            "is_connected": True,
            "badge_color": "green",
            "account": "ShashvatSharma18",
        },
        {
            "id": "file_share",
            "name": "File Share",
            "type": "files",
            "status": "Local Test" if file_share_configured else "Unconfigured",
            "is_connected": file_share_configured,
            "badge_color": "blue",
        },
        {
            "id": "lms",
            "name": "LMS",
            "type": "learning",
            "status": "Mock",
            "is_connected": True,
            "badge_color": "yellow",
        },
        {
            "id": "sharepoint",
            "name": "SharePoint",
            "type": "documents",
            "status": "Live" if ms_configured else "Code Ready",
            "is_connected": ms_configured,
            "badge_color": "green" if ms_configured else "purple",
        },
        {
            "id": "teams",
            "name": "Microsoft Teams",
            "type": "chat",
            "status": "Live" if ms_configured else "Code Ready",
            "is_connected": ms_configured,
            "badge_color": "green" if ms_configured else "purple",
        },
        {
            "id": "azure_devops",
            "name": "Azure DevOps Repos",
            "type": "code",
            "status": "Live" if ado_configured else "Code Ready",
            "is_connected": ado_configured,
            "badge_color": "green" if ado_configured else "purple",
        },
        {
            "id": "servicenow",
            "name": "ServiceNow",
            "type": "itsm",
            "status": "Live" if servicenow_configured else "Code Ready",
            "is_connected": servicenow_configured,
            "badge_color": "green" if servicenow_configured else "purple",
        },
        {
            "id": "salesforce",
            "name": "Salesforce",
            "type": "crm",
            "status": "Live" if salesforce_token_file else "Code Ready",
            "is_connected": salesforce_token_file,
            "badge_color": "green" if salesforce_token_file else "purple",
        },
        {
            "id": "google_drive",
            "name": "Google Drive",
            "type": "documents",
            "status": "Live" if google_drive_token_file else "Code Ready",
            "is_connected": google_drive_token_file,
            "badge_color": "green" if google_drive_token_file else "purple",
        },
        {
            "id": "jira",
            "name": "Jira",
            "type": "project_management",
            "status": "Live" if jira_configured else "Code Ready",
            "is_connected": jira_configured,
            "badge_color": "green" if jira_configured else "purple",
        },
    ]

    return {
        "connected_count": len([s for s in sources if s["is_connected"]]),
        "total_count": len(sources),
        "sources": sources,
    }


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

