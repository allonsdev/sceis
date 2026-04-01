import re
import json
import logging
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Optional, Tuple

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# GMAIL READER
# ─────────────────────────────────────────────
class GmailReader:
    """
    Reads emails from Gmail using IMAP with App Password auth.
    Configured via settings:
        GMAIL_USER      = "you@gmail.com"
        GMAIL_APP_PASS  = "xxxx xxxx xxxx xxxx"
    """

    IMAP_HOST = "imap.gmail.com"
    IMAP_PORT = 993

    def __init__(self):
        self.user = getattr(settings, "GMAIL_USER", "")
        self.password = getattr(settings, "GMAIL_APP_PASS", "")

    def fetch_unread_emails(self, max_results: int = 50) -> list[dict]:
        import imaplib
        import email as emaillib

        emails = []
        try:
            mail = imaplib.IMAP4_SSL(self.IMAP_HOST, self.IMAP_PORT)
            mail.login(self.user, self.password)
            mail.select("inbox")

            status, data = mail.search(None, "UNSEEN")
            if status != "OK":
                return emails

            uids = data[0].split()[-max_results:]

            for uid in uids:
                status, msg_data = mail.fetch(uid, "(RFC822)")
                if status != "OK":
                    continue

                raw = msg_data[0][1]
                msg = emaillib.message_from_bytes(raw)

                body = self._extract_body(msg)
                received_str = msg.get("Date", "")
                received_at = self._parse_date(received_str)

                emails.append({
                    "gmail_id": uid.decode(),
                    "sender": msg.get("From", ""),
                    "subject": msg.get("Subject", ""),
                    "body": body,
                    "received_at": received_at,
                })

            mail.logout()

        except Exception as exc:
            logger.error(f"[GmailReader] Error fetching emails: {exc}")

        return emails

    @staticmethod
    def _extract_body(msg) -> str:
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode("utf-8", errors="replace")
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="replace")
        return body.strip()

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            return timezone.now()


# ─────────────────────────────────────────────
# SENDER RESOLUTION HELPERS
# ─────────────────────────────────────────────

# Common role/department prefixes that are NOT org names
_ROLE_PREFIX_RE = re.compile(
    r"^(procurement\s+office|finance\s+dept(\.)?|hr\s+department|accounts?\s*(dept|office|payable|receivable)?|"
    r"admin(istration)?|secretary|director|manager|ceo|cfo|cto|it\s+dept(\.)?|"
    r"registrar('?s)?\s*(office)?|bursar('?s)?\s*(office)?|"
    r"principal('?s)?\s*(office)?|dean('?s)?\s*(office)?)\s*[,\-]?\s*",
    re.IGNORECASE,
)

# Words that add noise but carry no identity signal
_STOP_WORDS = {
    "of", "the", "and", "for", "a", "an", "in", "at", "by", "to",
    "ltd", "limited", "pvt", "inc", "co", "corp", "corporation",
    "group", "holdings", "pty", "llc", "plc",
}


def _extract_org_name_from_sender(sender_str: str) -> Optional[str]:
    """
    Pull the likely organisation name out of a raw sender string.

    Examples handled:
      "Procurement Office University of Zimbabwe <proc@uz.ac.zw>"  → "University of Zimbabwe"
      "John Doe - Acme Corp <john@acme.com>"                        → "Acme Corp"
      "Finance Dept, Harare City Council <fin@hcc.co.zw>"           → "Harare City Council"
      "admin@example.com"                                            → None
    """
    # Remove the <email@address> part
    display_name = re.sub(r"<[^>]+>", "", sender_str).strip().strip('"').strip("'")

    if not display_name or "@" in display_name:
        # Nothing useful left — it was a bare email address
        return None

    # Strip "Name - " or "Name, " separators (keep the org part after separator)
    if re.search(r"\s[-,]\s", display_name):
        # Take the last segment after the separator as the org name
        parts = re.split(r"\s[-,]\s", display_name)
        display_name = parts[-1].strip()

    # Strip common role/dept prefixes
    cleaned = _ROLE_PREFIX_RE.sub("", display_name).strip()

    return cleaned if cleaned else display_name


