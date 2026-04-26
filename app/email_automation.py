import re
import json
import logging
import smtplib
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Tuple

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# ENQUIRY DETECTION
# ─────────────────────────────────────────────

ENQUIRY_KEYWORDS = [
    "enquir", "inquir",          # covers enquiry/enquiries/inquiry/inquiries
    "quote", "quotation",
    "pricing", "price list",
    "how much", "cost of",
    "available", "availability",
    "more information", "more info",
    "interested in", "looking for",
    "can you provide", "please send",
    "information on", "details on",
    "training options", "course",
    "brochure", "prospectus",
    "register", "registration",
    "sign up", "enrol", "enroll",
    "get started", "find out more",
]

ENQUIRIES_EMAIL = "mtbenquiries@gmail.com"


def _is_enquiry(subject: str, body: str) -> bool:
    """
    Return True if the email looks like a sales/training enquiry.
    Checks subject first (higher signal), then body (lower weight).
    """
    text_subject = subject.lower()
    text_body    = (body or "")[:1500].lower()   # cap to avoid scanning huge bodies

    # A keyword hit in the subject is a strong signal
    for kw in ENQUIRY_KEYWORDS:
        if kw in text_subject:
            return True

    # Two or more keyword hits in the body confirms it
    body_hits = sum(1 for kw in ENQUIRY_KEYWORDS if kw in text_body)
    return body_hits >= 2


# ─────────────────────────────────────────────
# ENQUIRY EMAIL FORWARDER
# ─────────────────────────────────────────────

