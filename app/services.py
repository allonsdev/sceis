# =====================================================
# 📦 IMPORTS
# =====================================================
from googleapiclient.discovery import build
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail

from app.models import (
    EmailMessage,
    CommunicationLog,
    Task,
    ChurnAlert,
    ClientOrganization,
    ClientContact
)

# =====================================================
# 🔌 INIT
# =====================================================
analyzer = SentimentIntensityAnalyzer()

# =====================================================
# 🔌 GMAIL CONNECTION
# =====================================================
def get_gmail_service(creds):
    return build("gmail", "v1", credentials=creds)


def clean_sender(sender):
    if "<" in sender:
        return sender.split("<")[-1].replace(">", "").strip()
    return sender.strip()


# =====================================================
# 📥 FETCH EMAILS
# =====================================================
def fetch_emails(creds):
    service = get_gmail_service(creds)

    results = service.users().messages().list(
        userId="me",
        maxResults=20
    ).execute()

    messages = results.get("messages", [])

    for msg in messages:
        msg_data = service.users().messages().get(
            userId="me",
            id=msg["id"]
        ).execute()

        headers = msg_data["payload"]["headers"]

        def get_header(name):
            return next((h["value"] for h in headers if h["name"] == name), "")

        subject = get_header("Subject")
        sender = clean_sender(get_header("From"))
        body = msg_data.get("snippet", "")

        contact = ClientContact.objects.filter(email__iexact=sender).first()
        organization = contact.organization if contact else None

        EmailMessage.objects.get_or_create(
            gmail_id=msg["id"],
            defaults={
                "subject": subject,
                "sender": sender,
                "body": body,
                "organization": organization,
                "contact": contact,
                "received_at": timezone.now()
            }
        )


# =====================================================
# 🧠 SENTIMENT (VADER)
# =====================================================
def analyze_sentiment(text):
    score = analyzer.polarity_scores(text)
    return score["compound"]  # -1 to +1


# =====================================================
# 🧠 INTENT DETECTION
# =====================================================
INTENT_KEYWORDS = {
    "complaint": [
        "issue", "problem", "not working", "error",
        "fail", "broken", "disappointed", "bad service"
    ],
    "urgent": [
        "urgent", "asap", "immediately", "right now"
    ],
    "follow_up": [
        "follow up", "any update", "still waiting", "checking in"
    ],
    "sales": [
        "quote", "pricing", "proposal", "cost", "demo"
    ],
    "positive": [
        "thank you", "thanks", "great", "appreciate", "happy"
    ]
}


def detect_intent(text):
    text = text.lower()
    sentiment = analyze_sentiment(text)

    scores = {intent: 0 for intent in INTENT_KEYWORDS}

    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[intent] += 1

    best_intent = max(scores, key=scores.get)

    # fallback using sentiment
    if scores[best_intent] == 0:
        if sentiment < -0.4:
            return "complaint"
        elif sentiment > 0.5:
            return "positive"
        return "general"

    return best_intent


# =====================================================
# 🎯 PRIORITY SCORING
# =====================================================
def get_priority(sentiment, intent):
    if intent == "urgent":
        return "high"

    if intent == "complaint" and sentiment < -0.4:
        return "high"

    if intent in ["follow_up", "sales"]:
        return "medium"

    if sentiment > 0.5:
        return "low"

    return "medium"


# =====================================================
# ⚙️ PROCESS EMAILS
# =====================================================
def process_emails():
    emails = EmailMessage.objects.filter(processed=False)

    for email in emails:
        sentiment = analyze_sentiment(email.body)
        intent = detect_intent(email.body)
        priority = get_priority(sentiment, intent)

        # update email
        email.sentiment_score = sentiment
        email.intent = intent
        email.processed = True
        email.save()

        # log communication
        CommunicationLog.objects.create(
            organization=email.organization,
            contact=email.contact,
            channel="email",
            subject=email.subject,
            interaction_summary=email.body[:200],
            sentiment_score=sentiment,
            response_received=True
        )

        # update last interaction
        if email.contact:
            email.contact.last_interaction_date = timezone.now()
            email.contact.save()

        # 🎯 CREATE TASK (SMART LOGIC)
        if priority == "high":
            create_task(email, priority)

        # optional: medium priority follow-ups
        elif priority == "medium" and intent == "follow_up":
            create_task(email, priority)


# =====================================================
# 📌 TASK CREATION
# =====================================================
def create_task(email, priority):
    if not email.organization:
        return

    task = Task.objects.create(
        title=f"{priority.upper()} Priority: Client {email.intent}",
        description=email.body,
        assigned_to=email.organization.account_manager,
        related_organization=email.organization,
        due_date=timezone.now().date() + timedelta(days=2),
        priority=priority
    )

    send_task_email(email.organization, task)


# =====================================================
# 📧 TASK EMAIL ALERT
# =====================================================
def send_task_email(organization, task):
    user = organization.account_manager

    if not user or not user.email:
        return

    send_mail(
        subject=f"New {task.priority.upper()} Priority Task",
        message=f"""
A new task has been created.

Organization: {organization.name}
Intent: {task.title}
Priority: {task.priority}

Please log in to the CRM to take action.
""",
        from_email="system@crm.com",
        recipient_list=[user.email],
    )


# =====================================================
# 🚨 CHURN ANALYSIS
# =====================================================
def run_churn_analysis():
    for org in ClientOrganization.objects.all():

        logs = CommunicationLog.objects.filter(organization=org)
        last_log = logs.order_by("-created_at").first()

        risk_score = 0

        # inactivity
        if not last_log or last_log.created_at < timezone.now() - timedelta(days=14):
            risk_score += 0.5

        # negative sentiment trend
        negative = logs.filter(sentiment_score__lt=-0.3).count()
        if negative >= 3:
            risk_score += 0.4

        # high-priority issues
        high_issues = logs.filter(sentiment_score__lt=-0.5).count()
        if high_issues >= 2:
            risk_score += 0.3

        if risk_score > 0:

            if not ChurnAlert.objects.filter(
                organization=org,
                resolved=False
            ).exists():

                alert = ChurnAlert.objects.create(
                    organization=org,
                    risk_score=risk_score,
                    trigger_reason="Low engagement or repeated negative sentiment"
                )

                send_churn_email(alert)


# =====================================================
# 📧 CHURN EMAIL
# =====================================================
def send_churn_email(alert):
    user = alert.organization.account_manager

    if not user or not user.email:
        return

    send_mail(
        subject=f"🚨 Churn Risk Alert: {alert.organization.name}",
        message=f"""
Risk Score: {alert.risk_score}

Reason:
{alert.trigger_reason}

Immediate attention is recommended.
""",
        from_email="system@crm.com",
        recipient_list=[user.email],
    )


# =====================================================
# 🚀 MASTER PIPELINE
# =====================================================
def run_pipeline(creds):
    fetch_emails(creds)
    process_emails()
    run_churn_analysis()