def _similarity(a: str, b: str) -> float:
    """
    Combined similarity score using:
      - SequenceMatcher (character-level, 40%)
      - Token overlap    (word-level,      60%)

    Stop words are excluded from token comparison so
    "University of Zimbabwe" matches "Zimbabwe University" well.
    """
    a, b = a.lower().strip(), b.lower().strip()

    def tokens(s: str) -> set:
        return {w for w in re.findall(r"\w+", s) if w not in _STOP_WORDS}

    seq_score = SequenceMatcher(None, a, b).ratio()

    a_tok, b_tok = tokens(a), tokens(b)
    if a_tok and b_tok:
        overlap = len(a_tok & b_tok) / max(len(a_tok), len(b_tok))
    else:
        overlap = 0.0

    return round(0.4 * seq_score + 0.6 * overlap, 4)


def _fuzzy_match_organization(
    candidate_name: str,
    OrgModel,
    threshold: float = 0.45,
) -> Optional[object]:
    """
    Scan all ClientOrganization rows and return the best name/legal_name match
    above `threshold`, or None.

    Threshold guide
    ───────────────
    0.45  loose  — catches "Univ of Zimbabwe" → "University of Zimbabwe"
    0.60  strict — only very close matches; fewer false positives
    """
    if not candidate_name:
        return None

    best_org = None
    best_score = 0.0

    # Only pull the columns we need — avoids loading large text fields
    for org in OrgModel.objects.only("id", "name", "legal_name"):
        score = max(
            _similarity(candidate_name, org.name),
            _similarity(candidate_name, org.legal_name) if org.legal_name else 0.0,
        )
        if score > best_score:
            best_score = score
            best_org = org

    if best_org and best_score >= threshold:
        logger.info(
            f"[FuzzyMatch] '{candidate_name}' → '{best_org.name}' "
            f"(score={best_score:.2f}, threshold={threshold})"
        )
        return best_org

    logger.info(
        f"[FuzzyMatch] No match for '{candidate_name}' "
        f"(best={best_score:.2f}, threshold={threshold})"
    )
    return None


# ─────────────────────────────────────────────
# AI EMAIL ANALYSER  (OpenRouter)
# ─────────────────────────────────────────────

from openai import OpenAI


