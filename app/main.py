from io import BytesIO
from urllib.parse import quote
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response, RedirectResponse, StreamingResponse

from app.connectors.file_share import get_connector
from app.connectors.lms import get_lms_connector
from app.connectors.github import get_github_connector
from app.connectors.gmail import get_gmail_connector
from app.connectors.salesforce import get_salesforce_connector
from app.connectors.google_drive import get_google_drive_connector
from app.connectors.google_chat import get_google_chat_connector
from app.connectors.servicenow import get_servicenow_connector
from app.connectors.jira import get_jira_connector
from app.connectors.microsoft_graph import MicrosoftGraphError
from app.connectors.sharepoint import SharePointConnector
from app.connectors.teams import TeamsConnector
from app.connectors.azure_devops import (
    AzureDevOpsConnector,
    AzureDevOpsError,
)
from fastapi.middleware.cors import CORSMiddleware
from app.chat_router import router as chat_router

app = FastAPI(
    title="Source Systems Connector PoC",
    version="0.1.0",
    description="Point 01: Source system connectivity",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "project": "source-systems-poc",
        "scope": "source_systems_only",
    }


# ==========================================
# File Share Connector Endpoints
# ==========================================
@app.get("/file-share/files")
def list_files(
    path: str = Query(
        default="",
        description="Relative path inside configured root",
    ),
):
    connector = get_connector()
    return connector.list_directory(path)


@app.get("/file-share/download")
def download_file(
    path: str = Query(..., description="Relative file path inside configured root")
):
    connector = get_connector()
    file_path = connector.get_file(path)
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )


# ==========================================
# LMS Connector Endpoints (Mock / Modular)
# ==========================================
@app.get("/lms/courses")
def lms_list_courses():
    connector = get_lms_connector()
    return connector.list_courses()


@app.get("/lms/courses/{course_id}/modules")
def lms_list_modules(course_id: str):
    connector = get_lms_connector()
    return connector.list_modules(course_id)


@app.get("/lms/courses/{course_id}/files")
def lms_list_course_files(course_id: str):
    connector = get_lms_connector()
    return connector.list_course_files(course_id)


@app.get("/lms/files/{file_id}/download")
def lms_download_file(file_id: str):
    connector = get_lms_connector()
    file_path = connector.get_file(file_id)
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )


# ==========================================
# GitHub Connector Endpoints (Real GitHub API)
# ==========================================
@app.get("/github/repos")
def list_github_repositories(
    visibility: str = Query(default="all"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
):
    connector = get_github_connector()
    return connector.list_repositories(
        visibility=visibility,
        page=page,
        per_page=per_page,
    )


@app.get("/github/repos/{owner}/{repo}/contents")
def list_github_contents(
    owner: str,
    repo: str,
    path: str = Query(default=""),
    ref: str | None = Query(default=None),
):
    connector = get_github_connector()
    return connector.list_contents(owner, repo, path, ref)


@app.get("/github/repos/{owner}/{repo}/file")
def download_github_file(
    owner: str,
    repo: str,
    path: str = Query(...),
    ref: str | None = Query(default=None),
):
    connector = get_github_connector()
    content, filename = connector.download_file(owner, repo, path, ref)
    safe_filename = filename.replace('"', "").replace("\r", "").replace("\n", "")
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"'
        },
    )


# ==========================================
# Gmail Connector Endpoints (Google OAuth2 + Gmail API)
# ==========================================
@app.get("/gmail/auth/login")
def gmail_login():
    connector = get_gmail_connector()
    auth_url = connector.get_authorization_url()
    return RedirectResponse(url=auth_url)


@app.get("/gmail/callback")
def gmail_callback(code: str = Query(...), state: str = Query(default="")):
    connector = get_gmail_connector()
    connector.exchange_code_for_token(code)
    return RedirectResponse(url="http://localhost:5173/?connected=gmail")