class EnquiryForwarder:
    """
    Sends a nicely-formatted forward/notification email to the enquiries
    mailbox using the same Gmail SMTP credentials as the main account.

    Settings required (same as GmailReader):
        GMAIL_USER     = "you@gmail.com"
        GMAIL_APP_PASS = "xxxx xxxx xxxx xxxx"
    """

    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587

    def __init__(self):
        self.user     = getattr(settings, "GMAIL_USER", "")
        self.password = getattr(settings, "GMAIL_APP_PASS", "")

    def forward(
        self,
        original_sender: str,
        original_subject: str,
        original_body: str,
        received_at,
        ai_summary: str = "",
        task_title: str = "",
        org_name: str = "",
    ) -> bool:
        """
        Compose and send the enquiry notification. Returns True on success.
        """
        if not self.user or not self.password:
            logger.warning("[EnquiryForwarder] GMAIL credentials not configured — skipping forward.")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["From"]    = self.user
            msg["To"]      = ENQUIRIES_EMAIL
            msg["Subject"] = f"[ENQUIRY] {original_subject}"

            # ── Plain-text body ───────────────────────────────────────
            plain = (
                f"A new enquiry email has been received and assigned to you.\n\n"
                f"{'─' * 60}\n"
                f"From    : {original_sender}\n"
                f"Subject : {original_subject}\n"
                f"Received: {received_at}\n"
                f"Org     : {org_name or 'Unknown / unmatched'}\n"
                f"Task    : {task_title or 'N/A'}\n"
                f"{'─' * 60}\n\n"
                f"AI Summary:\n{ai_summary or 'Not available'}\n\n"
                f"{'─' * 60}\n"
                f"Original Message:\n\n"
                f"{original_body}\n"
            )

            # ── HTML body ─────────────────────────────────────────────
            html = f"""
<html>
<body style="font-family:Arial,sans-serif;font-size:14px;color:#1e293b;background:#f8fafc;padding:20px">
  <div style="max-width:640px;margin:auto;background:#fff;border-radius:10px;
              border:1px solid #e2e8f0;overflow:hidden">

    <!-- Header -->
    <div style="background:#2563EB;padding:18px 24px">
      <h2 style="margin:0;color:#fff;font-size:16px;letter-spacing:.5px">
        📬 New Enquiry Received
      </h2>
    </div>

    <!-- Meta -->
    <div style="padding:20px 24px;border-bottom:1px solid #e2e8f0;background:#f1f5f9">
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <tr>
          <td style="padding:4px 0;color:#64748b;width:100px">From</td>
          <td style="padding:4px 0;font-weight:600">{original_sender}</td>
        </tr>
        <tr>
          <td style="padding:4px 0;color:#64748b">Subject</td>
          <td style="padding:4px 0;font-weight:600">{original_subject}</td>
        </tr>
        <tr>
          <td style="padding:4px 0;color:#64748b">Received</td>
          <td style="padding:4px 0">{received_at}</td>
        </tr>
        <tr>
          <td style="padding:4px 0;color:#64748b">Organisation</td>
          <td style="padding:4px 0">{org_name or '<em style="color:#94a3b8">Unknown / unmatched</em>'}</td>
        </tr>
        <tr>
          <td style="padding:4px 0;color:#64748b">CRM Task</td>
          <td style="padding:4px 0">
            <span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;
                         border-radius:4px;font-size:12px;font-weight:600">
              {task_title or 'N/A'}
            </span>
          </td>
        </tr>
      </table>
    </div>

    <!-- AI Summary -->
    <div style="padding:20px 24px;border-bottom:1px solid #e2e8f0">
      <p style="margin:0 0 8px;font-size:12px;font-weight:700;color:#64748b;
                text-transform:uppercase;letter-spacing:.05em">AI Summary</p>
      <p style="margin:0;line-height:1.6;color:#334155">
        {ai_summary or '<em style="color:#94a3b8">Not available</em>'}
      </p>
    </div>

    <!-- Original message -->
    <div style="padding:20px 24px">
      <p style="margin:0 0 8px;font-size:12px;font-weight:700;color:#64748b;
                text-transform:uppercase;letter-spacing:.05em">Original Message</p>
      <div style="background:#f8fafc;border-left:3px solid #2563EB;
                  padding:12px 16px;border-radius:0 6px 6px 0;
                  font-size:13px;line-height:1.7;color:#475569;
                  white-space:pre-wrap">{original_body[:2000]}</div>
    </div>

    <!-- Footer -->
    <div style="padding:14px 24px;background:#f1f5f9;border-top:1px solid #e2e8f0;
                font-size:11px;color:#94a3b8;text-align:center">
      This message was automatically generated by the MTB CRM Enquiry Router.
    </div>
  </div>
</body>
</html>
"""

            msg.attach(MIMEText(plain, "plain"))
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, ENQUIRIES_EMAIL, msg.as_string())

            logger.info(
                f"[EnquiryForwarder] Forwarded enquiry '{original_subject}' "
                f"to {ENQUIRIES_EMAIL}"
            )
            return True

        except Exception as exc:
            logger.error(f"[EnquiryForwarder] Failed to send: {exc}")
            return False


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
        self.user     = getattr(settings, "GMAIL_USER", "")
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

                body        = self._extract_body(msg)
                received_at = self._parse_date(msg.get("Date", ""))

                emails.append({
                    "gmail_id":   uid.decode(),
                    "sender":     msg.get("From", ""),
                    "subject":    msg.get("Subject", ""),
                    "body":       body,
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

_ROLE_PREFIX_RE = re.compile(
    r"^(procurement\s+office|finance\s+dept(\.)?|hr\s+department|accounts?\s*(dept|office|payable|receivable)?|"
    r"admin(istration)?|secretary|director|manager|ceo|cfo|cto|it\s+dept(\.)?|"
    r"registrar('?s)?\s*(office)?|bursar('?s)?\s*(office)?|"
    r"principal('?s)?\s*(office)?|dean('?s)?\s*(office)?)\s*[,\-]?\s*",
    re.IGNORECASE,
)

_STOP_WORDS = {
    "of", "the", "and", "for", "a", "an", "in", "at", "by", "to",
    "ltd", "limited", "pvt", "inc", "co", "corp", "corporation",
    "group", "holdings", "pty", "llc", "plc",
}


def _extract_org_name_from_sender(sender_str: str) -> Optional[str]:
    display_name = re.sub(r"<[^>]+>", "", sender_str).strip().strip('"').strip("'")

    if not display_name or "@" in display_name:
        return None

    if re.search(r"\s[-,]\s", display_name):
        parts = re.split(r"\s[-,]\s", display_name)
        display_name = parts[-1].strip()

    cleaned = _ROLE_PREFIX_RE.sub("", display_name).strip()
    return cleaned if cleaned else display_name


def _similarity(a: str, b: str) -> float:
    a, b = a.lower().strip(), b.lower().strip()

    def tokens(s: str) -> set:
        return {w for w in re.findall(r"\w+", s) if w not in _STOP_WORDS}

    seq_score = SequenceMatcher(None, a, b).ratio()
    a_tok, b_tok = tokens(a), tokens(b)
    overlap = len(a_tok & b_tok) / max(len(a_tok), len(b_tok)) if (a_tok and b_tok) else 0.0

    return round(0.4 * seq_score + 0.6 * overlap, 4)


def _fuzzy_match_organization(
    candidate_name: str,
    OrgModel,
    threshold: float = 0.45,
) -> Optional[object]:
    if not candidate_name:
        return None

    best_org, best_score = None, 0.0

    for org in OrgModel.objects.only("id", "name", "legal_name"):
        score = max(
            _similarity(candidate_name, org.name),
            _similarity(candidate_name, org.legal_name) if org.legal_name else 0.0,
        )
        if score > best_score:
            best_score = score
            best_org   = org

    if best_org and best_score >= threshold:
        logger.info(f"[FuzzyMatch] '{candidate_name}' → '{best_org.name}' (score={best_score:.2f})")
        return best_org

    logger.info(f"[FuzzyMatch] No match for '{candidate_name}' (best={best_score:.2f})")
    return None


# ─────────────────────────────────────────────
# AI EMAIL ANALYSER  (OpenRouter)
# ─────────────────────────────────────────────

from openai import OpenAI


class EmailAIAnalyzer:
    SYSTEM_PROMPT = """
You are an intelligent CRM email analyst. Analyze client emails and return ONLY valid JSON (no markdown, no explanation).

Return this exact JSON structure:
{
  "intent": "complaint|inquiry|enquiry|renewal|churn_risk|positive|support|competitor_mention|other",
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
  "key_topics": ["topic1", "topic2"],
  "is_enquiry": true|false
}
"""

    def __init__(self):
        self.api_key = getattr(settings, "OPENROUTER_API_KEY", "")
        self.model   = getattr(settings, "OPENROUTER_MODEL", "openai/gpt-4o")

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
            content = re.sub(r"```json|```", "", content).strip()
            result  = json.loads(content)

            # Ensure is_enquiry is always present (older model responses may omit it)
            if "is_enquiry" not in result:
                result["is_enquiry"] = _is_enquiry(subject, body)

            return result

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
        is_enq     = _is_enquiry(subject, body)

        return {
            "intent":               "enquiry" if is_enq else ("churn_risk" if churn_risk > 0.4 else "inquiry"),
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
            "is_enquiry":           is_enq,
        }


# ─────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────

class EmailOrchestrator:
    """
    Main entry point. Call .run() from a management command or Celery task.

    Enquiry routing
    ───────────────
    If an email is detected as an enquiry (keyword scan + AI flag), it is:
      1. Assigned to the User whose email is ENQUIRIES_EMAIL.
      2. Forwarded to ENQUIRIES_EMAIL via SMTP with a formatted HTML notification.
    """

    def __init__(self):
        self.reader    = GmailReader()
        self.analyzer  = EmailAIAnalyzer()
        self.forwarder = EnquiryForwarder()

    # ── public entry point ────────────────────

    def run(self) -> dict:
        from django.contrib.auth import get_user_model
        from app.models import (
            EmailMessageContacts, ClientOrganization, ClientContact,
            ChurnAlert, Task, Competitor,
        )

        User       = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first()

        # ── Resolve the enquiries user once ──────────────────────────────
        enquiries_user = User.objects.filter(
            email__iexact=ENQUIRIES_EMAIL
        ).first()

        if not enquiries_user:
            logger.warning(
                f"[Orchestrator] No User found with email '{ENQUIRIES_EMAIL}'. "
                f"Enquiry tasks will fall back to account manager / admin."
            )

        summary = {
            "emails_processed":     0,
            "tasks_created":        0,
            "churn_alerts_created": 0,
            "enquiries_routed":     0,
            "errors":               0,
        }

        raw_emails = self.reader.fetch_unread_emails(max_results=50)
        logger.info(f"[Orchestrator] Fetched {len(raw_emails)} unread emails.")

        for raw in raw_emails:
            try:
                # ── Skip duplicates ───────────────────────────────────────
                if EmailMessageContacts.objects.filter(gmail_id=raw["gmail_id"]).exists():
                    continue

                # ── AI analysis ───────────────────────────────────────────
                analysis = self.analyzer.analyze(
                    subject=raw["subject"],
                    body=raw["body"],
                    sender=raw["sender"],
                )

                # ── Enquiry detection (keyword OR AI flag) ────────────────
                email_is_enquiry = (
                    bool(analysis.get("is_enquiry"))
                    or _is_enquiry(raw["subject"], raw["body"])
                )

                # ── Resolve sender → org / contact ────────────────────────
                org, contact = self._resolve_sender(
                    raw["sender"], ClientOrganization, ClientContact
                )

                # ── Persist email record ──────────────────────────────────
                EmailMessageContacts.objects.create(
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

                # ── Create Task ───────────────────────────────────────────
                task_obj = None
                if analysis.get("create_task"):
                    due = timezone.now().date() + timedelta(
                        days=int(analysis.get("task_due_days", 3))
                    )

                    # Enquiry tasks → enquiries_user; else → account manager / admin
                    if email_is_enquiry and enquiries_user:
                        assigned_to = enquiries_user
                    else:
                        assigned_to = (
                            org.account_manager
                            if org and org.account_manager
                            else admin_user
                        )

                    task_title = analysis.get(
                        "task_title",
                        f"Email follow-up: {raw['subject'][:80]}"
                    )

                    # Prefix enquiry tasks for easy identification
                    if email_is_enquiry and not task_title.lower().startswith("[enquiry]"):
                        task_title = f"[ENQUIRY] {task_title}"

                    task_obj = Task.objects.create(
                        title=task_title,
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

                # ── Forward enquiry email ─────────────────────────────────
                if email_is_enquiry:
                    sent = self.forwarder.forward(
                        original_sender=raw["sender"],
                        original_subject=raw["subject"],
                        original_body=raw["body"],
                        received_at=raw["received_at"],
                        ai_summary=analysis.get("summary", ""),
                        task_title=task_obj.title if task_obj else "",
                        org_name=org.name if org else "",
                    )
                    if sent:
                        summary["enquiries_routed"] += 1
                        logger.info(
                            f"[Orchestrator] Enquiry routed → {ENQUIRIES_EMAIL} | "
                            f"Subject: {raw['subject']!r}"
                        )

                # ── Create Churn Alert ────────────────────────────────────
                churn_risk = float(analysis.get("churn_risk", 0))
                if churn_risk >= 0.4:
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

                # ── Log Competitor Mention ────────────────────────────────
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

            # 1. Exact contact match
            contact = ContactModel.objects.filter(email__iexact=email_addr).first()
            if contact:
                logger.info(f"[Resolve] Exact contact match: {email_addr}")
                return contact.organization, contact

            # 2. Exact org primary_email match
            org = OrgModel.objects.filter(primary_email__iexact=email_addr).first()
            if org:
                logger.info(f"[Resolve] Exact primary_email match: {email_addr} → {org.name}")
                return org, None

            # 3. Domain match
            org = OrgModel.objects.filter(primary_email__icontains=domain).first()
            if org:
                logger.info(f"[Resolve] Domain match: {domain} → {org.name}")
                return org, None

        # 4. Fuzzy name match
        candidate_name = _extract_org_name_from_sender(sender_str)
        if candidate_name:
            org = _fuzzy_match_organization(candidate_name, OrgModel, threshold=0.45)
            if org:
                return org, None

        # 5. No match
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