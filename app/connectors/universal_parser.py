import os
import logging
from typing import Any
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_PARSER_URL = os.getenv("UNIVERSAL_PARSER_URL", "http://127.0.0.1:8000")
DEFAULT_PARSER_MODE = os.getenv("UNIVERSAL_PARSER_MODE", "balanced")


class UniversalParserConnector:
    """
    Connector for Parse and Furious (Universal Document Parser).
    Provides high-precision multimodal parsing for PDF, Office (DOCX, XLSX, PPTX),
    Images/OCR, CSV, EML with attachments, and HTML.
    Produces pre-grounded RAG chunks and structured tables with prompt-injection defense.
    """

    def __init__(self, base_url: str = DEFAULT_PARSER_URL, default_mode: str = DEFAULT_PARSER_MODE):
        self.base_url = base_url.rstrip("/")
        self.default_mode = default_mode

    def get_status(self) -> dict[str, Any]:
        """Check if Universal Parser service is reachable and return capabilities."""
        try:
            resp = requests.get(f"{self.base_url}/v1/ready", timeout=3)
            if resp.status_code == 200 and resp.json().get("status") == "ready":
                # Fetch capabilities
                cap_resp = requests.get(f"{self.base_url}/v1/capabilities", timeout=3)
                caps = cap_resp.json() if cap_resp.status_code == 200 else {}
                return {
                    "is_connected": True,
                    "status": "Live",
                    "base_url": self.base_url,
                    "default_mode": caps.get("default_mode", self.default_mode),
                    "modes": caps.get("modes", ["fast", "balanced", "max_accuracy", "offline"]),
                    "export_formats": caps.get("export_formats", ["chunks", "markdown", "text", "html", "tables", "json"]),
                    "supported_formats": [
                        "PDF (Born-Digital & Scanned)",
                        "Word (DOCX, DOC)",
                        "Excel (XLSX, XLS)",
                        "PowerPoint (PPTX, PPT)",
                        "Images (OCR via Tesseract)",
                        "Emails (EML with Attachments)",
                        "CSV & Structured Tables",
                        "HTML & Web Pages",
                    ],
                    "features": [
                        "Cell-by-cell table grounding",
                        "Prompt-injection & invisible text defense",
                        "Multi-parser ensemble fusion",
                        "Direct RAG token-bounded chunks",
                    ],
                    "version": caps.get("version", "0.1.0"),
                }
        except Exception as e:
            logger.warning("Universal Parser health check failed: %s", str(e))

        return {
            "is_connected": False,
            "status": "Offline",
            "base_url": self.base_url,
            "error": "Parser service unreachable at " + self.base_url,
            "modes": ["fast", "balanced", "max_accuracy"],
            "supported_formats": ["PDF", "DOCX", "XLSX", "PPTX", "Images", "CSV", "HTML"],
        }

    def parse_file(
        self,
        file_bytes: bytes,
        filename: str,
        mode: str | None = None,
        export_format: str = "chunks",
        pages: str | None = None,
    ) -> dict[str, Any]:
        """
        Parse an uploaded file or file buffer using Parse and Furious ensemble.
        export_format can be: 'chunks', 'markdown', 'tables', 'json', 'text', 'html'.
        """
        active_mode = mode or self.default_mode
        url = f"{self.base_url}/v1/parse"
        params: dict[str, Any] = {
            "mode": active_mode,
            "format": export_format,
        }
        if pages:
            params["pages"] = pages

        files = {
            "file": (filename, file_bytes, "application/octet-stream"),
        }

        try:
            resp = requests.post(url, params=params, files=files, timeout=90)
            if resp.status_code == 200:
                result = resp.json()
                return {
                    "success": True,
                    "filename": filename,
                    "mode": active_mode,
                    "format": export_format,
                    "data": result,
                }
            logger.error("Universal parser error (%d): %s", resp.status_code, resp.text)
            return {
                "success": False,
                "error": f"Parser error status {resp.status_code}: {resp.text[:300]}",
            }
        except Exception as e:
            logger.error("Exception invoking Universal Parser: %s", str(e))
            return {
                "success": False,
                "error": f"Failed to connect to parser service: {str(e)}",
            }

    def extract_text_and_tables(
        self,
        file_bytes: bytes,
        filename: str,
        mode: str = "balanced",
    ) -> dict[str, Any]:
        """
        Convenience method: parses document and returns clean text representation,
        extracted structured tables, and RAG chunks.
        """
        res = self.parse_file(file_bytes, filename, mode=mode, export_format="chunks")
        if not res.get("success"):
            return {
                "text": f"Error parsing document {filename}: {res.get('error')}",
                "chunks": [],
                "tables": [],
                "elements_count": 0,
            }

        data = res.get("data", {})
        elements = data.get("elements", {})
        chunks = []
        tables = []
        text_lines = []

        # If data itself contains chunks or elements
        for el_id, el in elements.items():
            el_type = el.get("type", "paragraph")
            el_text = el.get("text", "").strip()
            if el_type == "table":
                tables.append({
                    "id": el_id,
                    "text": el_text,
                    "order": el.get("order", 0),
                })
            if el_text:
                text_lines.append(el_text)
                chunks.append({
                    "id": el_id,
                    "type": el_type,
                    "content": el_text,
                    "source": el.get("source", []),
                })

        # Check validations (e.g. hidden text)
        validations = data.get("validations", [])
        hidden_text_flag = False
        for v in validations:
            if v.get("check") == "hidden_text" and v.get("status") == "fail":
                hidden_text_flag = True

        combined_text = "\n\n".join(text_lines)
        return {
            "success": True,
            "filename": filename,
            "mode": mode,
            "text": combined_text,
            "chunks": chunks,
            "tables": tables,
            "elements_count": len(elements),
            "hidden_text_detected": hidden_text_flag,
            "duration_ms": data.get("pipeline", {}).get("duration_ms", 0),
        }

    def parse_url(self, url: str, mode: str = "balanced", export_format: str = "markdown") -> dict[str, Any]:
        """Parse content from a web URL using Universal Parser."""
        active_mode = mode or self.default_mode
        endpoint = f"{self.base_url}/v1/parse/url"
        try:
            resp = requests.post(
                endpoint,
                params={"mode": active_mode, "format": export_format},
                json={"url": url},
                timeout=60,
            )
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            return {"success": False, "error": f"Error {resp.status_code}: {resp.text[:300]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


_connector_instance: UniversalParserConnector | None = None


def get_universal_parser_connector() -> UniversalParserConnector:
    """Singleton getter for UniversalParserConnector."""
    global _connector_instance
    if _connector_instance is None:
        _connector_instance = UniversalParserConnector()
    return _connector_instance