@app.get("/gmail/status")
def gmail_status():
    connector = get_gmail_connector()
    return connector.get_status()


@app.get("/gmail/messages")
def gmail_list_messages(
    max_results: int = Query(default=10, ge=1, le=50),
    q: str = Query(default="", description="Search query e.g. from:someone or has:attachment"),
):
    connector = get_gmail_connector()
    return connector.list_messages(max_results=max_results, q=q)


@app.get("/gmail/messages/{message_id}")
def gmail_get_message(message_id: str):
    connector = get_gmail_connector()
    return connector.get_message(message_id)


@app.get("/gmail/messages/{message_id}/open")
def gmail_open_in_web(message_id: str):
    connector = get_gmail_connector()
    msg = connector.get_message(message_id)
    thread_id = msg.get("thread_id") or message_id
    status = connector.get_status()
    user_email = status.get("email_address", "")
    target_url = (
        f"https://mail.google.com/mail/u/{user_email}/#all/{thread_id}"
        if user_email
        else f"https://mail.google.com/mail/#all/{thread_id}"
    )
    return RedirectResponse(url=target_url)


@app.get("/gmail/messages/{message_id}/attachments/{attachment_id}")
def gmail_download_attachment(
    message_id: str,
    attachment_id: str,
    filename: str = Query(default="attachment"),
):
    connector = get_gmail_connector()
    content, safe_filename = connector.download_attachment(message_id, attachment_id, filename)
    clean_filename = safe_filename.replace('"', "").replace("\r", "").replace("\n", "")
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{clean_filename}"'},
    )


# ==========================================
# Google Drive Connector Endpoints
# ==========================================
@app.get("/google-drive/auth/login")
def google_drive_login():
    connector = get_google_drive_connector()
    auth_url = connector.get_authorization_url()
    return RedirectResponse(url=auth_url)


@app.get("/google-drive/callback")
def google_drive_callback(code: str = Query(...), state: str = Query(default="")):
    connector = get_google_drive_connector()
    connector.exchange_code_for_token(code)
    return RedirectResponse(url="http://localhost:5173/?connected=google_drive")


@app.get("/google-drive/status")
def google_drive_status():
    connector = get_google_drive_connector()
    return connector.get_status()


@app.get("/google-drive/files")
def google_drive_list_files(
    max_results: int = Query(default=10, ge=1, le=100),
    q: str = Query(default="", description="Search query e.g. name contains 'project'"),
):
    connector = get_google_drive_connector()
    return connector.list_files(max_results=max_results, q=q)


@app.get("/google-drive/files/{file_id}")
def google_drive_get_file(file_id: str):
    connector = get_google_drive_connector()
    return connector.get_file_metadata(file_id)


@app.get("/google-drive/files/{file_id}/download")
def google_drive_download(file_id: str):
    connector = get_google_drive_connector()
    content, filename = connector.download_file(file_id)
    clean_filename = filename.replace('"', "").replace("\r", "").replace("\n", "")
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{clean_filename}"'},
    )


# ==========================================
# Google Chat Connector Endpoints
# ==========================================
@app.get("/google-chat/auth/login")
def google_chat_login():
    connector = get_google_chat_connector()
    auth_url = connector.get_authorization_url()
    return RedirectResponse(url=auth_url)


@app.get("/google-chat/callback")
def google_chat_callback(code: str = Query(...), state: str = Query(default="")):
    connector = get_google_chat_connector()
    connector.exchange_code_for_token(code)
    return RedirectResponse(url="http://localhost:5173/?connected=google_chat")


@app.get("/google-chat/status")
def google_chat_status():
    connector = get_google_chat_connector()
    return connector.get_status()


@app.get("/google-chat/spaces")
def google_chat_list_spaces(page_size: int = Query(default=30, ge=1, le=100)):
    connector = get_google_chat_connector()
    return connector.list_spaces(page_size=page_size)


