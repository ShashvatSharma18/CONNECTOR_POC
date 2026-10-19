from io import BytesIO
from urllib.parse import quote
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response, RedirectResponse, StreamingResponse

from app.connectors.file_share import get_connector
from app.connectors.lms import get_lms_connector
from app.connectors.github import get_github_connector
from app.connectors.gmail import get_gmail_connector
from app.connectors.microsoft_graph import MicrosoftGraphError
from app.connectors.sharepoint import SharePointConnector
from app.connectors.teams import TeamsConnector

app = FastAPI(
    title="Source Systems Connector PoC",
    version="0.1.0",
    description="Point 01: Source system connectivity",
)


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
    return {
        "status": "authenticated",
        "message": "Gmail authentication successful! You can now access /gmail/messages and /gmail/status",
    }


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