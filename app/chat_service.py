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
from app.connectors.google_chat import get_google_chat_connector
from app.connectors.universal_parser import get_universal_parser_connector

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
    - If user specifies a sender (e.g. 'latest mail of sukhpreet', 'from HR', 'sukhpreet's email'),
      search_query is extracted so Gmail filters for that person.
    - If user specifies a topic/subject (e.g. 'about marketing launch'), search_query is that topic.
    - If user asks for pure latest email (e.g. 'tell about the last mail', 'What is in my last email'),
      search_query is "" so Gmail returns the true latest message chronologically.
    - If user specifies a specific date/time (e.g. 'onn date 16 oct 2:22' or 'at 2:22'),
      search_query is "" so messages can be accurately matched by timestamp in Python.
    """
    clean = normalize_text_for_email_search(text.strip())

    # 0. Check for specific date or time targets (e.g. 'onn date 16 oct 2:22', 'mail at 2:22')
    target_h, target_m, target_day, target_month = extract_gmail_date_time_target(clean)
    if target_h is not None or target_day is not None:
        # Return empty query to fetch recent batch and filter in Python
        return "", 20, bool(target_h is not None)

    # 1. Check sender
    sender = None
    poss_match = re.search(r"\b([A-Za-z0-9_.@-]+(?:\s+[A-Za-z0-9_.@-]+)*)'s\s+(?:last\s+|latest\s+|recent\s+)?(?:email|mail)\b", clean, re.I)
    if poss_match:
        cand = poss_match.group(1).strip()
        if cand.lower() not in ["me", "my", "mine", "us", "the"]:
            sender = cand
    else:
        of_match = re.search(
            r"\b(?:from:?|by|sent by|of)\s+([A-Za-z0-9_.@-]+(?:\s+[A-Za-z0-9_.@-]+)*?)(?=\s+\b(and|what|whats|what's|with|which|about|regarding|titled|subject|is|in|for|to|\?|!|\.)\b|$)",
            clean,
            re.I,
        )
        if of_match:
            cand = of_match.group(1).strip()
            if cand.lower() not in ["me", "my", "mine", "us", "him", "her", "them", "the", "an", "a", "our", "all"]:
                sender = cand
        else:
            send_match = re.search(r"\bwhat did\s+([A-Za-z0-9_.@-]+(?:\s+[A-Za-z0-9_.@-]+)*?)\s+send\b", clean, re.I)
            if send_match:
                cand = send_match.group(1).strip()
                if cand.lower() not in ["you", "i", "we", "they"]:
                    sender = cand

    # 2. Check topic
    topic = None
    about_match = re.search(r"\b(?:about|regarding|titled|subject)\s+([^?.!]+)", clean, re.I)
    if about_match:
        raw_topic = re.sub(r"\b(my|the|an?|emails?|please|find|show|tell|me|and|what|is|in|that)\b", "", about_match.group(1).strip(), flags=re.I).strip()
        if raw_topic and raw_topic.lower() not in ["last", "latest", "recent"]:
            topic = raw_topic

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

    # 3. If sender or topic is explicitly specified, search by them
    if sender or topic:
        query_parts = []
        if sender:
            if "@" in sender or (len(sender.split()) == 1 and not topic):
                query_parts.append(f"from:{sender}")
            else:
                query_parts.append(sender)
        if topic:
            query_parts.append(topic)
        query = " ".join(query_parts)
        return query, 3, is_singular_latest

    # 4. Pure latest / general latest queries (no sender, no topic filter)
    is_general_latest = bool(re.search(
        r"^(what(\x27s|\s+is)?\s+(in\s+)?(my\s+)?(last|latest|recent|new)(\s+email)?|tell(\s+me)?\s+about\s+(the\s+|my\s+)?(last|latest|recent)\s+email|find\s+(my\s+)?(last|latest|recent)\s+email|show\s+(my\s+)?(last|latest|recent)\s+email|check\s+(my\s+)?(last|latest|recent|inbox|email)|(any\s+)?new\s+email|my\s+(last|latest|recent)\s+email|get\s+(my\s+)?(last|latest|recent)\s+email)[!.,?\s]*$",
        clean,
        re.I,
    ))

    # If it is a pure inbox-wide latest/last query, return empty query for true chronological inbox order
    if is_singular_latest or is_general_latest:
        count = 1 if is_singular_latest else 3
        return "", count, is_singular_latest

    # 5. Fallback: Strip filler/conversational words
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


def call_groq_rag_synthesis(messages: list[dict[str, str]]) -> dict[str, Any]:
    """
    Invoke Groq LLM API requesting structured JSON containing:
    - answer_markdown: str
    - key_updates: list[str]
    - pending_actions: list[str]
    - suggested_followups: list[str]
    """
    if not GROQ_API_KEY:
        return {
            "answer_markdown": "GROQ_API_KEY is not configured in .env. Please configure it to enable AI responses.",
            "key_updates": [],
            "pending_actions": [],
            "suggested_followups": [],
        }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1500,
            "response_format": {"type": "json_object"},
        }
        try:
            resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                raw_txt = data["choices"][0]["message"]["content"].strip()
                try:
                    parsed = json.loads(raw_txt)
                    if isinstance(parsed, dict) and "answer_markdown" in parsed:
                        return parsed
                except Exception:
                    return {
                        "answer_markdown": raw_txt,
                        "key_updates": [],
                        "pending_actions": [],
                        "suggested_followups": [],
                    }
            logger.warning("Groq model %s returned status %d: %s", model_name, resp.status_code, resp.text)
        except Exception as e:
            logger.warning("Error invoking Groq model %s: %s", model_name, str(e))

    return {
        "answer_markdown": "I'm having trouble connecting to the AI language model at the moment. Please try again shortly.",
        "key_updates": [],
        "pending_actions": [],
        "suggested_followups": [],
    }


def plan_retrieval_strategy(user_text: str, prior_messages: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Intelligent LLM-powered Query Intent & Retrieval Planner for Dabur One Enterprise AI.
    Understands questions in English, Hindi, Hinglish, informal, shorthand, or complex phrases
    WITHOUT requiring any hardcoded keywords.
    Dynamically identifies which connected enterprise source(s) to query and generates optimal search parameters.
    """
    clean = user_text.strip()
    if GREETING_REGEX.match(clean) and len(clean.split()) <= 3:
        return {
            "is_pure_greeting": True,
            "sources": [],
            "gmail_query": "",
            "gmail_count": 0,
            "drive_query": "",
            "github_query": "",
            "slack_query": "",
            "database_query": "",
            "notion_query": "",
            "user_intent_summary": "Greeting",
        }

    history_snippets = []
    for m in prior_messages[-3:]:
        role = m.get("role", "user")
        cnt = m.get("content", "")[:200]
        history_snippets.append(f"{role.capitalize()}: {cnt}")
    context_str = "\n".join(history_snippets)

    system_prompt = (
        "You are the intelligent Retrieval & Intent Planner for Cerebro Enterprise AI.\n"
        "Your job is to understand any question from an employee (in English, Hindi, or Hinglish) "
        "WITHOUT requiring any hardcoded keywords or exact commands.\n\n"
        "Available Connected Enterprise Systems:\n"
        "- 'gmail': emails, email threads, forwarded messages, sender communications, meeting invites, Minutes of Meeting (MoM), agendas, approvals, deliverables, leaves, and daily updates.\n"
        "- 'google_chat': Google Workspace chats, Google Chat spaces, direct messages, team chats, real-time messaging discussions.\n"
        "- 'google_drive': presentations, slides, decks, docs, spreadsheets, PDFs, files on Drive.\n"
        "- 'github': code repositories, branches, commits, pull requests, technical codebases.\n"
        "- 'slack': team chat channels, direct messages, daily standups.\n"
        "- 'database': PostgreSQL database, tables, schema, customer data, SQL queries.\n"
        "- 'notion': internal wiki pages, handbook, policies, company notes.\n"
        "- 'sharepoint': corporate policies, department intranets, guidelines.\n"
        "- 'lms': employee training courses, LMS certifications, learning modules.\n"
        "- 'file_share': network shared folders and server files.\n"
        "- 'universal_parser': multimodal document parser ensemble (Parse and Furious), extracting text, tables, OCR, and RAG chunks from PDFs, Word docs, Excel sheets, PPTX presentations, invoices, and image files.\n\n"
        "Rules:\n"
        "1. If user is greeting ('hi', 'hello', 'good morning', 'namaste', 'thanks', 'bye') without asking for information, set 'is_pure_greeting': true and 'sources': [].\n"
        "2. If user asks about being away, absence, leave, or updates from the last 3 days ('away for 3 days', 'chhutti par tha', 'what happened while I was away', 'catch up'):\n"
        "   - Set 'sources': ['gmail', 'google_drive', 'google_chat'].\n"
        "   - Set 'gmail_query': '' and set 'gmail_count': 15 to retrieve the batch of all recent messages across the absence window.\n"
        "   - Set 'drive_query': '' and 'chat_query': ''.\n"
        "3. If user asks about chat, messages, or Google Chat with a person (e.g. 'chat with Sagar', 'message with Anish', 'what is the last message with Anish'):\n"
        "   - Set 'sources': ['google_chat']. (DO NOT include 'gmail' unless user explicitly asks for email!)\n"
        "   - Set 'chat_query': person's name.\n"
        "4. If user asks about emails from or with a person (e.g. 'email from Sagar', 'mail from Rahul'):\n"
        "   - Set 'sources': ['gmail']. (DO NOT include 'google_chat' unless user asks for chat!)\n"
        "   - Set 'gmail_query': person's name, 'gmail_count': 5.\n"
        "5. If user asks generally about communications or updates with a person without specifying chat or email (e.g. 'Priya ke sath kya baat hui', 'updates from Rahul'):\n"
        "   - Set 'sources': ['google_chat', 'gmail'].\n"
        "   - Set 'gmail_query': person's name, 'chat_query': person's name, 'gmail_count': 5.\n"
        "6. For general single latest email queries ('what is in my last email', 'tell me about latest email'):\n"
        "   - Set 'sources': ['gmail'], 'gmail_query': '', 'gmail_count': 1.\n"
        "7. For specific topics, products, or campaigns (e.g. 'Chyawanprash launch', 'marketing updates', 'vendor contract'):\n"
        "   - Search for the core topic keyword (e.g. 'Chyawanprash').\n"
        "   - Set 'sources': ['gmail', 'google_drive'], 'gmail_count': 5.\n"
        "8. If user asks about chat rooms, spaces, or channels in Google Chat (e.g. 'any chat rooms', 'what rooms do I have', 'list chat rooms', 'show spaces', 'any chat rooms ??'):\n"
        "   - Set 'sources': ['google_chat'], 'chat_query': 'spaces'.\n"
        "9. If user asks for unread chats, latest chats, or a summary of chats (e.g. 'summary of unreads chat in google chat', 'unread messages', 'catch up on chats'):\n"
        "   - Set 'sources': ['google_chat'], 'chat_query': ''. (DO NOT put words like 'unread', 'summary', or question words into chat_query!)\n"
        "10. If user asks to parse, analyze, OCR, read, or extract tables from a document, PDF, file, attachment, invoice, or spreadsheet (e.g. 'parse this PDF', 'extract table from invoice', 'read document', 'analyze Q3 report', 'universal parser'):\n"
        "   - Set 'sources': ['universal_parser'], 'parser_query': 'parse'.\n"
        "11. Return ONLY a valid JSON object matching this schema:\n"
        "{\n"
        "  \"is_pure_greeting\": false,\n"
        "  \"sources\": [\"gmail\"],\n"
        "  \"gmail_query\": \"sukhpreet singh kalra\",\n"
        "  \"gmail_count\": 3,\n"
        "  \"drive_query\": \"\",\n"
        "  \"chat_query\": \"\",\n"
        "  \"parser_query\": \"\",\n"
        "  \"github_query\": \"\",\n"
        "  \"slack_query\": \"\",\n"
        "  \"database_query\": \"\",\n"
        "  \"notion_query\": \"\",\n"
        "  \"user_intent_summary\": \"Looking for latest email from Sukhpreet Singh Kalra and agenda details\"\n"
        "}"
    )

    if GROQ_API_KEY:
        try:
            resp = requests.post(
                GROQ_API_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "openai/gpt-oss-20b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Recent Conversation Context:\n{context_str}\n\nUser Question: {clean}"}
                    ],
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"}
                },
                timeout=8
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_json = data["choices"][0]["message"]["content"].strip()
                parsed = json.loads(raw_json)
                if isinstance(parsed, dict) and "sources" in parsed:
                    return parsed
        except Exception as e:
            logger.warning("LLM retrieval planner fallback due to error: %s", str(e))

    # Fast heuristic fallback if LLM planner times out or is offline
    fallback_sources = []
    clean_norm = normalize_text_for_email_search(clean)
    target_h, target_m, target_day, target_month = extract_gmail_date_time_target(clean_norm)
    has_email = bool(
        re.search(r"\b(email|emails|mail|mails|gmail|inbox|sent)\b", clean_norm, re.I)
        or (target_h is not None or target_day is not None)
    )
    if has_email:
        fallback_sources.append("gmail")
    if re.search(r"\b(google\s*chat|gchat|chat|chats|chat\s*space|spaces?|dm|messages?)\b", clean, re.I):
        fallback_sources.append("google_chat")
    if re.search(r"\b(github|repo|code|commit|branch|pr)\b", clean, re.I):
        fallback_sources.append("github")
    if re.search(r"\b(drive|google\s*doc|doc|deck|presentation|sheet)\b", clean, re.I):
        fallback_sources.append("google_drive")
    if re.search(r"\b(postgres|sql|database|table|query)\b", clean, re.I):
        fallback_sources.append("database")
    if re.search(r"\b(slack|channel|dm)\b", clean, re.I):
        fallback_sources.append("slack")
    if re.search(r"\b(notion|wiki|page)\b", clean, re.I):
        fallback_sources.append("notion")

    # Absence / catch-up query detection
    is_away_query = bool(re.search(r"\b(away|days?|chhutti|leave|vacation|catch\s*up|behind)\b", clean, re.I))
    if is_away_query:
        for s in ["gmail", "google_drive", "google_chat"]:
            if s not in fallback_sources:
                fallback_sources.append(s)

    # If no source was detected, default to searching Gmail so broad questions still check communications
    if not fallback_sources and not GREETING_REGEX.match(clean):
        fallback_sources.append("gmail")

    g_q, g_cnt, _ = extract_gmail_query_and_count(clean)
    if is_away_query:
        g_cnt = 15
        g_q = ""

    return {
        "is_pure_greeting": bool(GREETING_REGEX.match(clean) and len(clean.split()) <= 3),
        "sources": fallback_sources,
        "gmail_query": g_q,
        "gmail_count": g_cnt,
        "drive_query": clean if not is_away_query else "",
        "chat_query": clean if not is_away_query else "",
        "github_query": clean,
        "slack_query": clean,
        "database_query": clean,
        "notion_query": clean,
        "user_intent_summary": clean,
    }