@app.get("/google-chat/spaces/{space_id}/messages")
def google_chat_list_messages(space_id: str, page_size: int = Query(default=20, ge=1, le=50)):
    connector = get_google_chat_connector()
    return connector.list_messages(space_name=space_id, page_size=page_size)


@app.get("/google-chat/messages/search")
def google_chat_search_messages(
    query: str = Query(default="", description="Search query terms or sender"),
    max_results: int = Query(default=15, ge=1, le=50),
):
    connector = get_google_chat_connector()
    return connector.search_messages(query=query, max_results=max_results)


# ==========================================
# ServiceNow Connector Endpoints
# ==========================================
@app.get("/servicenow/status")
def servicenow_status():
    connector = get_servicenow_connector()
    return connector.get_status()


@app.get("/servicenow/incidents")
def servicenow_list_incidents(
    max_results: int = Query(default=10, ge=1, le=100),
    query: str = Query(default="", description="ServiceNow query string or filter"),
):
    connector = get_servicenow_connector()
    return connector.list_incidents(max_results=max_results, query=query)


@app.get("/servicenow/incidents/{sys_id}")
def servicenow_get_incident(sys_id: str):
    connector = get_servicenow_connector()
    return connector.get_incident(sys_id)


@app.get("/servicenow/requests")
def servicenow_list_requests(
    max_results: int = Query(default=10, ge=1, le=100),
    query: str = Query(default="", description="ServiceNow query string or filter"),
):
    connector = get_servicenow_connector()
    return connector.list_requests(max_results=max_results, query=query)


@app.get("/servicenow/knowledge")
def servicenow_search_knowledge(
    query: str = Query(default="", description="Search query for knowledge articles"),
    max_results: int = Query(default=10, ge=1, le=100),
):
    connector = get_servicenow_connector()
    return connector.search_knowledge(query=query, max_results=max_results)


# ==========================================
# Jira Connector Endpoints
# ==========================================
@app.get("/jira/status")
def jira_status():
    connector = get_jira_connector()
    return connector.get_status()


@app.get("/jira/issues")
def jira_search_issues(
    jql: str = Query(default="", description="JQL query to search issues"),
    max_results: int = Query(default=10, ge=1, le=50, description="Maximum number of issues to return"),
):
    connector = get_jira_connector()
    return connector.search_issues(jql=jql, max_results=max_results)


@app.get("/jira/issues/{issue_key}")
def jira_get_issue(issue_key: str):
    connector = get_jira_connector()
    return connector.get_issue(issue_key)


@app.get("/jira/projects")
def jira_list_projects():
    connector = get_jira_connector()
    return connector.list_projects()


# ==========================================
# Salesforce Connector Endpoints
# ==========================================
@app.get("/salesforce/auth/login")
def salesforce_login():
    connector = get_salesforce_connector()
    auth_url = connector.get_authorization_url()
    return RedirectResponse(url=auth_url)


@app.get("/salesforce/callback")
def salesforce_callback(code: str = Query(...), state: str = Query(default="sf_auth_state")):
    connector = get_salesforce_connector()
    connector.exchange_code_for_token(code)
    return RedirectResponse(url="http://localhost:5173/?connected=salesforce")


@app.get("/salesforce/status")
def salesforce_status():
    try:
        connector = get_salesforce_connector()
        return connector.get_status()
    except HTTPException as exc:
        return {"authenticated": False, "detail": exc.detail}


@app.get("/salesforce/accounts")
def salesforce_list_accounts(
    max_results: int = Query(default=10, ge=1, le=100),
    search: str = Query(default="", description="Search term for account name"),
):
    connector = get_salesforce_connector()
    return connector.list_accounts(max_results=max_results, search_term=search)


@app.get("/salesforce/leads")
def salesforce_list_leads(
    max_results: int = Query(default=10, ge=1, le=100),
    search: str = Query(default="", description="Search term for lead name, company, or email"),
):
    connector = get_salesforce_connector()
    return connector.list_leads(max_results=max_results, search_term=search)


