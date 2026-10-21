import datetime
import email.utils
import html
import json
import logging
import os
import re
from typing import Any
from urllib.parse import quote
import requests
from dotenv import load_dotenv

from app.chat_history import db
from app.connectors.gmail import get_gmail_connector
from app.connectors.github import get_github_connector
from app.connectors.file_share import get_connector as get_fileshare_connector
from app.connectors.lms import get_lms_connector
from app.connectors.servicenow import get_servicenow_connector
from app.connectors.salesforce import get_salesforce_connector
from app.connectors.google_drive import get_google_drive_connector
from app.connectors.jira import get_jira_connector
from app.connectors.slack import get_slack_connector
from app.connectors.postgres import DatabaseConnector
from app.connectors.notion import get_notion_connector

load_dotenv()
logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PRIMARY_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "openai/gpt-oss-20b"

GREETING_REGEX = re.compile(
    r"^(hi+|hello+|hey+|good\s+(morning|afternoon|evening)|howdy|sup|how\s+are\s+you|thanks|thank\s+you|bye|goodbye|what\'?s\s+up)[!.,?\s]*$",
    re.IGNORECASE,
)

FOLLOWUP_REGEX = re.compile(
    r"\b(summarize|summarise|explain|more\s+details|tell\s+me\s+more|who\s+sent|what\s+about|elaborate|show\s+more|details)\b",
    re.IGNORECASE,
)


def normalize_text_for_email_search(text: str) -> str:
    """Normalize common typos for email / mail."""
    normalized = re.sub(r"\b(e-?mials?|e-?maiols?|maiols?|mials?|maill?s?|e-?mails?|mails?)\b", "email", text, flags=re.I)
    normalized = re.sub(r"\bwhats\b", "what is", normalized, flags=re.I)
    return normalized


def extract_gmail_date_time_target(text: str) -> tuple[int | None, int | None, int | None, str | None]:
    """
    Extracts target hour, minute, day, and month from user query.
    Returns (target_hour, target_minute, target_day, target_month_abbr).
    e.g. 'onn date 16 oct 2:22' -> (2, 22, 16, 'oct')
    e.g. 'This is the mail at 2: 22' -> (2, 22, None, None)
    """
    clean = text.strip()

    # Time match: 2:22, 02:22, 2: 22, 14:22, 2.22
    time_match = re.search(r'\b(\d{1,2})\s*[:.]\s*(\d{2})\s*(am|pm)?\b', clean, re.I)
    target_h, target_m = None, None
    if time_match:
        target_h = int(time_match.group(1))
        target_m = int(time_match.group(2))
        ampm = (time_match.group(3) or '').lower()
        if ampm == 'pm' and target_h < 12:
            target_h += 12
        elif ampm == 'am' and target_h == 12:
            target_h = 0

    # Date match: 16 oct, 16th october, oct 16
    date_match = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(oct|nov|dec|jan|feb|mar|apr|may|jun|jul|aug|sep)[a-z]*\b', clean, re.I)
    target_day, target_month = None, None
    if date_match:
        target_day = int(date_match.group(1))
        target_month = date_match.group(2).lower()[:3]
    else:
        date_rev = re.search(r'\b(oct|nov|dec|jan|feb|mar|apr|may|jun|jul|aug|sep)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\b', clean, re.I)
        if date_rev:
            target_month = date_rev.group(1).lower()[:3]
            target_day = int(date_rev.group(2))

    return target_h, target_m, target_day, target_month


def extract_gmail_query_and_count(text: str) -> tuple[str, int, bool]:
    """
    Intelligently parses user query for Gmail:
    Returns (search_query, count, is_singular_latest).
    - If user asks for their last/latest email (e.g. 'tell about the last mail', 'What is in my last email'),
      search_query is "" so Gmail returns the true latest message chronologically.
    - If user specifies a specific date/time (e.g. 'onn date 16 oct 2:22' or 'at 2:22'),
      search_query is "" so messages can be accurately matched by timestamp in Python.
    - If user specifies a sender (e.g. 'from HR'), search_query is 'from:HR'.
    - If user specifies a specific topic, extracts that topic.
    """
    clean = normalize_text_for_email_search(text.strip())

    # 0. Check for specific date or time targets (e.g. 'onn date 16 oct 2:22', 'mail at 2:22')
    target_h, target_m, target_day, target_month = extract_gmail_date_time_target(clean)
    if target_h is not None or target_day is not None:
        # Return empty query to fetch recent batch and filter in Python
        return "", 20, bool(target_h is not None)

    # 1. Check if asking for a singular latest email
    is_singular_latest = bool(
        re.search(
            r"\b(last\s+email|latest\s+email|most\s+recent\s+email|previous\s+email|last\s+one|latest\s+one)\b",
            clean,
            re.I,
        )
        or re.search(
            r"^(what(\x27s|\s+is)?\s+(in\s+)?(my\s+)?(last|latest|recent)|whats\s+(in\s+)?(my\s+)?(last|latest|recent))[!.,?\s]*$",
            clean,
            re.I,
        )
    )

    # Check for general latest queries
    is_general_latest = bool(re.search(
        r"^(what(\x27s|\s+is)?\s+(in\s+)?(my\s+)?(last|latest|recent|new)(\s+email)?|tell(\s+me)?\s+about\s+(the\s+|my\s+)?(last|latest|recent)\s+email|find\s+(my\s+)?(last|latest|recent)\s+email|show\s+(my\s+)?(last|latest|recent)\s+email|check\s+(my\s+)?(last|latest|recent|inbox|email)|(any\s+)?new\s+email|my\s+(last|latest|recent)\s+email|get\s+(my\s+)?(last|latest|recent)\s+email)[!.,?\s]*$",
        clean,
        re.I,
    ))

    # If it is a latest/last query, ALWAYS return empty query for true chronological inbox order!
    if is_singular_latest or is_general_latest:
        count = 1 if is_singular_latest else 3
        return "", count, is_singular_latest

    # 2. Check for "from: <sender>"
    from_match = re.search(r"\bfrom:?\s+([A-Za-z0-9_.@-]+)", clean, re.I)
    if from_match:
        return f"from:{from_match.group(1).strip()}", 3, False

    # 3. Check for "about: <topic>"
    about_match = re.search(r"\b(about|regarding|subject|titled)\s+([^?.!]+)", clean, re.I)
    if about_match:
        topic = re.sub(r"\b(my|the|an?|emails?|please|find|show|tell|me)\b", "", about_match.group(2).strip(), flags=re.I).strip()
        if topic and topic.lower() not in ["last", "latest", "recent"]:
            return topic, 3, False

    # 4. Strip filler/conversational words
    stopwords = r"\b(hi+|hello+|hey+|what(\x27s|\s+is)?|in|my|the|find|search|get|show|check|tell|me|about|latest|recent|last|new|emails?|gmail|inbox|please|can|you|whats|onn?|date|at|this|is)\b"
    extracted = re.sub(stopwords, "", clean, flags=re.I)
    extracted = re.sub(r"[^a-zA-Z0-9\s]", " ", extracted).strip()

    if len(extracted) < 3 or extracted.lower() in ["last", "latest", "recent"]:
        return "", 1, True

    return extracted, 3, False


def call_groq_llm(messages: list[dict[str, str]]) -> str:
    """Invoke Groq LLM API with fallback handling."""
    if not GROQ_API_KEY:
        return "GROQ_API_KEY is not configured in .env. Please configure it to enable AI responses."

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    # Try Primary Model
    for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        try:
            resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            logger.warning("Groq model %s returned status %d: %s", model_name, resp.status_code, resp.text)
        except Exception as e:
            logger.warning("Error invoking Groq model %s: %s", model_name, str(e))

    return "I'm having trouble connecting to the AI language model at the moment. Please try again shortly."


def process_chat_turn(session_id: str, user_text: str) -> dict[str, Any]:
    """
    Process a chat turn:
    1. Save user message.
    2. Retrieve conversation history.
    3. Detect intent (Greeting, Gmail, GitHub, Follow-up, etc.).
    4. Fetch real source evidence if applicable.
    5. Invoke Groq AI with multi-turn context and evidence.
    6. Construct rich_cards and sources_accessed.
    7. Persist assistant message in SQLite and update session title if needed.
    """
    clean_text = user_text.strip()
    clean_normalized = normalize_text_for_email_search(clean_text)

    # 1. Save user message
    user_msg = db.add_message(session_id=session_id, role="user", content=clean_text)

    # 2. Get session details and recent history
    session = db.get_session(session_id)
    history_messages = session.get("messages", []) if session else []
    # Take prior messages (excluding the message just inserted)
    prior_messages = [m for m in history_messages if m["id"] != user_msg["id"]][-6:]

    # 3. Detect Intent
    is_pure_greeting = bool(GREETING_REGEX.match(clean_text))
    has_github_intent = bool(re.search(r"\b(github|repo|repos|repository|repositories|commit|code|branch|pr)\b", clean_text, re.I))
    has_sharepoint_intent = bool(re.search(r"\b(sharepoint|teams|microsoft)\b", clean_text, re.I))
    has_fileshare_intent = bool(re.search(r"\b(file\s*share|shared\s*folder|test-share)\b", clean_text, re.I))
    has_lms_intent = bool(re.search(r"\b(lms|course|courses|learning)\b", clean_text, re.I))
    has_slack_intent = bool(re.search(r"\b(slack|channel|channels|dm|direct\s*message|workspace\s*chat)\b", clean_text, re.I))
    has_database_intent = bool(re.search(r"\b(postgres|postgresql|database|sql|tables?|schema|query|sqlite)\b", clean_text, re.I))
    has_notion_intent = bool(re.search(r"\b(notion|wiki|workspace\s*page|notion\s*page|notion\s*doc)\b", clean_text, re.I))
    has_servicenow_intent = bool(re.search(r"\b(servicenow|incident|incidents|ticket|tickets|service\s*request|service\s*requests|sc_request|knowledge\s*base)\b", clean_text, re.I))
    has_salesforce_intent = bool(re.search(r"\b(salesforce|crm|lead|leads|opportunity|opportunities|deal|deals|account|accounts)\b", clean_text, re.I))
    has_drive_intent = bool(re.search(r"\b(google\s*drive|gdrive|drive\s*file|drive\s*files|google\s*doc|google\s*docs|google\s*sheet|google\s*sheets|drive)\b", clean_text, re.I))
    has_jira_intent = bool(re.search(r"\b(jira|issue|issues|sprint|backlog|epic|story|bug|bugs|kanban|board|atlassian)\b", clean_text, re.I))
    is_followup = bool(FOLLOWUP_REGEX.search(clean_text))

    target_h, target_m, target_day, target_month = extract_gmail_date_time_target(clean_normalized)
    has_email_intent = bool(
        re.search(r"\b(email|emails|mail|mails|gmail|inbox|sent|message|messages)\b", clean_normalized, re.I)
        or re.search(
            r"^(what(\x27s|\s+is)?\s+(in\s+)?(my\s+)?(last|latest|recent)|whats\s+(in\s+)?(my\s+)?(last|latest|recent))[!.,?\s]*$",
            clean_normalized,
            re.I,
        )
        or ((target_h is not None or target_day is not None) and not (has_github_intent or has_jira_intent or has_drive_intent or has_servicenow_intent or has_salesforce_intent or has_slack_intent or has_database_intent or has_notion_intent))
    )

    rich_cards: list[dict[str, Any]] = []
    sources_accessed: list[dict[str, Any]] = []
    retrieved_evidence: list[str] = []
    search_q = ""
    is_singular_latest = False

    # Check previous conversation context for follow-ups
    prev_cards = []
    for m in reversed(prior_messages):
        if m.get("role") == "assistant" and m.get("rich_cards"):
            prev_cards = m["rich_cards"]
            break

    if is_followup and not (has_email_intent or has_github_intent or has_sharepoint_intent or has_drive_intent or has_jira_intent or has_servicenow_intent or has_salesforce_intent or has_slack_intent or has_database_intent or has_notion_intent):
        # Determine if previous context was email, github, slack, database, or notion
        if any(c.get("type") == "email" for c in prev_cards):
            has_email_intent = True
        elif any(c.get("type") == "repo" for c in prev_cards):
            has_github_intent = True
        elif any(c.get("type") == "slack" for c in prev_cards):
            has_slack_intent = True
        elif any(c.get("type") == "database" for c in prev_cards):
            has_database_intent = True
        elif any(c.get("type") == "notion" for c in prev_cards):
            has_notion_intent = True

    # 4. Handle Pure Greeting (no sources queried)
    if is_pure_greeting:
        ai_messages = [
            {
                "role": "system",
                "content": (
                    "You are a friendly, professional workplace AI assistant for Shashvat at Appinventiv. "
                    "Respond cordially and naturally to the user's greeting. "
                    "Offer assistance with searching connected workplace sources (Gmail, GitHub, SharePoint, Teams, LMS, etc.). "
                    "Keep it concise (1-2 sentences)."
                ),
            }
        ]
        # Include brief history
        for m in prior_messages[-3:]:
            ai_messages.append({"role": m["role"], "content": m["content"]})
        ai_messages.append({"role": "user", "content": clean_text})

        assistant_reply = call_groq_llm(ai_messages)

    # 5. Handle Source Inquiries
    else:
        # A. Gmail Retrieval
        if has_email_intent:
            try:
                gmail = get_gmail_connector()
                search_q, fetch_count, is_singular_latest = extract_gmail_query_and_count(clean_text)
                target_h, target_m, target_day, target_month = extract_gmail_date_time_target(clean_normalized)
                if is_followup:
                    search_q = ""
                    fetch_count = 1

                ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

                # If user asked for specific date or time, fetch recent inbox batch and filter in Python
                if target_h is not None or target_day is not None:
                    msgs_res = gmail.list_messages(max_results=30, q="")
                    raw_messages = msgs_res.get("messages", [])
                    matched_messages = []

                    for m in raw_messages:
                        raw_date = m.get("date", "")
                        if not raw_date:
                            continue
                        try:
                            dt = email.utils.parsedate_to_datetime(raw_date).astimezone(ist)
                        except Exception:
                            continue

                        # Check hour and minute
                        time_matches = True
                        if target_h is not None and target_m is not None:
                            h_match = (dt.hour == target_h) or (dt.hour % 12 == target_h % 12)
                            m_diff = abs(dt.minute - target_m)
                            time_matches = h_match and (m_diff <= 1)
                        elif target_h is not None:
                            h_match = (dt.hour == target_h) or (dt.hour % 12 == target_h % 12)
                            time_matches = h_match

                        # Check day and month
                        date_matches = True
                        if target_day is not None:
                            date_matches = date_matches and (dt.day == target_day)
                        if target_month is not None:
                            date_matches = date_matches and (dt.strftime("%b").lower() == target_month.lower())

                        if time_matches and date_matches:
                            matched_messages.append(m)

                    if matched_messages:
                        messages_list = matched_messages
                        fetch_count = len(matched_messages)
                    else:
                        messages_list = []
                else:
                    msgs_res = gmail.list_messages(max_results=max(fetch_count, 1), q=search_q)
                    messages_list = msgs_res.get("messages", [])

                if messages_list:
                    sources_accessed.append({
                        "name": "Gmail",
                        "status_text": "Live inbox accessed",
                        "icon": "gmail",
                        "verified": True,
                    })

                    # Fetch full details of target messages
                    for idx, m_meta in enumerate(messages_list[:fetch_count]):
                        m_id = m_meta["id"]
                        full_msg = gmail.get_message(m_id)
                        subject = html.unescape(full_msg.get("subject", "(No Subject)"))
                        sender = html.unescape(full_msg.get("from", "Unknown"))
                        raw_date = full_msg.get("date", "")
                        try:
                            dt = email.utils.parsedate_to_datetime(raw_date).astimezone(ist)
                            date = dt.strftime("%d %b %Y, %I:%M %p IST")
                        except Exception:
                            date = raw_date
                        raw_snippet = full_msg.get("snippet", "")
                        clean_snippet = html.unescape(re.sub(r"^-+\s*Forwarded message\s*-+\s*", "", raw_snippet, flags=re.I)).strip()
                        body = full_msg.get("body_text", clean_snippet)[:1500]
                        attachments = full_msg.get("attachments", [])

                        evidence_text = (
                            f"Email {idx+1} (ID: {m_id}):\n"
                            f"- Subject: {subject}\n"
                            f"- From: {sender}\n"
                            f"- Date: {date}\n"
                            f"- Snippet: {clean_snippet}\n"
                            f"- Full Body Excerpt:\n{body}"
                        )
                        if attachments:
                            att_names = ", ".join([a["filename"] for a in attachments])
                            evidence_text += f"\n- Attachments: {att_names}"
                        retrieved_evidence.append(evidence_text)

                        # Create email rich card
                        card_attachments = []
                        for a in attachments:
                            att_url = f"http://localhost:8000/gmail/messages/{m_id}/attachments/{a['attachment_id']}?filename={quote(a['filename'])}"
                            card_attachments.append({
                                "filename": a["filename"],
                                "size": f"{round(a.get('size', 0)/1024, 1)} KB" if a.get("size") else "Download",
                                "download_url": att_url,
                            })

                        rich_cards.append({
                            "type": "email",
                            "title": subject,
                            "metadata": f"Gmail • From: {sender} • {date}",
                            "snippet": clean_snippet or (body[:150] + "..."),
                            "link": f"http://localhost:8000/gmail/messages/{m_id}",
                            "action_label": "View Email",
                            "attachments": card_attachments,
                        })
                else:
                    retrieved_evidence.append(f"Gmail was searched with query '{search_q}' but no matching emails were found.")
                    sources_accessed.append({
                        "name": "Gmail",
                        "status_text": "No matching emails",
                        "icon": "gmail",
                        "verified": True,
                    })
            except Exception as e:
                logger.error("Error retrieving Gmail data: %s", str(e))
                retrieved_evidence.append(f"Gmail search error: {str(e)}")

        # B. GitHub Retrieval
        if has_github_intent:
            try:
                gh = get_github_connector()
                repos_res = gh.list_repositories(per_page=30)
                items = repos_res.get("items", [])

                if items:
                    # Sort items so Shashvat's own repos (ShashvatSharma18 / SookieAI) come first
                    sorted_items = sorted(
                        items,
                        key=lambda x: (
                            0 if "shashvat" in x["full_name"].lower()
                            else (1 if "sookie" in x["full_name"].lower() else 2)
                        )
                    )

                    sources_accessed.append({
                        "name": "GitHub",
                        "status_text": f"Live repositories indexed ({len(items)})",
                        "icon": "github",
                        "verified": True,
                    })

                    # Check if asking for all repos or general list
                    is_all_repos = bool(
                        re.search(
                            r"\b(all\s+repos?|all\s+repositories|list\s+repos?|list\s+repositories|show\s+all|available|my\s+repos?|what\s+repos?)\b",
                            clean_text,
                            re.I,
                        )
                    )

                    # Check if user mentioned a specific repo name or keyword
                    matched_repo = None
                    clean_no_punct = re.sub(r"[^a-zA-Z0-9\s-]", " ", clean_text).lower()
                    query_words = [
                        w for w in clean_no_punct.split()
                        if len(w) > 3 and w not in ["github", "repo", "repos", "repository", "repositories", "about", "details", "give", "tell", "show", "find", "what"]
                    ]

                    for r in items:
                        r_name = r["name"].lower()
                        if r_name in clean_text.lower():
                            matched_repo = r
                            break
                        for qw in query_words:
                            if qw in r_name:
                                matched_repo = r
                                break
                        if matched_repo:
                            break

                    # If asking for all repos or asking generally without a specific repo:
                    if is_all_repos or not matched_repo:
                        repo_summary_lines = [f"Available GitHub Repositories for Shashvat Sharma (Total: {len(items)}):"]
                        for r in sorted_items:
                            desc = r.get("description") or "No description provided"
                            vis = r.get("visibility", "public")
                            branch = r.get("default_branch", "main")
                            repo_summary_lines.append(f"- **{r['full_name']}** ({vis}, branch: {branch}): {desc}\n  URL: {r.get('html_url')}")
                        retrieved_evidence.append("\n".join(repo_summary_lines))

                        # If user asked generally, also spotlight the primary repository
                        primary_repo = sorted_items[0]
                        p_owner = primary_repo.get("owner", "ShashvatSharma18")
                        p_name = primary_repo["name"]
                        try:
                            p_contents = gh.list_contents(p_owner, p_name)
                            p_files = [f["name"] for f in p_contents.get("items", [])]
                            p_detail = f"Detailed Spotlight on Primary Project '{primary_repo['full_name']}':\n- Files: {', '.join(p_files[:15])}"
                            if "README.md" in p_files:
                                readme_b, _ = gh.download_file(p_owner, p_name, "README.md")
                                p_detail += "\n- README.md highlights:\n" + readme_b.decode("utf-8", errors="replace")[:1000]
                            retrieved_evidence.append(p_detail)
                        except Exception:
                            pass

                        # Add rich cards for the top repositories
                        for r in sorted_items[:4]:
                            rich_cards.append({
                                "type": "repo",
                                "title": r["full_name"],
                                "metadata": f"GitHub • Branch: {r.get('default_branch', 'main')} • {r.get('visibility', 'public')}",
                                "snippet": r.get("description") or "GitHub repository with source code and documentation.",
                                "link": r.get("html_url") or f"https://github.com/{r['full_name']}",
                                "action_label": "View on GitHub",
                            })

                    else:
                        # Specific matched repository
                        target_repo = matched_repo
                        repo_owner = target_repo.get("owner", "ShashvatSharma18")
                        repo_name = target_repo["name"]

                        evidence_text = (
                            f"GitHub Repository: {target_repo['full_name']}\n"
                            f"- Description: {target_repo.get('description') or 'No description provided'}\n"
                            f"- Branch: {target_repo.get('default_branch', 'main')}\n"
                            f"- Visibility: {target_repo.get('visibility', 'public')}\n"
                            f"- URL: {target_repo.get('html_url')}"
                        )

                        files = []
                        try:
                            contents = gh.list_contents(repo_owner, repo_name)
                            files = [f["name"] for f in contents.get("items", [])]
                            evidence_text += f"\n- Files in repository: {', '.join(files[:15])}"

                            if "README.md" in files:
                                readme_bytes, _ = gh.download_file(repo_owner, repo_name, "README.md")
                                readme_content = readme_bytes.decode("utf-8", errors="replace")[:1200]
                                evidence_text += f"\n- README.md content excerpt:\n{readme_content}"
                        except Exception as ce:
                            evidence_text += f"\n- (Could not load file tree: {str(ce)})"

                        retrieved_evidence.append(evidence_text)

                        rich_cards.append({
                            "type": "repo",
                            "title": target_repo["full_name"],
                            "metadata": f"GitHub • Branch: {target_repo.get('default_branch', 'main')} • {target_repo.get('visibility', 'public')}",
                            "snippet": target_repo.get("description") or f"Repository with {len(files)} files.",
                            "link": target_repo.get("html_url") or f"https://github.com/{target_repo['full_name']}",
                            "action_label": "View on GitHub",
                        })
                else:
                    retrieved_evidence.append("GitHub was checked, but no repositories were found.")
            except Exception as e:
                logger.error("Error retrieving GitHub data: %s", str(e))
                retrieved_evidence.append(f"GitHub retrieval error: {str(e)}")

        # C. SharePoint / Teams Check
        if has_sharepoint_intent:
            ms_configured = bool(
                os.getenv("MICROSOFT_TENANT_ID")
                and os.getenv("MICROSOFT_CLIENT_ID")
                and os.getenv("MICROSOFT_CLIENT_SECRET")
            )
            if not ms_configured:
                retrieved_evidence.append(
                    "SharePoint and Microsoft Teams connectors are code-ready and integrated, "
                    "but Microsoft 365 tenant credentials (MICROSOFT_TENANT_ID, CLIENT_ID, CLIENT_SECRET) "
                    "are currently pending configuration from your administrator. No live search could be performed."
                )
                sources_accessed.append({
                    "name": "SharePoint",
                    "status_text": "Code Ready (Awaiting Tenant Credentials)",
                    "icon": "sharepoint",
                    "verified": False,
                })
                sources_accessed.append({
                    "name": "Microsoft Teams",
                    "status_text": "Code Ready (Awaiting Tenant Credentials)",
                    "icon": "teams",
                    "verified": False,
                })

        # D. File Share Retrieval
        if has_fileshare_intent:
            try:
                fs = get_fileshare_connector()
                files_res = fs.list_directory("")
                items = files_res.get("items", [])
                file_names = [i["name"] for i in items]
                retrieved_evidence.append(f"Local File Share contents: {', '.join(file_names)}")
                sources_accessed.append({
                    "name": "File Share",
                    "status_text": "Local test share indexed",
                    "icon": "file_share",
                    "verified": True,
                })
            except Exception as e:
                retrieved_evidence.append(f"File share error: {str(e)}")

        # E. LMS Retrieval
        if has_lms_intent:
            try:
                lms = get_lms_connector()
                courses_res = lms.list_courses()
                c_titles = [c["title"] for c in courses_res.get("courses", [])]
                retrieved_evidence.append(f"LMS Courses: {', '.join(c_titles)}")
                sources_accessed.append({
                    "name": "LMS",
                    "status_text": "Mock course catalog accessed",
                    "icon": "lms",
                    "verified": True,
                })
            except Exception as e:
                retrieved_evidence.append(f"LMS error: {str(e)}")

        # F. ServiceNow Retrieval
        if has_servicenow_intent:
            sn_configured = bool(
                os.getenv("SERVICENOW_INSTANCE_URL")
                and os.getenv("SERVICENOW_USERNAME")
                and os.getenv("SERVICENOW_PASSWORD")
            )
            if not sn_configured:
                retrieved_evidence.append(
                    "ServiceNow connector is code-ready and integrated, but credentials "
                    "(SERVICENOW_INSTANCE_URL, SERVICENOW_USERNAME, SERVICENOW_PASSWORD) "
                    "are currently pending configuration from your administrator. No live search could be performed."
                )
                sources_accessed.append({
                    "name": "ServiceNow",
                    "status_text": "Code Ready (Awaiting Credentials)",
                    "icon": "servicenow",
                    "verified": False,
                })
            else:
                try:
                    sn = get_servicenow_connector()
                    is_kb = bool(re.search(r"\b(knowledge|kb|article|solution)\b", clean_text, re.I))
                    if is_kb:
                        kb_res = sn.search_knowledge(query=clean_text, max_results=5)
                        articles = kb_res.get("articles", [])
                        if articles:
                            sources_accessed.append({
                                "name": "ServiceNow",
                                "status_text": f"Knowledge base searched ({len(articles)})",
                                "icon": "servicenow",
                                "verified": True,
                            })
                            evidence_lines = ["ServiceNow Knowledge Base Articles:"]
                            for art in articles:
                                evidence_lines.append(
                                    f"- **{art.get('number')}**: {art.get('short_description')} (Topic: {art.get('topic')})\n"
                                    f"  {art.get('snippet')}"
                                )
                                rich_cards.append({
                                    "type": "document",
                                    "title": f"{art.get('number')} - {art.get('short_description')}",
                                    "metadata": f"ServiceNow KB • Topic: {art.get('topic')} • State: {art.get('workflow_state')}",
                                    "snippet": art.get("snippet"),
                                    "action_label": "View Article",
                                })
                            retrieved_evidence.append("\n".join(evidence_lines))
                        else:
                            retrieved_evidence.append("ServiceNow knowledge base was searched, but no matching articles were found.")
                    else:
                        inc_res = sn.list_incidents(max_results=5)
                        incidents = inc_res.get("incidents", [])
                        if incidents:
                            sources_accessed.append({
                                "name": "ServiceNow",
                                "status_text": f"Incidents retrieved ({len(incidents)})",
                                "icon": "servicenow",
                                "verified": True,
                            })
                            evidence_lines = ["ServiceNow Incidents:"]
                            for inc in incidents:
                                evidence_lines.append(
                                    f"- **{inc.get('number')}**: {inc.get('short_description')}\n"
                                    f"  Priority: {inc.get('priority')} | State: {inc.get('state')} | Assigned To: {inc.get('assigned_to')} | Opened: {inc.get('opened_at')}"
                                )
                                rich_cards.append({
                                    "type": "document",
                                    "title": f"{inc.get('number')} - {inc.get('short_description')}",
                                    "metadata": f"ServiceNow • Priority: {inc.get('priority')} • State: {inc.get('state')} • Assigned: {inc.get('assigned_to')}",
                                    "snippet": inc.get("description") or inc.get("short_description"),
                                    "action_label": "View Incident",
                                })
                            retrieved_evidence.append("\n".join(evidence_lines))
                        else:
                            retrieved_evidence.append("ServiceNow was checked, but no incidents were found.")
                except Exception as e:
                    logger.error("Error retrieving ServiceNow data: %s", str(e))
                    retrieved_evidence.append(f"ServiceNow retrieval error: {str(e)}")

        # G. Salesforce Retrieval
        if has_salesforce_intent:
            sf_token_file = os.path.exists(".salesforce_token.json")
            sf_configured = bool(
                sf_token_file
                or (os.getenv("SALESFORCE_CLIENT_ID") and os.getenv("SALESFORCE_CLIENT_SECRET"))
            )
            if not sf_configured:
                retrieved_evidence.append(
                    "Salesforce connector is code-ready and integrated, but credentials "
                    "(SALESFORCE_CLIENT_ID, SALESFORCE_CLIENT_SECRET) or OAuth token "
                    "are currently pending configuration from your administrator. No live search could be performed."
                )
                sources_accessed.append({
                    "name": "Salesforce",
                    "status_text": "Code Ready (Awaiting Credentials / OAuth)",
                    "icon": "salesforce",
                    "verified": False,
                })
            else:
                try:
                    sf = get_salesforce_connector()
                    if re.search(r"\b(lead|leads)\b", clean_text, re.I):
                        res = sf.list_leads(max_results=5)
                        leads = res.get("leads", [])
                        if leads:
                            sources_accessed.append({
                                "name": "Salesforce",
                                "status_text": f"Leads retrieved ({len(leads)})",
                                "icon": "salesforce",
                                "verified": True,
                            })
                            evidence_lines = ["Salesforce Leads:"]
                            for lead in leads:
                                evidence_lines.append(
                                    f"- **{lead.get('Name')}** (Company: {lead.get('Company')}, Status: {lead.get('Status')}, Email: {lead.get('Email')})"
                                )
                                rich_cards.append({
                                    "type": "document",
                                    "title": f"Lead: {lead.get('Name')}",
                                    "metadata": f"Salesforce • Company: {lead.get('Company')} • Status: {lead.get('Status')}",
                                    "snippet": f"Email: {lead.get('Email')} | Title: {lead.get('Title')} | Phone: {lead.get('Phone')}",
                                    "action_label": "View Lead",
                                })
                            retrieved_evidence.append("\n".join(evidence_lines))
                        else:
                            retrieved_evidence.append("Salesforce was checked, but no leads were found.")
                    elif re.search(r"\b(opportunity|opportunities|deal|deals)\b", clean_text, re.I):
                        res = sf.list_opportunities(max_results=5)
                        opps = res.get("opportunities", [])
                        if opps:
                            sources_accessed.append({
                                "name": "Salesforce",
                                "status_text": f"Opportunities retrieved ({len(opps)})",
                                "icon": "salesforce",
                                "verified": True,
                            })
                            evidence_lines = ["Salesforce Opportunities:"]
                            for opp in opps:
                                evidence_lines.append(
                                    f"- **{opp.get('Name')}** (Stage: {opp.get('StageName')}, Amount: {opp.get('Amount')}, Close Date: {opp.get('CloseDate')})"
                                )
                                rich_cards.append({
                                    "type": "document",
                                    "title": f"Opportunity: {opp.get('Name')}",
                                    "metadata": f"Salesforce • Stage: {opp.get('StageName')} • Amount: {opp.get('Amount')}",
                                    "snippet": f"Stage: {opp.get('StageName')} | Close Date: {opp.get('CloseDate')} | Probability: {opp.get('Probability')}%",
                                    "action_label": "View Opportunity",
                                })
                            retrieved_evidence.append("\n".join(evidence_lines))
                        else:
                            retrieved_evidence.append("Salesforce was checked, but no opportunities were found.")
                    else:
                        res = sf.list_accounts(max_results=5)
                        accounts = res.get("accounts", [])
                        if accounts:
                            sources_accessed.append({
                                "name": "Salesforce",
                                "status_text": f"Accounts retrieved ({len(accounts)})",
                                "icon": "salesforce",
                                "verified": True,
                            })
                            evidence_lines = ["Salesforce Accounts:"]
                            for acc in accounts:
                                evidence_lines.append(
                                    f"- **{acc.get('Name')}** (Type: {acc.get('Type')}, Industry: {acc.get('Industry')}, Phone: {acc.get('Phone')})"
                                )
                                rich_cards.append({
                                    "type": "document",
                                    "title": f"Account: {acc.get('Name')}",
                                    "metadata": f"Salesforce • Industry: {acc.get('Industry')} • Type: {acc.get('Type')}",
                                    "snippet": f"Industry: {acc.get('Industry')} | Phone: {acc.get('Phone')} | Website: {acc.get('Website')}",
                                    "action_label": "View Account",
                                })
                            retrieved_evidence.append("\n".join(evidence_lines))
                        else:
                            retrieved_evidence.append("Salesforce was checked, but no accounts were found.")
                except Exception as e:
                    logger.error("Error retrieving Salesforce data: %s", str(e))
                    retrieved_evidence.append(f"Salesforce retrieval error: {str(e)}")

        # H. Google Drive Retrieval
        if has_drive_intent:
            gdrive_token_file = os.path.exists(".google_drive_token.json")
            gdrive_configured = bool(
                gdrive_token_file
                or (os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))
            )
            if not gdrive_token_file:
                retrieved_evidence.append(
                    "Google Drive connector is code-ready and integrated, but Google Drive OAuth authorization "
                    "has not been completed yet. Please visit /google-drive/auth/login to authenticate and grant drive.readonly access."
                )
                sources_accessed.append({
                    "name": "Google Drive",
                    "status_text": "Code Ready (Needs OAuth Login)",
                    "icon": "google_drive",
                    "verified": False,
                })
            else:
                try:
                    drive = get_google_drive_connector()
                    # Check if asking for latest file(s)
                    is_drive_latest = bool(
                        re.search(
                            r"\b(last\s+file|latest\s+file|recent\s+file|newest\s+file|last\s+doc|latest\s+doc|recent\s+doc|last\s+document|latest\s+document|recent\s+document|last\s+sheet|latest\s+sheet|latest|last|recent|newest)\b",
                            clean_text,
                            re.I,
                        )
                    )

                    # Extract topic/query if user searched for something specific
                    stopwords = r"\b(what(\x27s|\s+is)?|whats|in|the|my|of|a|an|search|find|show|get|tell|check|about|google|drive|gdrive|files?|docs?|sheets?|documents?|latest|recent|last|newest|please|can|you)\b"
                    cleaned_search = re.sub(stopwords, " ", clean_text, flags=re.I)
                    cleaned_search = re.sub(r"[^a-zA-Z0-9\s-]", " ", cleaned_search).strip()
                    cleaned_search = " ".join(cleaned_search.split())

                    # If it's a latest file request or cleaned search is empty/short, fetch chronologically
                    if is_drive_latest or len(cleaned_search) < 2:
                        search_drive_q = ""
                    else:
                        search_drive_q = cleaned_search

                    res = drive.list_files(max_results=5, q=search_drive_q, order_by="modifiedTime desc")
                    files = res.get("files", [])
                    if files:
                        sources_accessed.append({
                            "name": "Google Drive",
                            "status_text": f"Live drive files indexed ({len(files)})",
                            "icon": "google_drive",
                            "verified": True,
                        })

                        # Extract readable text content from top file(s) for deep inspection
                        top_file = files[0]
                        top_text = drive.get_file_text_content(top_file.get("id"), top_file.get("mimeType"))

                        evidence_lines = [f"Google Drive Files (Retrieved in true chronological order - Latest First, Total {len(files)}):"]
                        for idx, f in enumerate(files):
                            f_name = f.get("name", "Untitled")
                            f_mime = f.get("mimeType", "")
                            f_mod = f.get("modifiedTime", "")
                            f_link = f.get("webViewLink", "")
                            evidence_lines.append(
                                f"- File {idx+1}: **{f_name}** | Type: {f_mime} | Last Modified: {f_mod} | Link: {f_link}"
                            )

                        if top_text and not top_text.startswith("(Could not"):
                            evidence_lines.append(
                                f"\n### Content Excerpt of Most Recent File '{top_file.get('name')}':\n{top_text[:2500]}\n### End Content Excerpt"
                            )

                        for f in files:
                            f_size_kb = f"{round(f['size']/1024, 1)} KB" if f.get("size") else "Google Doc"
                            rich_cards.append({
                                "type": "document",
                                "title": f.get("name", "Drive File"),
                                "metadata": f"Google Drive • {f_size_kb} • {str(f.get('modifiedTime', ''))[:10]}",
                                "snippet": f"File type: {f.get('mimeType')}",
                                "link": f.get("webViewLink") or f"http://localhost:8000/google-drive/files/{f.get('id')}/download",
                                "action_label": "Open in Drive",
                            })
                        retrieved_evidence.append("\n".join(evidence_lines))
                    else:
                        retrieved_evidence.append("Google Drive was searched, but no matching files were found.")
                        sources_accessed.append({
                            "name": "Google Drive",
                            "status_text": "No matching files",
                            "icon": "google_drive",
                            "verified": True,
                        })
                except Exception as e:
                    logger.error("Error retrieving Google Drive data: %s", str(e))
                    retrieved_evidence.append(f"Google Drive retrieval error: {str(e)}")

        # I. Jira Retrieval
        if has_jira_intent:
            jira_configured = bool(
                os.getenv("JIRA_BASE_URL")
                and os.getenv("JIRA_EMAIL")
                and os.getenv("JIRA_API_TOKEN")
            )
            if not jira_configured:
                retrieved_evidence.append(
                    "Jira connector is code-ready and integrated, but Jira credentials "
                    "(JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN) are currently pending configuration from your administrator. "
                    "No live issue search could be performed."
                )
                sources_accessed.append({
                    "name": "Jira",
                    "status_text": "Code Ready (Awaiting API Token)",
                    "icon": "jira",
                    "verified": False,
                })
            else:
                try:
                    jira = get_jira_connector()
                    key_match = re.search(r"\b([A-Z][A-Z0-9]+-\d+)\b", clean_text)
                    if key_match:
                        issue_key = key_match.group(1)
                        try:
                            issue = jira.get_issue(issue_key)
                            sources_accessed.append({
                                "name": "Jira",
                                "status_text": f"Issue {issue_key} retrieved",
                                "icon": "jira",
                                "verified": True,
                            })
                            evidence_lines = [
                                f"Jira Issue {issue.get('key')}:",
                                f"- Summary: {issue.get('summary')}",
                                f"- Status: {issue.get('status')}",
                                f"- Priority: {issue.get('priority')}",
                                f"- Assignee: {issue.get('assignee')}",
                                f"- Type: {issue.get('type')}",
                                f"- Description: {issue.get('description', '')[:500]}",
                            ]
                            retrieved_evidence.append("\n".join(evidence_lines))
                            rich_cards.append({
                                "type": "document",
                                "title": f"[{issue.get('key')}] {issue.get('summary')}",
                                "metadata": f"Jira • Status: {issue.get('status')} • Priority: {issue.get('priority')} • Assignee: {issue.get('assignee')}",
                                "snippet": issue.get("description", "")[:200] or issue.get("summary"),
                                "link": issue.get("url"),
                                "action_label": "View in Jira",
                            })
                        except Exception as e:
                            retrieved_evidence.append(f"Jira issue {issue_key} lookup error: {str(e)}")
                    else:
                        res = jira.search_issues(max_results=5)
                        issues = res.get("issues", [])
                        if issues:
                            sources_accessed.append({
                                "name": "Jira",
                                "status_text": f"Issues retrieved ({len(issues)})",
                                "icon": "jira",
                                "verified": True,
                            })
                            evidence_lines = ["Jira Issues:"]
                            for iss in issues:
                                evidence_lines.append(
                                    f"- **{iss.get('key')}**: {iss.get('summary')} (Status: {iss.get('status')}, Priority: {iss.get('priority')}, Assignee: {iss.get('assignee')})"
                                )
                                rich_cards.append({
                                    "type": "document",
                                    "title": f"[{iss.get('key')}] {iss.get('summary')}",
                                    "metadata": f"Jira • Status: {iss.get('status')} • Priority: {iss.get('priority')} • Assignee: {iss.get('assignee')}",
                                    "snippet": iss.get("description", "")[:200] or iss.get("summary"),
                                    "link": iss.get("url"),
                                    "action_label": "View in Jira",
                                })
                            retrieved_evidence.append("\n".join(evidence_lines))
                        else:
                            retrieved_evidence.append("Jira was checked, but no issues were found.")
                except Exception as e:
                    logger.error("Error retrieving Jira data: %s", str(e))
                    retrieved_evidence.append(f"Jira retrieval error: {str(e)}")

        # J. Slack Retrieval
        if has_slack_intent:
            slack_token = os.getenv("SLACK_BOT_TOKEN")
            if not slack_token:
                retrieved_evidence.append(
                    "Slack connector is ready and integrated, but SLACK_BOT_TOKEN is not configured yet. "
                    "Please configure your Slack Bot User OAuth Token in the Connected Sources panel."
                )
                sources_accessed.append({
                    "name": "Slack",
                    "status_text": "Code Ready (Awaiting Bot Token)",
                    "icon": "slack",
                    "verified": False,
                })
            else:
                try:
                    slack = get_slack_connector()
                    stopwords = r"\b(slack|channels?|dms?|messages?|chat|show|list|get|find|search|about|what|is|in|my)\b"
                    clean_slack_q = re.sub(stopwords, " ", clean_text, flags=re.I).strip()
                    clean_slack_q = " ".join(clean_slack_q.split())

                    if clean_slack_q and len(clean_slack_q) > 2:
                        found_msgs = slack.search_all_channels_for_query(clean_slack_q, limit_per_channel=10)
                        if found_msgs:
                            sources_accessed.append({
                                "name": "Slack",
                                "status_text": f"Messages found ({len(found_msgs)})",
                                "icon": "slack",
                                "verified": True,
                            })
                            evidence_lines = [f"Slack Messages matching '{clean_slack_q}':"]
                            for m in found_msgs[:5]:
                                evidence_lines.append(f"- [#{m.get('channel_name')}] User {m.get('user')}: {m.get('text')}")
                                rich_cards.append({
                                    "type": "slack",
                                    "title": f"#{m.get('channel_name')}",
                                    "metadata": f"Slack • User {m.get('user')}",
                                    "snippet": m.get("text", "")[:250],
                                    "action_label": "Open Slack",
                                })
                            retrieved_evidence.append("\n".join(evidence_lines))
                        else:
                            retrieved_evidence.append(f"Slack was searched for '{clean_slack_q}', but no matching messages were found.")
                    else:
                        channels = slack.list_channels(limit=10)
                        if channels:
                            sources_accessed.append({
                                "name": "Slack",
                                "status_text": f"Channels listed ({len(channels)})",
                                "icon": "slack",
                                "verified": True,
                            })
                            evidence_lines = ["Slack Channels:"]
                            for ch in channels:
                                evidence_lines.append(f"- **#{ch.get('name')}**: {ch.get('purpose') or ch.get('topic') or 'General discussion'} ({ch.get('num_members')} members)")
                                rich_cards.append({
                                    "type": "slack",
                                    "title": f"#{ch.get('name')}",
                                    "metadata": f"Slack • {ch.get('num_members')} members",
                                    "snippet": ch.get("purpose") or ch.get("topic") or "Slack discussion channel",
                                    "action_label": "View Channel",
                                })
                            retrieved_evidence.append("\n".join(evidence_lines))
                        else:
                            retrieved_evidence.append("Slack was queried, but no accessible channels were returned.")
                except Exception as e:
                    logger.error("Error retrieving Slack data: %s", str(e))
                    retrieved_evidence.append(f"Slack retrieval error: {str(e)}")

        # K. SQL Database Retrieval (PostgreSQL / SQLite)
        if has_database_intent:
            db_conn = DatabaseConnector()
            st = db_conn.get_status()
            if not st.get("authenticated"):
                retrieved_evidence.append(
                    "Database connector is ready and integrated, but POSTGRES_URL is not configured yet. "
                    "Configure it in the Connected Sources panel with a PostgreSQL or SQLite connection string."
                )
                sources_accessed.append({
                    "name": "SQL Database",
                    "status_text": "Code Ready (Awaiting Connection URL)",
                    "icon": "postgres",
                    "verified": False,
                })
            else:
                try:
                    tables = db_conn.list_tables()
                    target_table = None
                    for t in tables:
                        if re.search(rf"\b{re.escape(t)}\b", clean_text, re.I):
                            target_table = t
                            break

                    if target_table:
                        schema = db_conn.describe_table(target_table)
                        sample = db_conn.execute_read_query(f"SELECT * FROM {target_table}", limit=5)
                        sources_accessed.append({
                            "name": "SQL Database",
                            "status_text": f"Table '{target_table}' inspected",
                            "icon": "postgres",
                            "verified": True,
                        })
                        cols_summary = ", ".join([f"{col['name']} ({col['type']})" for col in schema.get("columns", [])])
                        evidence_lines = [
                            f"Database Table '{target_table}':",
                            f"- Columns: {cols_summary}",
                            f"- Row count: {sample.get('row_count', 0)}",
                            f"- Sample rows: {json.dumps(sample.get('rows', [])[:3])}"
                        ]
                        retrieved_evidence.append("\n".join(evidence_lines))
                        rich_cards.append({
                            "type": "database",
                            "title": f"Table: {target_table}",
                            "metadata": f"{st.get('database_type')} • {len(schema.get('columns', []))} columns",
                            "snippet": f"Columns: {cols_summary}",
                            "action_label": "View Table",
                        })
                    else:
                        sources_accessed.append({
                            "name": "SQL Database",
                            "status_text": f"{len(tables)} tables indexed",
                            "icon": "postgres",
                            "verified": True,
                        })
                        evidence_lines = [f"Connected {st.get('database_type')} Tables ({len(tables)} total):"]
                        for tbl in tables[:15]:
                            evidence_lines.append(f"- **{tbl}**")
                            rich_cards.append({
                                "type": "database",
                                "title": f"Table: {tbl}",
                                "metadata": f"{st.get('database_type')} Database",
                                "snippet": "Available table in database.",
                                "action_label": "Inspect Table",
                            })
                        retrieved_evidence.append("\n".join(evidence_lines))
                except Exception as e:
                    logger.error("Error retrieving Database data: %s", str(e))
                    retrieved_evidence.append(f"Database query error: {str(e)}")

        # L. Notion Retrieval
        if has_notion_intent:
            notion_key = os.getenv("NOTION_API_KEY")
            if not notion_key:
                retrieved_evidence.append(
                    "Notion connector is ready and integrated, but NOTION_API_KEY is not configured yet. "
                    "Configure your Notion Internal Integration Secret in the Connected Sources panel."
                )
                sources_accessed.append({
                    "name": "Notion",
                    "status_text": "Code Ready (Awaiting Integration Secret)",
                    "icon": "notion",
                    "verified": False,
                })
            else:
                try:
                    notion = get_notion_connector()
                    clean_notion_q = re.sub(r"\b(notion|page|pages|doc|docs|workspace|search|find|show|get|about|what|is)\b", " ", clean_text, flags=re.I).strip()
                    res = notion.search(query=clean_notion_q, page_size=5)
                    pages = res.get("results", [])
                    if pages:
                        sources_accessed.append({
                            "name": "Notion",
                            "status_text": f"Pages retrieved ({len(pages)})",
                            "icon": "notion",
                            "verified": True,
                        })
                        evidence_lines = [f"Notion Pages ({len(pages)} found):"]
                        for p in pages:
                            p_title = p.get("title", "Untitled")
                            p_url = p.get("url", "")
                            p_id = p.get("id", "")
                            content_excerpt = ""
                            try:
                                content_excerpt = notion.get_page_content(p_id, max_blocks=5)
                            except Exception:
                                pass
                            evidence_lines.append(
                                f"- **{p_title}** ({p.get('type')}) - Last edited: {p.get('last_edited_time')}\n  URL: {p_url}\n  Summary: {content_excerpt[:200]}"
                            )
                            rich_cards.append({
                                "type": "notion",
                                "title": p_title,
                                "metadata": f"Notion • {p.get('type')} • {str(p.get('last_edited_time', ''))[:10]}",
                                "snippet": content_excerpt[:200] or f"Notion page: {p_title}",
                                "link": p_url,
                                "action_label": "Open in Notion",
                            })
                        retrieved_evidence.append("\n".join(evidence_lines))
                    else:
                        retrieved_evidence.append(f"Notion was searched for '{clean_notion_q}', but no matching pages or databases were found.")
                except Exception as e:
                    logger.error("Error retrieving Notion data: %s", str(e))
                    retrieved_evidence.append(f"Notion retrieval error: {str(e)}")

        # Build prompt for Groq LLM
        system_prompt = (
            "You are an intelligent, professional workplace AI assistant for Shashvat at Appinventiv.\n"
            "You have access to connected workplace sources (Gmail, Google Drive, Slack, SQL Database, Notion, GitHub, SharePoint, Microsoft Teams, Azure DevOps, Local File Share, and LMS).\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. If the user greeting is mixed (e.g., 'Hi, find my latest email'), greet them cordially AND answer their source inquiry.\n"
            "2. Base your factual answers STRICTLY on the retrieved evidence provided below. Do NOT invent, assume, or fabricate any emails, files, senders, or code that is not present in the evidence.\n"
            "3. If the user asks 'What is in my last email' or asks about their 'latest email', focus your response EXCLUSIVELY on the single most recent email in the retrieved evidence. State clearly:\n"
            "   - **Subject**\n"
            "   - **From / Sender** (if it is a forwarded thread, clearly mention who sent or forwarded it, and original author if applicable)\n"
            "   - **Date & Time** (as stated in the email metadata)\n"
            "   - **What the email is about / Key Points / Action Items** in clear, easy-to-read bullet points.\n"
            "4. Do NOT output backslash-escaped brackets like \\< or \\> around email addresses. Write email addresses as Name <email@example.com>.\n"
            "5. When explaining GitHub projects, highlight: Repository name, purpose/README highlights, key files, and branch.\n"
            "6. If a source is unconfigured (like SharePoint/Teams awaiting admin credentials), state the actual status honestly and clearly.\n"
            "7. If the user asks a follow-up question (e.g. 'Summarize it' or 'Show more details'), reference the prior context accurately.\n"
            "8. Format your response cleanly using Markdown bullet points and bold headers.\n"
            "9. If the user asks 'what is in the drive latest file' or asks about their latest file/documents in Google Drive:\n"
            "   - Focus on the single most recent file by Last Modified timestamp (File 1 in the chronological evidence).\n"
            "   - State the **File Name**, **Type**, and **Last Modified Date & Time**.\n"
            "   - Provide a clear, structured explanation and key takeaways of **what is inside the file** using the extracted content excerpt provided in the evidence.\n"
            "   - If it is a spreadsheet, summarize the key rows/columns/questions. If it is a document, summarize the main sections and points."
        )

        ai_messages = [{"role": "system", "content": system_prompt}]

        # Append prior conversation history
        for m in prior_messages[-4:]:
            # If this is a fresh latest email query, avoid polluting with stale older email texts
            if (has_email_intent and (is_singular_latest or search_q == "")) and m.get("role") == "assistant" and any(c.get("type") == "email" for c in m.get("rich_cards", [])):
                continue
            ai_messages.append({"role": m["role"], "content": m["content"]})

        # Append current user question with evidence
        user_prompt_with_evidence = clean_text
        if retrieved_evidence:
            evidence_block = "\n\n---\n### RETRIEVED SOURCE EVIDENCE:\n" + "\n\n".join(retrieved_evidence) + "\n---"
            user_prompt_with_evidence += evidence_block

        ai_messages.append({"role": "user", "content": user_prompt_with_evidence})

        assistant_reply = call_groq_llm(ai_messages)

    # 6. Save assistant message to SQLite
    assistant_msg = db.add_message(
        session_id=session_id,
        role="assistant",
        content=assistant_reply,
        rich_cards=rich_cards,
        sources_accessed=sources_accessed,
    )

    # 7. Update session title if default
    if session and (session.get("title") in ["New chat", "New Chat", "Untitled"]):
        # Create a clean short title (first 4-6 words)
        words = clean_text.split()[:5]
        new_title = " ".join(words)
        if len(new_title) > 30:
            new_title = new_title[:27] + "..."
        db.update_session_title(session_id, new_title.capitalize())

    return {
        "user_message": user_msg,
        "assistant_message": assistant_msg,
    }