def rerank_and_filter_evidence(query: str, rich_cards: list[dict[str, Any]], max_items: int = 5) -> list[dict[str, Any]]:
    """
    Cross-Encoder / LLM Relevance Reranker for enterprise workplace retrieval.
    Filters out noise (e.g. incidental calendar invites, marketing emails, unrelated forwards)
    and sorts candidates in descending order of direct relevance to the user's specific query.
    Falls back gracefully to term-overlap ranking if the LLM call times out or fails.
    """
    if not rich_cards or len(rich_cards) <= 1:
        return rich_cards[:max_items]

    query_lower = query.lower()
    query_terms = [
        t for t in re.findall(r"\w+", query_lower)
        if len(t) > 2 and t not in ["what", "with", "from", "that", "this", "tell", "show", "last", "latest", "recent", "about", "give"]
    ]

    def token_overlap_score(card: dict[str, Any]) -> float:
        text = f"{card.get('title', '')} {card.get('metadata', '')} {card.get('snippet', '')} {card.get('sender_name', '')}".lower()
        score = 0.0
        # If user explicitly asked about chat and card is chat, boost
        if any(w in query_lower for w in ["chat", "message", "dm", "gchat"]) and card.get("type") in ["chat", "google_chat", "slack"]:
            score += 3.0
        # If user explicitly asked about email and card is email, boost
        if any(w in query_lower for w in ["email", "mail", "gmail", "inbox"]) and card.get("type") == "email":
            score += 3.0
        for term in query_terms:
            if term in text:
                score += 1.5
        return score

    if not GROQ_API_KEY:
        sorted_cards = sorted(rich_cards, key=token_overlap_score, reverse=True)
        return sorted_cards[:max_items]

    # Prepare candidate items summary for reranking
    candidates = []
    for i, c in enumerate(rich_cards[:15]):
        c_type = c.get("type", "item")
        title = c.get("title", "")
        sender = c.get("sender_name") or c.get("metadata", "")
        snippet = (c.get("snippet") or "")[:200]
        candidates.append(f"[{i}] Type: {c_type} | Title: {title} | Sender: {sender} | Excerpt: {snippet}")

    system_prompt = (
        "You are an enterprise workplace search reranker.\n"
        "Given the user query and candidate items, return ONLY a JSON object: {\"indices\": [int, ...]} containing 0-based indices in descending order of direct relevance.\n\n"
        "CRITICAL RULES:\n"
        "1. If the user query is about chat or messages with a person, strictly prefer Chat/DM items and EXCLUDE automated calendar invitations, Google Drive spreadsheet shares, or marketing emails.\n"
        "2. If an item is an automated calendar invite or an email where the person is merely mentioned or CC'd, exclude it unless the user specifically asked for calendar invites or emails.\n"
        "3. Exclude completely irrelevant items that do not help answer the query.\n"
        "4. Return the top relevant indices only."
    )

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "openai/gpt-oss-120b",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"User Query: {query}\n\nCandidate Items:\n" + "\n".join(candidates)}
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            },
            timeout=6
        )
        if resp.status_code == 200:
            data = resp.json()
            raw_content = data["choices"][0]["message"]["content"].strip()
            parsed = json.loads(raw_content)
            indices = parsed.get("indices", [])
            filtered = [rich_cards[idx] for idx in indices if isinstance(idx, int) and 0 <= idx < len(rich_cards)]
            if filtered:
                return filtered[:max_items]
    except Exception as e:
        logger.warning("Groq reranker fallback due to error: %s", str(e))

    sorted_cards = sorted(rich_cards, key=token_overlap_score, reverse=True)
    return sorted_cards[:max_items]