@app.get("/salesforce/opportunities")
def salesforce_list_opportunities(
    max_results: int = Query(default=10, ge=1, le=100),
    search: str = Query(default="", description="Search term for opportunity name"),
):
    connector = get_salesforce_connector()
    return connector.list_opportunities(max_results=max_results, search_term=search)


@app.get("/salesforce/records/{sobject}/{record_id}")
def salesforce_get_record(sobject: str, record_id: str):
    connector = get_salesforce_connector()
    return connector.get_record(sobject_type=sobject, record_id=record_id)


# ==========================================
# Microsoft SharePoint Connector Endpoints
# ==========================================
@app.get("/sharepoint/sites")
def sharepoint_sites(search: str | None = None):
    try:
        return {"value": SharePointConnector().list_sites(search)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MicrosoftGraphError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/sharepoint/sites/{site_id}/drives")
def sharepoint_drives(site_id: str):
    try:
        return {"value": SharePointConnector().list_drives(site_id)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MicrosoftGraphError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/sharepoint/drives/{drive_id}/items")
def sharepoint_items(
    drive_id: str,
    folder_id: str = Query(default="root"),
):
    try:
        return {
            "value": SharePointConnector().list_items(drive_id, folder_id)
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MicrosoftGraphError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/sharepoint/drives/{drive_id}/items/{item_id}/download")
def sharepoint_download(drive_id: str, item_id: str):
    try:
        content, filename = SharePointConnector().download_item(
            drive_id, item_id
        )
        safe_filename = filename.replace("\r", "").replace("\n", "")
        headers = {
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{quote(safe_filename, safe='')}"
            )
        }
        return StreamingResponse(
            BytesIO(content),
            media_type="application/octet-stream",
            headers=headers,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MicrosoftGraphError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# ==========================================
# Microsoft Teams Connector Endpoints
# ==========================================
@app.get("/teams/list")
def teams_list():
    try:
        return {"value": TeamsConnector().list_teams()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MicrosoftGraphError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/teams/{team_id}/channels")
def teams_channels(team_id: str):
    try:
        return {"value": TeamsConnector().list_channels(team_id)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MicrosoftGraphError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/teams/{team_id}/channels/{channel_id}/messages")
def teams_messages(
    team_id: str,
    channel_id: str,
    limit: int = Query(default=50, ge=1, le=100),
):
    try:
        return {
            "value": TeamsConnector().list_channel_messages(
                team_id, channel_id, limit
            )
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MicrosoftGraphError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# ==========================================
# Azure DevOps Repos Endpoints
# ==========================================
@app.get("/azure-devops/projects")
def azure_devops_projects():
    try:
        connector = AzureDevOpsConnector()
        return {"value": connector.list_projects()}
    except AzureDevOpsError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/azure-devops/projects/{project}/repos")
def azure_devops_repositories(project: str):
    try:
        connector = AzureDevOpsConnector()
        return {"value": connector.list_repositories(project)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AzureDevOpsError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/azure-devops/projects/{project}/repos/{repo_id}/items")
def azure_devops_items(
    project: str,
    repo_id: str,
    path: str = Query(default="/"),
    recursion_level: str = Query(default="Full"),
):
    try:
        connector = AzureDevOpsConnector()
        items = connector.list_items(
            project=project,
            repository_id=repo_id,
            path=path,
            recursion_level=recursion_level,
        )
        return {"value": items}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AzureDevOpsError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/azure-devops/projects/{project}/repos/{repo_id}/file")
def azure_devops_file(
    project: str,
    repo_id: str,
    path: str = Query(..., description="Repository file path"),
):
    try:
        connector = AzureDevOpsConnector()
        content = connector.get_file(
            project=project,
            repository_id=repo_id,
            path=path,
        )
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment",
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AzureDevOpsError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc