import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()
logger = logging.getLogger(__name__)

SLACK_API_BASE = "https://slack.com/api"


class SlackConnector:
    """Read-only and message retrieval Slack connector using Slack Web API and Bot Token."""

    def __init__(self, token: str | None = None):
        self.token = (token or os.getenv("SLACK_BOT_TOKEN") or "").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.token)

    def _api_request(self, method: str, params: dict[str, Any] | None = None, is_post: bool = False, body: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.is_configured:
            raise HTTPException(
                status_code=500,
                detail="Slack connector is not configured. Missing SLACK_BOT_TOKEN.",
            )

        url = f"{SLACK_API_BASE}/{method}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "source-systems-connector-poc",
        }

        data = None
        if is_post:
            headers["Content-Type"] = "application/json; charset=utf-8"
            data = json.dumps(body or {}).encode("utf-8")
        elif params:
            clean_params = {k: str(v) for k, v in params.items() if v is not None and v != ""}
            if clean_params:
                url += "?" + urllib.parse.urlencode(clean_params)

        req = urllib.request.Request(url, headers=headers, data=data, method="POST" if is_post else "GET")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_text = resp.read().decode("utf-8")
                res = json.loads(resp_text)
                if not res.get("ok"):
                    error_code = res.get("error", "unknown_error")
                    raise HTTPException(status_code=400, detail=f"Slack API error: {error_code}")
                return res
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            logger.error("Slack HTTP error %d: %s", exc.code, err_body)
            raise HTTPException(status_code=exc.code, detail=f"Slack HTTP error: {err_body}")
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Slack unexpected error: %s", str(exc))
            raise HTTPException(status_code=502, detail=f"Slack connection error: {str(exc)}")

    def get_status(self) -> dict[str, Any]:
        """Verify token and return workspace/bot details."""
        if not self.is_configured:
            return {"configured": False, "authenticated": False, "message": "SLACK_BOT_TOKEN not configured"}
        try:
            auth_info = self._api_request("auth.test")
            return {
                "configured": True,
                "authenticated": True,
                "team": auth_info.get("team"),
                "team_id": auth_info.get("team_id"),
                "user": auth_info.get("user"),
                "user_id": auth_info.get("user_id"),
                "bot_id": auth_info.get("bot_id"),
            }
        except Exception as exc:
            return {"configured": True, "authenticated": False, "error": str(exc)}

    def list_channels(self, limit: int = 50, types: str = "public_channel,private_channel") -> list[dict[str, Any]]:
        """List public and private channels the bot has access to."""
        params = {"limit": min(max(limit, 1), 100), "types": types, "exclude_archived": "true"}
        res = self._api_request("conversations.list", params=params)
        channels = []
        for ch in res.get("channels", []):
            channels.append({
                "id": ch.get("id"),
                "name": ch.get("name"),
                "is_private": ch.get("is_private", False),
                "topic": ch.get("topic", {}).get("value", ""),
                "purpose": ch.get("purpose", {}).get("value", ""),
                "num_members": ch.get("num_members", 0),
            })
        return channels

    def list_messages(self, channel_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch conversation history from a given channel."""
        params = {"channel": channel_id, "limit": min(max(limit, 1), 50)}
        res = self._api_request("conversations.history", params=params)
        messages = []
        for msg in res.get("messages", []):
            messages.append({
                "ts": msg.get("ts"),
                "user": msg.get("user"),
                "text": msg.get("text", ""),
                "thread_ts": msg.get("thread_ts"),
                "reply_count": msg.get("reply_count", 0),
            })
        return messages

    def get_thread_replies(self, channel_id: str, thread_ts: str) -> list[dict[str, Any]]:
        """Fetch all messages in a thread."""
        params = {"channel": channel_id, "ts": thread_ts}
        res = self._api_request("conversations.replies", params=params)
        return res.get("messages", [])

    def search_all_channels_for_query(self, query: str, limit_per_channel: int = 15) -> list[dict[str, Any]]:
        """Search across bot's channels for messages matching query text."""
        clean_q = query.lower().strip()
        channels = self.list_channels(limit=10)
        found_messages = []

        for ch in channels:
            ch_id = ch["id"]
            ch_name = ch["name"]
            try:
                msgs = self.list_messages(ch_id, limit=limit_per_channel)
                for m in msgs:
                    txt = m.get("text", "")
                    if clean_q in txt.lower():
                        found_messages.append({
                            "channel_id": ch_id,
                            "channel_name": ch_name,
                            "text": txt,
                            "ts": m.get("ts"),
                            "user": m.get("user"),
                        })
            except Exception:
                continue

        return found_messages


def get_slack_connector() -> SlackConnector:
    return SlackConnector()