class EmailAIAnalyzer:
    """
    Sends email content to OpenRouter and returns structured JSON analysis.
    Falls back to keyword heuristics when the API key is absent or the call fails.
    """

    SYSTEM_PROMPT = """
You are an intelligent CRM email analyst. Analyze client emails and return ONLY valid JSON (no markdown, no explanation).

Return this exact JSON structure:
{
  "intent": "complaint|inquiry|renewal|churn_risk|positive|support|competitor_mention|other",
  "sentiment_score": <float -1.0 to 1.0>,
  "churn_risk": <float 0.0 to 1.0>,
  "churn_reason": "<brief reason if churn_risk > 0.4, else empty>",
  "urgency": "low|medium|high",
  "create_task": true|false,
  "task_title": "<action title if create_task>",
  "task_description": "<detail>",
  "task_due_days": <int, days from now>,
  "task_priority": "low|medium|high",
  "competitor_mentioned": "<name or empty>",
  "suggested_reply_tone": "empathetic|professional|urgent|celebratory",
  "summary": "<1-2 sentence summary of the email>",
  "key_topics": ["topic1", "topic2"]
}
"""

    def __init__(self):
        self.api_key = getattr(settings, "OPENROUTER_API_KEY", "")
        self.model = getattr(settings, "OPENROUTER_MODEL", "openai/gpt-4o")

    def analyze(self, subject: str, body: str, sender: str) -> Optional[dict]:
        if not self.api_key:
            logger.warning("[EmailAI] OPENROUTER_API_KEY not set — using fallback analysis.")
            return self._fallback_analysis(subject, body)

        user_content = (
            f"Sender: {sender}\n"
            f"Subject: {subject}\n\n"
            f"Email Body:\n{body[:3000]}"
        )

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )

        try:
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user",   "content": user_content},
                ],
                temperature=0.2,
                max_tokens=500,
            )
            content = completion.choices[0].message.content
            # Strip markdown fences if the model wrapped the JSON
            content = re.sub(r"```json|```", "", content).strip()
            return json.loads(content)

        except Exception as exc:
            logger.error(f"[EmailAI] Analysis failed: {exc}")
            return self._fallback_analysis(subject, body)

    @staticmethod
    def _fallback_analysis(subject: str, body: str) -> dict:
        text = (subject + " " + body).lower()
        churn_keywords = [
            "cancel", "cancellation", "leaving", "competitor",
            "unhappy", "disappointed", "switch", "alternative provider",
            "no choice", "move to",
        ]
        churn_risk = 0.75 if any(k in text for k in churn_keywords) else 0.1
        sentiment  = -0.6 if churn_risk > 0.4 else 0.3

        return {
            "intent":               "churn_risk" if churn_risk > 0.4 else "inquiry",
            "sentiment_score":      sentiment,
            "churn_risk":           churn_risk,
            "churn_reason":         "Keyword-based churn signal detected" if churn_risk > 0.4 else "",
            "urgency":              "high" if churn_risk > 0.5 else "medium",
            "create_task":          True,
            "task_title":           f"Follow up: {subject[:80]}",
            "task_description":     body[:300],
            "task_due_days":        1 if churn_risk > 0.5 else 3,
            "task_priority":        "high" if churn_risk > 0.5 else "medium",
            "competitor_mentioned": "",
            "suggested_reply_tone": "empathetic" if churn_risk > 0.4 else "professional",
            "summary":              f"Email from client regarding: {subject}",
            "key_topics":           [],
        }


# ─────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────

class EmailOrchestrator:
    """
    Main entry point. Call .run() from a management command or Celery task.
    """

    def __init__(self):
        self.reader   = GmailReader()
        self.analyzer = EmailAIAnalyzer()

    # ── public entry point ────────────────────

    def run(self) -> dict:
        from django.contrib.auth import get_user_model
        from app.models import (
            EmailMessage, ClientOrganization, ClientContact,
            ChurnAlert, Task, Competitor,
        )

        User       = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first()

        summary = {
            "emails_processed":    0,
            "tasks_created":       0,
            "churn_alerts_created": 0,
            "errors":              0,
        }

        raw_emails = self.reader.fetch_unread_emails(max_results=50)
        logger.info(f"[Orchestrator] Fetched {len(raw_emails)} unread emails.")

        for raw in raw_emails:
            try:
                # ── Skip duplicates ───────────────────────
                if EmailMessage.objects.filter(gmail_id=raw["gmail_id"]).exists():
                    continue

                # ── AI analysis ───────────────────────────
                analysis = self.analyzer.analyze(
                    subject=raw["subject"],
                    body=raw["body"],
                    sender=raw["sender"],
                )

                # ── Resolve sender → org / contact ────────
                org, contact = self._resolve_sender(
                    raw["sender"], ClientOrganization, ClientContact
                )

                # ── Persist email record ──────────────────
                EmailMessage.objects.create(
                    gmail_id=raw["gmail_id"],
                    sender=raw["sender"],
                    subject=raw["subject"],
                    body=raw["body"],
                    received_at=raw["received_at"],
                    organization=org,
                    contact=contact,
                    sentiment_score=analysis.get("sentiment_score"),
                    intent=analysis.get("intent", ""),
                    processed=True,
                )

                # ── Create Task ───────────────────────────
                if analysis.get("create_task"):
                    due = timezone.now().date() + timedelta(
                        days=int(analysis.get("task_due_days", 3))
                    )
                    # Prefer org's account manager, fall back to any superuser
                    assigned_to = (
                        org.account_manager
                        if org and org.account_manager
                        else admin_user
                    )
                    Task.objects.create(
                        title=analysis.get(
                            "task_title",
                            f"Email follow-up: {raw['subject'][:80]}"
                        ),
                        description=(
                            f"{analysis.get('task_description', '')}\n\n"
                            f"--- Original Email ---\n"
                            f"From: {raw['sender']}\n"
                            f"Subject: {raw['subject']}\n\n"
                            f"{raw['body'][:500]}"
                        ),
                        assigned_to=assigned_to,
                        related_organization=org,
                        due_date=due,
                        priority=analysis.get("task_priority", "medium"),
                        status="pending",
                    )
                    summary["tasks_created"] += 1

                # ── Create Churn Alert ────────────────────
                churn_risk = float(analysis.get("churn_risk", 0))
                if churn_risk >= 0.4:
                    # org may be None for unmatched senders — ensure your
                    # ChurnAlert.organization field has null=True, blank=True
                    ChurnAlert.objects.create(
                        organization=org,
                        risk_score=churn_risk,
                        trigger_reason=(
                            f"[Email Analysis] {analysis.get('churn_reason', '')}\n"
                            f"Subject: {raw['subject']}\n"
                            f"From: {raw['sender']}"
                        ),
                        recommended_action=self._recommended_action(analysis),
                    )
                    summary["churn_alerts_created"] += 1

                # ── Log Competitor Mention ────────────────
                competitor_name = analysis.get("competitor_mentioned", "").strip()
                if competitor_name:
                    Competitor.objects.get_or_create(
                        name=competitor_name,
                        defaults={"threat_level": 5.0},
                    )

                summary["emails_processed"] += 1

            except Exception as exc:
                logger.error(
                    f"[Orchestrator] Error processing email "
                    f"{raw.get('gmail_id')}: {exc}"
                )
                summary["errors"] += 1

        return summary

    # ── helpers ───────────────────────────────

    @staticmethod
    def _resolve_sender(
        sender_str: str,
        OrgModel,
        ContactModel,
    ) -> Tuple[Optional[object], Optional[object]]:
        
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]+", sender_str)
        if email_match:
            email_addr = email_match.group(0).lower()
            domain     = email_addr.split("@")[-1]

            # ── 1. Exact contact match ────────────
            contact = ContactModel.objects.filter(email__iexact=email_addr).first()
            if contact:
                logger.info(f"[Resolve] Exact contact match: {email_addr}")
                return contact.organization, contact

            # ── 2. Exact org primary_email match ──  ← NEW
            org = OrgModel.objects.filter(primary_email__iexact=email_addr).first()
            if org:
                logger.info(f"[Resolve] Exact primary_email match: {email_addr} → {org.name}")
                return org, None

            # ── 3. Domain match ───────────────────
            org = OrgModel.objects.filter(primary_email__icontains=domain).first()
            if org:
                logger.info(f"[Resolve] Domain match: {domain} → {org.name}")
                return org, None

        # ── 4. Fuzzy name match ───────────────
        candidate_name = _extract_org_name_from_sender(sender_str)
        if candidate_name:
            org = _fuzzy_match_organization(candidate_name, OrgModel, threshold=0.45)
            if org:
                return org, None

        # ── 5. No match ───────────────────────
        logger.info(f"[Resolve] No org/contact match for sender: {sender_str!r}")
        return None, None

    @staticmethod
    def _recommended_action(analysis: dict) -> str:
        urgency = analysis.get("urgency", "medium")
        tone    = analysis.get("suggested_reply_tone", "professional")
        topics  = ", ".join(analysis.get("key_topics", []))
        return (
            f"Urgency: {urgency.upper()}. "
            f"Respond with a {tone} tone. "
            f"Key topics to address: {topics or 'see email summary'}. "
            f"Summary: {analysis.get('summary', '')}"
        )