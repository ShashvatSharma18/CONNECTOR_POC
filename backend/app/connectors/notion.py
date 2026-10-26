import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()
logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionConnector:
    """Read-only Notion connector for searching pages, databases, and reading block text."""

    def __init__(self, token: str | None = None):
        self.token = (token or os.getenv("NOTION_API_KEY") or "").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.token)

    def _api_request(self, endpoint: str, data: dict[str, Any] | None = None, method: str = "POST") -> dict[str, Any]:
        if not self.is_configured:
            raise HTTPException(500, "Notion connector is not configured. Missing NOTION_API_KEY.")

        url = f"{NOTION_API_BASE}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
            "User-Agent": "source-systems-connector-poc",
        }

        body_bytes = json.dumps(data or {}).encode("utf-8") if (data is not None or method == "POST") else None
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_text = resp.read().decode("utf-8")
                return json.loads(resp_text)
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            logger.error("Notion HTTP error %d: %s", exc.code, err_body)
            raise HTTPException(status_code=exc.code, detail=f"Notion API error: {err_body}")
        except Exception as exc:
            logger.error("Notion unexpected error: %s", str(exc))
            raise HTTPException(status_code=502, detail=f"Notion connection error: {str(exc)}")

    def get_status(self) -> dict[str, Any]:
        """Test token validity with a lightweight search query."""
        if not self.is_configured:
            return {"configured": False, "authenticated": False, "message": "NOTION_API_KEY not configured"}
        try:
            res = self._api_request("/search", data={"page_size": 1})
            return {
                "configured": True,
                "authenticated": True,
                "total_accessible": len(res.get("results", [])),
                "message": "Connected to Notion workspace successfully",
            }
        except Exception as exc:
            return {"configured": True, "authenticated": False, "error": str(exc)}

    def search(self, query: str = "", limit: int = 10) -> list[dict[str, Any]]:
        """Search pages and databases in the Notion workspace."""
        payload: dict[str, Any] = {"page_size": min(max(limit, 1), 30)}
        if query and query.strip():
            payload["query"] = query.strip()

        res = self._api_request("/search", data=payload)
        results = []
        for item in res.get("results", []):
            item_type = item.get("object")  # "page" or "database"
            title = ""
            if item_type == "page":
                # Extract page title from properties
                props = item.get("properties", {})
                for p_val in props.values():
                    if p_val.get("id") == "title" or p_val.get("type") == "title":
                        title_arr = p_val.get("title", [])
                        if title_arr:
                            title = title_arr[0].get("plain_text", "")
                            break
            elif item_type == "database":
                title_arr = item.get("title", [])
                if title_arr:
                    title = title_arr[0].get("plain_text", "")

            results.append({
                "id": item.get("id"),
                "type": item_type,
                "title": title or "(Untitled)",
                "url": item.get("url"),
                "created_time": item.get("created_time"),
                "last_edited_time": item.get("last_edited_time"),
            })
        return results

    def get_page_content(self, page_id: str, limit: int = 50) -> str:
        """Fetch child blocks of a page and concatenate text."""
        endpoint = f"/blocks/{page_id}/children?page_size={min(limit, 100)}"
        res = self._api_request(endpoint, method="GET")
        text_lines = []
        for block in res.get("results", []):
            b_type = block.get("type")
            b_content = block.get(b_type, {})
            rich_texts = b_content.get("rich_text", [])
            line = "".join([t.get("plain_text", "") for t in rich_texts]).strip()
            if line:
                if b_type.startswith("heading_1"):
                    text_lines.append(f"# {line}")
                elif b_type.startswith("heading_2"):
                    text_lines.append(f"## {line}")
                elif b_type.startswith("bulleted_list_item"):
                    text_lines.append(f"- {line}")
                else:
                    text_lines.append(line)
        return "\n\n".join(text_lines)


def get_notion_connector() -> NotionConnector:
    return NotionConnector()
