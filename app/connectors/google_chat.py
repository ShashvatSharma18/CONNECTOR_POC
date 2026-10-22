import base64
import email.utils
import html
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOKEN_CACHE_FILE = PROJECT_ROOT / ".google_chat_token.json"

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
CHAT_API_BASE = "https://chat.googleapis.com/v1"

SCOPES = [
    "https://www.googleapis.com/auth/chat.spaces.readonly",
    "https://www.googleapis.com/auth/chat.messages.readonly",
    "https://www.googleapis.com/auth/chat.memberships.readonly",
]


class GoogleChatConnector:
    """Read-only Google Chat connector using Google Workspace OAuth 2.0."""

    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv(
            "GOOGLE_CHAT_REDIRECT_URI",
            os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/gmail/callback"),
        )

        if not self.client_id or not self.client_secret:
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not configured in .env",
            )

    def get_authorization_url(self, state: str = "gchat_auth_state") -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> dict:
        data = urllib.parse.urlencode({
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }).encode("utf-8")

        req = urllib.request.Request(
            TOKEN_ENDPOINT,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                token_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise HTTPException(
                status_code=400,
                detail=f"Token exchange failed: {err_body}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to reach Google OAuth: {str(e)}",
            )

        expires_in = token_data.get("expires_in", 3600)
        token_data["expires_at"] = time.time() + expires_in

        # If previous refresh token exists and new one is not returned, preserve it
        if TOKEN_CACHE_FILE.exists():
            try:
                with open(TOKEN_CACHE_FILE, "r") as f:
                    old_tokens = json.load(f)
                    if "refresh_token" in old_tokens and "refresh_token" not in token_data:
                        token_data["refresh_token"] = old_tokens["refresh_token"]
            except Exception:
                pass

        with open(TOKEN_CACHE_FILE, "w") as f:
            json.dump(token_data, f, indent=2)

        return token_data

    def _get_valid_token(self) -> str:
        if not TOKEN_CACHE_FILE.exists():
            raise HTTPException(
                status_code=401,
                detail="Not authenticated with Google Chat. Visit /google-chat/auth/login",
            )

        try:
            with open(TOKEN_CACHE_FILE, "r") as f:
                token_data = json.load(f)
        except Exception:
            raise HTTPException(
                status_code=401,
                detail="Invalid token cache. Re-authenticate via /google-chat/auth/login",
            )

        access_token = token_data.get("access_token")
        expires_at = token_data.get("expires_at", 0)
        refresh_token = token_data.get("refresh_token")

        if time.time() > (expires_at - 60):
            if not refresh_token:
                raise HTTPException(
                    status_code=401,
                    detail="Google Chat token expired and no refresh token available. Visit /google-chat/auth/login",
                )
            access_token = self._refresh_access_token(refresh_token)

        return access_token

    def _refresh_access_token(self, refresh_token: str) -> str:
        data = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }).encode("utf-8")

        req = urllib.request.Request(
            TOKEN_ENDPOINT,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                new_data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise HTTPException(
                status_code=401,
                detail=f"Failed to refresh Google Chat token: {str(exc)}. Please re-authenticate.",
            )

        with open(TOKEN_CACHE_FILE, "r") as f:
            tokens = json.load(f)

        tokens["access_token"] = new_data["access_token"]
        tokens["expires_at"] = time.time() + new_data.get("expires_in", 3600)

        with open(TOKEN_CACHE_FILE, "w") as f:
            json.dump(tokens, f, indent=2)

        return new_data["access_token"]

    def _api_request(self, endpoint: str, params: dict = None) -> dict:
        token = self._get_valid_token()
        url = f"{CHAT_API_BASE}{endpoint}" if endpoint.startswith("/") else f"{CHAT_API_BASE}/{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            logger.error(f"Google Chat API error HTTP {exc.code}: {err_body}")
            try:
                err_json = json.loads(err_body)
                err_msg = err_json.get("error", {}).get("message", err_body)
            except Exception:
                err_msg = err_body

            if exc.code == 401:
                raise HTTPException(401, f"Google Chat access token is invalid or expired: {err_msg}")
            if exc.code == 403:
                raise HTTPException(403, f"Google Chat API access denied: {err_msg}")
            if exc.code == 404:
                raise HTTPException(404, f"Google Chat resource not found: {err_msg}")
            raise HTTPException(502, f"Google Chat API error HTTP {exc.code}: {err_msg}")
        except Exception as exc:
            raise HTTPException(502, f"Unable to reach Google Chat API: {str(exc)}")

    def get_status(self) -> dict:
        if not TOKEN_CACHE_FILE.exists():
            return {
                "authenticated": False,
                "message": "Not authenticated. Visit /google-chat/auth/login",
            }
        try:
            # Test listing spaces
            res = self._api_request("/spaces", {"pageSize": 10})
            spaces = res.get("spaces", [])
            return {
                "authenticated": True,
                "spaces_count": len(spaces),
                "status": "connected",
            }
        except HTTPException as e:
            return {"authenticated": False, "detail": e.detail}
        except Exception as e:
            return {"authenticated": False, "detail": str(e)}

    def list_spaces(self, page_size: int = 30) -> dict:
        """List accessible Google Chat spaces, rooms, and group conversations."""
        res = self._api_request("/spaces", {"pageSize": min(max(page_size, 1), 100)})
        raw_spaces = res.get("spaces", [])
        cleaned_spaces = []
        for s in raw_spaces:
            name = s.get("name", "")
            space_id = name.replace("spaces/", "")
            display_name = s.get("displayName") or ("Direct Message" if s.get("spaceType") == "DIRECT_MESSAGE" else "Group Chat")
            cleaned_spaces.append({
                "id": space_id,
                "name": name,
                "displayName": display_name,
                "type": s.get("spaceType", s.get("type", "SPACE")),
                "threadingState": s.get("spaceThreadingState"),
                "webLink": f"https://mail.google.com/chat/u/0/#chat/space/{space_id}",
            })
        return {
            "spaces": cleaned_spaces,
            "nextPageToken": res.get("nextPageToken"),
        }

    def list_messages(self, space_name: str, page_size: int = 20) -> dict:
        """List messages inside a specific space or room."""
        # space_name can be 'spaces/AAAA...' or just 'AAAA...'
        if not space_name.startswith("spaces/"):
            space_name = f"spaces/{space_name}"

        res = self._api_request(f"/{space_name}/messages", {"pageSize": min(max(page_size, 1), 50)})
        raw_msgs = res.get("messages", [])
        cleaned_msgs = []
        for m in raw_msgs:
            sender = m.get("sender", {})
            sender_name = sender.get("displayName", "User")
            create_time = m.get("createTime", "")
            cleaned_msgs.append({
                "name": m.get("name"),
                "text": m.get("text", ""),
                "sender": sender_name,
                "sender_type": sender.get("type", "HUMAN"),
                "createTime": create_time,
                "threadName": m.get("thread", {}).get("name"),
            })
        return {
            "messages": cleaned_msgs,
            "nextPageToken": res.get("nextPageToken"),
        }

    def search_messages(self, query: str = "", max_results: int = 15) -> dict:
        """
        Searches recent messages across accessible spaces for query terms or sender.
        """
        spaces_res = self.list_spaces(page_size=10)
        spaces = spaces_res.get("spaces", [])
        matched = []

        stop_terms = {"latest", "recent", "last", "newest", "today", "yesterday", "chat", "chats", "message", "messages"}
        q_terms = [w.lower() for w in query.split() if len(w) > 2 and w.lower() not in stop_terms] if query else []

        for sp in spaces:
            sp_name = sp["name"]
            sp_display = sp["displayName"]
            try:
                msg_res = self.list_messages(sp_name, page_size=20)
                msgs = msg_res.get("messages", [])
                for m in msgs:
                    text = m.get("text", "")
                    sender = m.get("sender", "")
                    content_lower = f"{sender} {text}".lower()

                    if not q_terms or any(term in content_lower for term in q_terms):
                        matched.append({
                            "space_id": sp["id"],
                            "space_name": sp_display,
                            "sender": sender,
                            "text": text,
                            "createTime": m.get("createTime"),
                            "link": sp["webLink"],
                        })
                        if len(matched) >= max_results:
                            break
            except Exception as e:
                logger.debug("Could not read messages from space %s: %s", sp_name, str(e))

            if len(matched) >= max_results * 2:
                break

        matched.sort(key=lambda x: x.get("createTime") or "", reverse=True)
        result = matched[:max_results]
        return {"messages": result, "total": len(result)}


def get_google_chat_connector() -> GoogleChatConnector:
    return GoogleChatConnector()