def process_chat_turn(session_id: str, user_text: str) -> dict[str, Any]:
    """
    Process a chat turn:
    1. Save user message.
    2. Retrieve conversation history.
    3. Intelligent Intent & Source Retrieval Planning (Zero-hardcoding).
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
    active_doc = session.get("active_document") if session else None

    # If current message has an attached document, persist it as the session's active document
    if "[Attached Document:" in clean_text:
        doc_match = re.search(r"\[Attached Document:\s*([^(\]\n]+)(?:\(([^)]*)\))?\]", clean_text)
        doc_filename = doc_match.group(1).strip() if doc_match else "Attached Document"
        body_parts = clean_text.split("User Question:")
        raw_doc_body = body_parts[0] if len(body_parts) > 1 else clean_text
        doc_content = re.sub(r"\[Attached Document:[^\]]+\]", "", raw_doc_body).strip()
        doc_content = re.sub(r"^Content Excerpt:\s*", "", doc_content).strip()
        active_doc = {
            "filename": doc_filename,
            "text": doc_content,
            "elements_count": 0,
        }
        db.set_session_document(session_id, active_doc)

    # Take prior messages (excluding the message just inserted)
    prior_messages = [m for m in history_messages if m["id"] != user_msg["id"]][-6:]

    # 3. Intelligent Intent & Source Retrieval Planning (Zero-hardcoding)
    plan = plan_retrieval_strategy(clean_text, prior_messages)
    is_pure_greeting = plan.get("is_pure_greeting", False)
    planned_sources = plan.get("sources", [])

    has_email_intent = "gmail" in planned_sources or bool(plan.get("gmail_query"))
    has_gchat_intent = "google_chat" in planned_sources or bool(plan.get("chat_query")) or bool(re.search(r"\b(google\s*chat|gchat|chat\s*space|spaces?)\b", clean_text, re.I))

    # If the user explicitly asked for chat/messages without mentioning emails or mail, do not query Gmail
    is_explicit_chat_only = (
        bool(re.search(r"\b(chat|chats|google\s*chat|gchat|dm|slack|message|messages)\b", clean_text, re.I))
        and not bool(re.search(r"\b(email|emails|mail|mails|gmail|inbox)\b", clean_text, re.I))
    )
    if is_explicit_chat_only:
        has_email_intent = False
        has_gchat_intent = True
    has_drive_intent = "google_drive" in planned_sources or bool(plan.get("drive_query"))
    has_github_intent = "github" in planned_sources or bool(plan.get("github_query"))
    has_slack_intent = "slack" in planned_sources or bool(plan.get("slack_query"))
    has_database_intent = "database" in planned_sources or bool(plan.get("database_query"))
    has_notion_intent = "notion" in planned_sources or bool(plan.get("notion_query"))
    has_sharepoint_intent = "sharepoint" in planned_sources or bool(re.search(r"\b(sharepoint|teams|microsoft)\b", clean_text, re.I))
    has_fileshare_intent = "file_share" in planned_sources or bool(re.search(r"\b(file\s*share|shared\s*folder|test-share)\b", clean_text, re.I))
    has_lms_intent = "lms" in planned_sources or bool(re.search(r"\b(lms|course|courses|learning)\b", clean_text, re.I))
    has_servicenow_intent = "servicenow" in planned_sources
    has_salesforce_intent = "salesforce" in planned_sources
    has_jira_intent = "jira" in planned_sources
    has_parser_intent = (
        bool(active_doc)
        or "universal_parser" in planned_sources
        or bool(plan.get("parser_query"))
        or bool(re.search(r"\b(universal\s*parser|parse\s*(this|document|pdf|file|table|sheet)?|ocr|extract\s*table|extract\s*tables|document\s*parser|certificate|score|marks|grade|roll\s*no|roll\s*number|awarded|exam|nptel)\b", clean_text, re.I))
    )

    rich_cards: list[dict[str, Any]] = []
    sources_accessed: list[dict[str, Any]] = []
    retrieved_evidence: list[str] = []
    summary_block: dict[str, Any] | None = None
    suggested_followups: list[str] = []
    search_q = ""
    is_singular_latest = False

    # Check previous conversation context for follow-ups
    prev_cards = []
    for m in reversed(prior_messages):
        if m.get("role") == "assistant" and m.get("rich_cards"):
            prev_cards = m["rich_cards"]
            break

    # Genuine followup: short conversational inquiry referring to previous card context
    has_explicit_query = bool(plan.get("gmail_query") or plan.get("drive_query") or plan.get("chat_query"))
    is_followup = bool(
        prev_cards
        and not has_explicit_query
        and FOLLOWUP_REGEX.search(clean_text)
        and len(clean_text.split()) <= 7
    )

    if is_followup and not (has_email_intent or has_gchat_intent or has_github_intent or has_sharepoint_intent or has_drive_intent or has_jira_intent or has_servicenow_intent or has_salesforce_intent or has_slack_intent or has_database_intent or has_notion_intent):
        if any(c.get("type") == "email" for c in prev_cards):
            has_email_intent = True
        elif any(c.get("type") in ["chat", "google_chat"] for c in prev_cards):
            has_gchat_intent = True
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
                planned_g_q = plan.get("gmail_query")
                if planned_g_q is not None:
                    search_q = planned_g_q
                    fetch_count = plan.get("gmail_count", 3)
                    is_singular_latest = (fetch_count == 1 and not search_q)
                else:
                    search_q, fetch_count, is_singular_latest = extract_gmail_query_and_count(clean_text)

                is_away = bool(re.search(r"\b(away|days?|chhutti|leave|vacation|catch\s*up|behind)\b", clean_text, re.I))
                if is_away:
                    search_q = ""
                    fetch_count = 15
                    is_singular_latest = False

                target_h, target_m, target_day, target_month = extract_gmail_date_time_target(clean_normalized)
                if is_followup and not search_q:
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

                    # Get authenticated user email for precise account URL
                    user_email = ""
                    try:
                        u_stat = gmail.get_status()
                        user_email = u_stat.get("email_address", "")
                    except Exception:
                        pass

                    # If user asked specifically for chat, prioritize chat notifications or direct correspondence from the person
                    is_explicit_chat_intent = bool(re.search(r"\b(chat|gchat|google\s*chat|slack|dm)\b", clean_text, re.I)) and not bool(re.search(r"\b(emails?|mails?|inbox)\b", clean_text, re.I))
                    if is_explicit_chat_intent:
                        filtered_msgs = []
                        for m_meta in messages_list:
                            s_lower = (m_meta.get("subject", "") + " " + m_meta.get("from", "")).lower()
                            if "chat" in s_lower or (planned_g_q and planned_g_q.lower() in m_meta.get("from", "").lower()):
                                filtered_msgs.append(m_meta)
                        if filtered_msgs:
                            messages_list = filtered_msgs

                    # Fetch full details of target messages
                    for idx, m_meta in enumerate(messages_list[:fetch_count]):
                        m_id = m_meta["id"]
                        full_msg = gmail.get_message(m_id)
                        thread_id = full_msg.get("thread_id") or m_id
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
                        body = full_msg.get("body_text", clean_snippet)[:3500]
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

                        # Deep link directly to email in Gmail web using valid authuser param
                        gmail_web_link = (
                            f"https://mail.google.com/mail/?authuser={user_email}#all/{thread_id}"
                            if user_email
                            else f"https://mail.google.com/mail/#all/{thread_id}"
                        )

                        rich_cards.append({
                            "type": "email",
                            "title": subject,
                            "metadata": f"Gmail • From: {sender} • {date}",
                            "snippet": clean_snippet or (body[:150] + "..."),
                            "link": gmail_web_link,
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

        # J2. Google Chat Retrieval
        if has_gchat_intent:
            gchat_token_file = os.path.exists(".google_chat_token.json")
            if not gchat_token_file:
                retrieved_evidence.append(
                    "Google Chat connector is integrated, but OAuth authentication is pending. "
                    "Please connect Google Chat via OAuth in Knowledge Hub (visit /google-chat/auth/login)."
                )
                sources_accessed.append({
                    "name": "Google Chat",
                    "status_text": "OAuth Pending",
                    "icon": "google_chat",
                    "verified": False,
                })
            else:
                try:
                    gchat = get_google_chat_connector()
                    chat_q = plan.get("chat_query") or clean_text

                    # Detect if user is asking to list or inspect rooms/spaces
                    is_asking_rooms = (
                        chat_q.strip().lower() == "spaces"
                        or bool(re.search(r"\b(any\s+(chat\s+)?rooms?|list\s+(chat\s+)?rooms?|what\s+(chat\s+)?rooms?|show\s+(chat\s+)?rooms?|what\s+spaces?|list\s+spaces?|available\s+rooms?|available\s+spaces?)\b", clean_text, re.I))
                        or bool(re.search(r"^\s*any\s+chat\s+rooms\s*\??\s*$", clean_text, re.I))
                        or (bool(re.search(r"\b(rooms?|spaces?)\b", clean_text, re.I)) and not re.search(r"\b(in\s+the\s+room|in\s+the\s+space|in\s+room)\b", clean_text, re.I) and not bool(re.search(r"\b(message|talk|said|text)\b", clean_text, re.I)))
                    )

                    if is_asking_rooms:
                        spaces_res = gchat.list_spaces(page_size=50)
                        all_spaces = spaces_res.get("spaces", [])
                        named_rooms = [s for s in all_spaces if s.get("displayName") and s.get("displayName").strip() and s.get("displayName") != "Direct Message"]
                        dm_spaces = [s for s in all_spaces if not s.get("displayName") or s.get("displayName") == "Direct Message"]

                        if all_spaces:
                            sources_accessed.append({
                                "name": "Google Chat",
                                "status_text": f"Found {len(named_rooms)} chat rooms ({len(all_spaces)} spaces total)",
                                "icon": "google_chat",
                                "verified": True,
                            })
                            evidence_lines = [
                                f"Google Chat Accessible Rooms & Spaces for Shashvat Sharma (Total: {len(all_spaces)} spaces):",
                                f"Team Chat Rooms / Project Spaces ({len(named_rooms)} active):"
                            ]
                            for idx, rm in enumerate(named_rooms, 1):
                                r_name = rm.get("displayName")
                                r_link = rm.get("webLink") or "https://mail.google.com/chat"
                                evidence_lines.append(f"{idx}. **{r_name}** (Type: {rm.get('type') or 'Space'}, Link: {r_link})")
                                if idx <= 8:
                                    rich_cards.append({
                                        "type": "chat",
                                        "title": r_name,
                                        "sender_name": "Google Chat Room",
                                        "snippet": f"Active collaboration space for team discussions.",
                                        "link": r_link,
                                        "action_label": "Open in Google Chat",
                                        "department": "Google Chat",
                                    })
                            evidence_lines.append(f"\nDirect Message Conversations: {len(dm_spaces)} active 1-on-1 conversations.")
                            retrieved_evidence.append("\n".join(evidence_lines))
                        else:
                            retrieved_evidence.append("Google Chat was checked, but no accessible spaces or chat rooms were found.")
                    else:
                        stopwords = r"\b(google\s*chat|gchat|chat|space|spaces|messages?|show|list|get|find|search|about|what|is|in|my|last|latest|recent|newest|all|give|the|summary|summarize|unread|unreads|any|tell|check|room|rooms)\b"
                        clean_chat_q = re.sub(stopwords, " ", chat_q, flags=re.I).strip()
                        clean_chat_q = re.sub(r"[?!.,'\"]+", "", clean_chat_q).strip()

                        is_unread_query = bool(re.search(r"\b(unreads?|not read|pending chats?)\b", clean_text, re.I))

                        search_res = gchat.search_messages(clean_chat_q, max_results=8)
                        msgs = search_res.get("messages", [])
                        if msgs:
                            sources_accessed.append({
                                "name": "Google Chat",
                                "status_text": f"Messages found ({len(msgs)})",
                                "icon": "google_chat",
                                "verified": True,
                            })
                            evidence_lines = []
                            if is_unread_query:
                                evidence_lines.append(
                                    "NOTE ON UNREAD STATUS: The Google Chat REST API does not provide a server-side read/unread flag for messages. "
                                    "Therefore, Cerebro retrieves the latest active messages across your spaces and DMs (ordered newest-first) to give you an unread catch-up briefing:\n"
                                )
                            evidence_lines.append(f"Google Chat Recent Messages (query: '{clean_chat_q or 'latest activity'}'):")
                            for m in msgs:
                                evidence_lines.append(
                                    f"- Space: {m.get('space_name')} | Sender: {m.get('sender')} | Time: {m.get('createTime')}\n"
                                    f"  Message Context: {m.get('dialogue_context') or m.get('text')}"
                                )
                                rich_cards.append({
                                    "type": "chat",
                                    "title": f"Chat in {m.get('space_name')}",
                                    "sender_name": m.get("sender"),
                                    "date_str": str(m.get("createTime", ""))[:19].replace("T", " "),
                                    "snippet": m.get("text"),
                                    "link": m.get("link") or "https://mail.google.com/chat",
                                    "action_label": "Open in Google Chat",
                                    "department": "Google Chat",
                                })
                            retrieved_evidence.append("\n".join(evidence_lines))
                        else:
                            retrieved_evidence.append(f"Google Chat was searched, but no messages were found for query: '{clean_chat_q}'.")
                            sources_accessed.append({
                                "name": "Google Chat",
                                "status_text": "No messages found",
                                "icon": "google_chat",
                                "verified": True,
                            })
                except Exception as e:
                    logger.error("Error retrieving Google Chat data: %s", str(e))
                    retrieved_evidence.append(f"Google Chat retrieval error: {str(e)}")

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

        # M. Universal Document Parser Retrieval
        if has_parser_intent or active_doc:
            try:
                parser_conn = get_universal_parser_connector()
                st = parser_conn.get_status()
                if not st.get("is_connected"):
                    sources_accessed.append({
                        "name": "Universal Document Parser",
                        "status_text": "Service Offline",
                        "icon": "document_parser",
                        "verified": False,
                    })
                    retrieved_evidence.append("Universal Document Parser engine is offline at " + st.get("base_url", "http://127.0.0.1:8000"))
                else:
                    sources_accessed.append({
                        "name": "Universal Document Parser",
                        "status_text": f"Live (Ensemble v{st.get('version', '0.1.0')})",
                        "icon": "document_parser",
                        "verified": True,
                    })

                    # If this session has an active document, ALWAYS inject its content as primary evidence
                    if active_doc and active_doc.get("text"):
                        doc_fname = active_doc.get("filename", "Uploaded Document")
                        doc_body = active_doc.get("text", "")
                        retrieved_evidence.append(
                            f"ACTIVE SESSION DOCUMENT '{doc_fname}' (Parsed via Universal Parser):\n"
                            f"----------------------------------------\n"
                            f"{doc_body}\n"
                            f"----------------------------------------"
                        )
                        rich_cards.append({
                            "type": "document_parser",
                            "title": f"Active Document: {doc_fname}",
                            "metadata": f"Universal Parser • {active_doc.get('elements_count', 0)} elements • Active Session",
                            "snippet": (doc_body[:250] + "...") if len(doc_body) > 250 else doc_body,
                            "action_label": "Inspect Document",
                            "full_content": doc_body,
                            "tables": active_doc.get("tables", []),
                            "elements_count": active_doc.get("elements_count", 0),
                            "department": "Document Parser",
                            "sender_name": "Universal Document Parser",
                            "sender_initials": "DP",
                            "badge_color": "#059669",
                        })
                    else:
                        # Check for documents in test-share or query
                        target_file = None
                        file_share_root = os.getenv("FILE_SHARE_ROOT", "/home/appinventiv/source-systems-poc/test-share")
                        if os.path.isdir(file_share_root):
                            for f in sorted(os.listdir(file_share_root)):
                                if f.lower().endswith(('.pdf', '.docx', '.xlsx', '.txt', '.md', '.csv', '.png', '.jpg')):
                                    if f.lower() in clean_text.lower() or not target_file:
                                        target_file = os.path.join(file_share_root, f)
                                        if f.lower() in clean_text.lower():
                                            break
                        
                        if target_file and os.path.exists(target_file):
                            with open(target_file, "rb") as fh:
                                raw_bytes = fh.read()
                            fname = os.path.basename(target_file)
                            parse_res = parser_conn.extract_text_and_tables(raw_bytes, fname, mode="balanced")
                            doc_text = parse_res.get("text", "")[:3500]
                            tables = parse_res.get("tables", [])
                            tbl_summary = f"{len(tables)} tables extracted" if tables else "No tabular elements"
                            retrieved_evidence.append(
                                f"Universal Document Parser Parsed Document '{fname}' ({len(raw_bytes)} bytes, {parse_res.get('elements_count')} elements, {parse_res.get('duration_ms', 0):.1f}ms):\n"
                                f"- Tabular: {tbl_summary}\n"
                                f"- Content Excerpt:\n{doc_text}"
                            )
                            rich_cards.append({
                                "type": "document_parser",
                                "title": f"Parsed Document: {fname}",
                                "metadata": f"Universal Parser • {parse_res.get('elements_count')} elements • {parse_res.get('duration_ms', 0):.1f}ms",
                                "snippet": (doc_text[:250] + "...") if len(doc_text) > 250 else doc_text,
                                "action_label": "Inspect Document",
                                "full_content": doc_text,
                                "tables": tables,
                                "elements_count": parse_res.get("elements_count", 0),
                                "department": "Document Parser",
                                "sender_name": "Universal Document Parser",
                                "sender_initials": "DP",
                                "badge_color": "#059669",
                            })
                        else:
                            formats_str = ", ".join(st.get("supported_formats", []))
                            modes_str = ", ".join(st.get("modes", []))
                            retrieved_evidence.append(
                                "Universal Document Parser (Parse and Furious) is active, connected, and operational.\n"
                                f"- Supported Formats: {formats_str}\n"
                                f"- Available Modes: {modes_str}\n"
                                "- Features: Cell-by-cell table grounding, OCR via Tesseract, prompt-injection defense, and token-bounded RAG chunks.\n"
                                "- Usage: Upload a file via the paperclip attachment icon or query any document in the workspace."
                            )
                            rich_cards.append({
                                "type": "document_parser",
                                "title": "Universal Document Parser Engine",
                                "metadata": f"Ensemble Engine • {len(st.get('supported_formats', []))} formats supported",
                                "snippet": "Multi-format document parsing ensemble for PDF, Word, Excel, PPTX, OCR, and table grounding.",
                                "action_label": "Inspect Engine",
                                "full_content": (
                                    "Universal Document Parser (Parse and Furious) Capabilities:\n\n"
                                    f"• Supported Formats: {formats_str}\n"
                                    f"• Available Modes: {modes_str}\n"
                                    "• Features:\n"
                                    "  - Cell-by-cell table grounding\n"
                                    "  - Direct OCR & visual figure text extraction\n"
                                    "  - Prompt-injection & invisible text defense\n"
                                    "  - Token-bounded RAG chunks"
                                ),
                                "department": "Document Parser",
                                "sender_name": "Universal Document Parser",
                                "sender_initials": "DP",
                                "badge_color": "#059669",
                            })
            except Exception as e:
                logger.error("Error invoking Universal Document Parser: %s", str(e))
                retrieved_evidence.append(f"Universal Document Parser error: {str(e)}")

        # Enrich email cards with initials, department tags, and branding badges
        for card in rich_cards:
            if card.get("type") == "email":
                if not card.get("sender_initials"):
                    snd = card.get("metadata", "")
                    words = re.findall(r"[A-Za-z]+", snd)
                    inits = "".join([w[0].upper() for w in words[:2]]) if words else "EM"
                    card["sender_initials"] = inits
                t_lower = (card.get("title", "") + " " + card.get("snippet", "")).lower()
                if not card.get("department"):
                    if "marketing" in t_lower or "creative" in t_lower:
                        card["department"] = "Marketing"
                        card["badge_color"] = "#EF4444"
                    elif "sales" in t_lower or "retail" in t_lower or "stock" in t_lower:
                        card["department"] = "Sales"
                        card["badge_color"] = "#3B82F6"
                    elif "pack" in t_lower or "r&d" in t_lower or "quality" in t_lower:
                        card["department"] = "R&D"
                        card["badge_color"] = "#0D9488"
                    elif "digital" in t_lower or "media" in t_lower or "ad" in t_lower:
                        card["department"] = "Digital"
                        card["badge_color"] = "#F59E0B"
                    else:
                        card["department"] = "General"
                        card["badge_color"] = "#164E33"

        # Cross-Encoder / LLM Relevance Reranking & Noise Filtering
        if len(rich_cards) > 1:
            rich_cards = rerank_and_filter_evidence(clean_text, rich_cards, max_items=5)

        # Build prompt for Groq LLM (Dynamic RAG Synthesis)
        system_prompt = (
            "You are Cerebro, the intelligent, trusted enterprise workplace AI assistant for Shashvat.\n"
            "You have access to connected enterprise sources (Gmail, Google Chat, Google Drive, Slack, SQL Database, Notion, SharePoint, Teams, Universal Document Parser, and Local File Share).\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Base your factual answers STRICTLY on the retrieved evidence provided below. Do NOT invent, assume, or fabricate any emails, files, senders, or content that is not present in the evidence.\n"
            "   Prioritize the most directly relevant communications that answer the user's specific question. Disregard incidental mentions, automated calendar notifications, or third-party email threads where a person was only in CC unless asked.\n"
            "2. If no matching emails or documents were found in the evidence (for example, if a topic was searched but returned no results):\n"
            "   - State clearly and honestly that no emails or files matched the query in the connected account.\n"
            "   - Return EMPTY arrays [] for 'key_updates' and 'pending_actions'.\n"
            "   - Suggest next steps or alternative search terms.\n"
            "3. If evidence was retrieved:\n"
            "   - For email inquiries, extract the exact Subject, Sender, Date, Executive Summary, Key Highlights, and real Action Items.\n"
            "   - For absence/catch-up inquiries ('away for 3 days', 'what happened while I was away'): synthesize what actually arrived or changed across the retrieved emails and documents. Highlight Key Developments, Decisions, and Urgent Actions.\n"
            "   - For document analysis (PDFs, certificates, invoices, reports): inspect the document text thoroughly. Extract all recipient names (e.g. 'SHASHVAT', 'awarded to'), scores, grades, roll numbers, dates, institutions, and tables. Answer the user's specific questions factually and directly based on the document.\n"
            "   - In 'key_updates', list 2-5 concise bullet points of actual events or message summaries from the evidence.\n"
            "   - In 'pending_actions', list real action items requiring attention. If none (e.g. celebratory or informational emails), leave as [].\n"
            "4. Return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            "  \"answer_markdown\": \"Full, executive-level response in clean Markdown with ### Headings, **bold labels**, and • bullets. Do NOT output pipe tables.\",\n"
            "  \"key_updates\": [\"update 1\", \"update 2\"],\n"
            "  \"pending_actions\": [\"action 1\", \"action 2\"],\n"
            "  \"suggested_followups\": [\"followup 1\", \"followup 2\"]\n"
            "}"
        )

        ai_messages = [{"role": "system", "content": system_prompt}]

        # Append prior conversation history
        for m in prior_messages[-4:]:
            if (has_email_intent and (is_singular_latest or search_q == "")) and m.get("role") == "assistant" and any(c.get("type") == "email" for c in m.get("rich_cards", [])):
                continue
            ai_messages.append({"role": m["role"], "content": m["content"]})

        # Append current user question with evidence
        user_prompt_with_evidence = clean_text
        if retrieved_evidence:
            evidence_block = "\n\n---\n### RETRIEVED SOURCE EVIDENCE:\n" + "\n\n".join(retrieved_evidence) + "\n---"
            user_prompt_with_evidence += evidence_block

        ai_messages.append({"role": "user", "content": user_prompt_with_evidence})

        # Dynamic RAG Synthesis
        synth_res = call_groq_rag_synthesis(ai_messages)
        assistant_reply = synth_res.get("answer_markdown", "")
        extracted_updates = synth_res.get("key_updates", [])
        extracted_actions = synth_res.get("pending_actions", [])
        suggested_followups = synth_res.get("suggested_followups", [])

        # Only display summary block if real evidence exists and has extracted updates or actions
        if rich_cards and (extracted_updates or extracted_actions):
            summary_block = {
                "key_updates": extracted_updates,
                "pending_actions": extracted_actions,
                "source_summary": f"Source: {len(rich_cards)} verified item(s) • Live Workspace",
            }

    # 6. Save assistant message to SQLite
    assistant_msg = db.add_message(
        session_id=session_id,
        role="assistant",
        content=assistant_reply,
        rich_cards=rich_cards,
        sources_accessed=sources_accessed,
        summary_block=summary_block,
        suggested_followups=suggested_followups,
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
