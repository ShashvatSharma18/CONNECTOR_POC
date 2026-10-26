import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOKEN_CACHE_FILE = PROJECT_ROOT / ".salesforce_token.json"

AUTH_ENDPOINT = "https://login.salesforce.com/services/oauth2/authorize"
TOKEN_ENDPOINT = "https://login.salesforce.com/services/oauth2/token"
API_VERSION = "v59.0"


class SalesforceConnector:
    """Salesforce REST API connector using OAuth 2.0 Web Server flow."""

    def __init__(self):
        self.instance_url = os.getenv("SALESFORCE_INSTANCE_URL", "").strip().rstrip("/")
        self.client_id = os.getenv("SALESFORCE_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("SALESFORCE_CLIENT_SECRET", "").strip()
        self.redirect_uri = os.getenv(
            "SALESFORCE_REDIRECT_URI", "http://localhost:8000/salesforce/callback"
        ).strip()

        if not self.client_id or not self.client_secret:
            raise HTTPException(
                status_code=500,
                detail="SALESFORCE_CLIENT_ID or SALESFORCE_CLIENT_SECRET not configured in .env",
            )

    def get_authorization_url(self, state: str = "sf_auth_state") -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "prompt": "consent",
        }
        return f"{AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> dict:
        data = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
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
                detail=f"Salesforce token exchange failed: {err_body}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to reach Salesforce OAuth: {str(e)}",
            )

        # Salesforce returns issued_at (epoch ms as string) and optionally expires_in
        expires_in = token_data.get("expires_in", 7200)
        token_data["expires_at"] = time.time() + float(expires_in)

        # Preserve refresh_token and instance_url if already in cache and not returned
        if TOKEN_CACHE_FILE.exists():
            try:
                with open(TOKEN_CACHE_FILE, "r") as f:
                    old_tokens = json.load(f)
                    if "refresh_token" in old_tokens and "refresh_token" not in token_data:
                        token_data["refresh_token"] = old_tokens["refresh_token"]
                    if "instance_url" in old_tokens and "instance_url" not in token_data:
                        token_data["instance_url"] = old_tokens["instance_url"]
            except Exception:
                pass

        if self.instance_url and not token_data.get("instance_url"):
            token_data["instance_url"] = self.instance_url

        with open(TOKEN_CACHE_FILE, "w") as f:
            json.dump(token_data, f, indent=2)

        return token_data

    def _get_valid_token(self) -> str:
        if not TOKEN_CACHE_FILE.exists():
            raise HTTPException(
                status_code=401,
                detail="Salesforce is not authenticated. Please authenticate by visiting /salesforce/auth/login",
            )

        try:
            with open(TOKEN_CACHE_FILE, "r") as f:
                token_data = json.load(f)
        except Exception:
            raise HTTPException(
                status_code=401,
                detail="Invalid token cache. Re-authenticate via /salesforce/auth/login",
            )

        access_token = token_data.get("access_token")
        expires_at = token_data.get("expires_at", 0)
        refresh_token = token_data.get("refresh_token")

        if not access_token:
            raise HTTPException(
                status_code=401,
                detail="Salesforce access token missing. Please re-authenticate via /salesforce/auth/login",
            )

        # Refresh if token will expire in next 60 seconds
        if time.time() > (expires_at - 60):
            if not refresh_token:
                return access_token
            access_token = self._refresh_access_token(refresh_token)

        return access_token

    def _refresh_access_token(self, refresh_token: str) -> str:
        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
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
                detail=f"Failed to refresh Salesforce token: {str(exc)}. Please re-authenticate.",
            )

        with open(TOKEN_CACHE_FILE, "r") as f:
            tokens = json.load(f)

        tokens["access_token"] = new_data["access_token"]
        expires_in = new_data.get("expires_in", 7200)
        tokens["expires_at"] = time.time() + float(expires_in)
        if "instance_url" in new_data:
            tokens["instance_url"] = new_data["instance_url"]

        with open(TOKEN_CACHE_FILE, "w") as f:
            json.dump(tokens, f, indent=2)

        return tokens["access_token"]

    def _get_instance_url(self) -> str:
        if self.instance_url:
            return self.instance_url
        if TOKEN_CACHE_FILE.exists():
            try:
                with open(TOKEN_CACHE_FILE, "r") as f:
                    data = json.load(f)
                    if data.get("instance_url"):
                        return data["instance_url"].rstrip("/")
            except Exception:
                pass
        raise HTTPException(
            status_code=500,
            detail="Salesforce instance URL not configured and not found in token cache. Set SALESFORCE_INSTANCE_URL in .env",
        )

    def _api_request(self, endpoint: str, params: dict | None = None) -> dict:
        token = self._get_valid_token()
        instance_url = self._get_instance_url()

        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        url = f"{instance_url}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)

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
            if exc.code == 401:
                raise HTTPException(401, f"Salesforce access token is invalid or expired: {err_body}")
            if exc.code == 403:
                raise HTTPException(403, f"Salesforce API access denied or insufficient permissions: {err_body}")
            if exc.code == 404:
                raise HTTPException(404, f"Salesforce resource not found: {err_body}")
            raise HTTPException(502, f"Salesforce API error (HTTP {exc.code}): {err_body}")
        except Exception as exc:
            raise HTTPException(502, f"Unable to reach Salesforce API: {str(exc)}")

    def get_status(self) -> dict:
        if not TOKEN_CACHE_FILE.exists():
            return {
                "authenticated": False,
                "message": "Not authenticated. Visit /salesforce/auth/login",
            }
        try:
            token = self._get_valid_token()
            instance_url = self._get_instance_url()

            user_info = {}
            try:
                user_info = self._api_request("/services/oauth2/userinfo")
            except Exception:
                pass

            return {
                "authenticated": True,
                "instance_url": instance_url,
                "username": user_info.get("preferred_username") or user_info.get("email"),
                "display_name": user_info.get("name"),
                "organization_id": user_info.get("organization_id"),
            }
        except HTTPException as e:
            return {"authenticated": False, "detail": e.detail}
        except Exception as e:
            return {"authenticated": False, "detail": str(e)}

    def search_records(self, soql_query: str) -> dict:
        """Generic SOQL query execution via /services/data/v59.0/query."""
        return self._api_request(
            f"/services/data/{API_VERSION}/query",
            params={"q": soql_query},
        )

    def list_accounts(self, max_results: int = 10, search_term: str = "") -> dict:
        limit = min(max(max_results, 1), 100)
        query = "SELECT Id, Name, Type, Industry, Phone, Website, CreatedDate FROM Account"
        if search_term:
            clean_term = search_term.replace("'", "\\'")
            query += f" WHERE Name LIKE '%{clean_term}%'"
        query += f" ORDER BY CreatedDate DESC LIMIT {limit}"

        result = self.search_records(query)
        records = result.get("records", [])
        return {
            "accounts": records,
            "records": records,
            "total_size": result.get("totalSize", len(records)),
            "done": result.get("done", True),
        }

    def list_leads(self, max_results: int = 10, search_term: str = "") -> dict:
        limit = min(max(max_results, 1), 100)
        query = "SELECT Id, Name, Title, Company, Email, Phone, Status, CreatedDate FROM Lead"
        if search_term:
            clean_term = search_term.replace("'", "\\'")
            query += (
                f" WHERE Name LIKE '%{clean_term}%' "
                f"OR Company LIKE '%{clean_term}%' "
                f"OR Email LIKE '%{clean_term}%'"
            )
        query += f" ORDER BY CreatedDate DESC LIMIT {limit}"

        result = self.search_records(query)
        records = result.get("records", [])
        return {
            "leads": records,
            "records": records,
            "total_size": result.get("totalSize", len(records)),
            "done": result.get("done", True),
        }

    def list_opportunities(self, max_results: int = 10, search_term: str = "") -> dict:
        limit = min(max(max_results, 1), 100)
        query = "SELECT Id, Name, StageName, Amount, CloseDate, Probability, Type, CreatedDate FROM Opportunity"
        if search_term:
            clean_term = search_term.replace("'", "\\'")
            query += f" WHERE Name LIKE '%{clean_term}%'"
        query += f" ORDER BY CreatedDate DESC LIMIT {limit}"

        result = self.search_records(query)
        records = result.get("records", [])
        return {
            "opportunities": records,
            "records": records,
            "total_size": result.get("totalSize", len(records)),
            "done": result.get("done", True),
        }

    def get_record(self, sobject_type: str, record_id: str) -> dict:
        clean_sobject = urllib.parse.quote(sobject_type.strip(), safe="")
        clean_id = urllib.parse.quote(record_id.strip(), safe="")
        return self._api_request(
            f"/services/data/{API_VERSION}/sobjects/{clean_sobject}/{clean_id}"
        )


def get_salesforce_connector() -> SalesforceConnector:
    return SalesforceConnector()
