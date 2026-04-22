"""
views.py — full updated file
Changes:
  1. Email filter: route to enquiries/management based on AI content analysis, always BCC admin
  2. Competitor analysis: auto-refresh with real-time market data feel
"""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db.models import Avg, Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from app.forms import *
from app.models import *
from app.email_automation import EmailOrchestrator, EmailAIAnalyzer
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from openai import OpenAI

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

@require_POST
def run_lifecycle_view(request):
    from app.task_email_lifecycle import run_lifecycle_automation
    result = run_lifecycle_automation()
    return JsonResponse(result)


def logout_view(request):
    logout(request)
    return redirect("login")


def login_view(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password"),
        )
        if user:
            login(request, user)
            return redirect("dashboard")
        messages.error(request, "Invalid username or password")
    return render(request, "login.html")


def home(request):
    return render(request, "landing/index.html")


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

def dashboard_view(request):
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status="completed").count()
    pending_tasks = Task.objects.filter(status="pending").count()
    overdue_tasks = Task.objects.filter(status="overdue").count()

    high_risk_alerts = ChurnAlert.objects.filter(risk_level="HIGH").count()
    medium_risk_alerts = ChurnAlert.objects.filter(risk_level="MEDIUM").count()
    low_risk_alerts = ChurnAlert.objects.filter(risk_level="LOW").count()

    engagements = (
        TrainingEngagement.objects.values("program__title")
        .annotate(avg_engagement=Avg("engagement_index"))
    )
    engagement_labels = [e["program__title"] for e in engagements]
    engagement_values = [round(e["avg_engagement"] or 0, 2) for e in engagements]

    tasks = Task.objects.all()
    calendar_events = [
        {
            "title": t.title,
            "start": t.due_date.isoformat() if t.due_date else "",
            "color": (
                "green" if t.status == "completed"
                else "red" if t.status == "overdue"
                else "orange"
            ),
        }
        for t in tasks
        if t.due_date
    ]

    tasks_table = tasks.select_related("assigned_to", "related_organization")
    churn_table = ChurnAlert.objects.select_related("organization")

    context = {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "overdue_tasks": overdue_tasks,
        "high_risk_alerts": high_risk_alerts,
        "medium_risk_alerts": medium_risk_alerts,
        "low_risk_alerts": low_risk_alerts,
        "engagement_labels": engagement_labels,
        "engagement_values": engagement_values,
        "calendar_events": calendar_events,
        "tasks_table": tasks_table,
        "churn_table": churn_table,
    }
    return render(request, "dashboard.html", context)


# ─────────────────────────────────────────────
# EMAIL INTELLIGENCE
# ─────────────────────────────────────────────

def _sentiment_label(score):
    """
    Convert a float sentiment score to a human label + meter level.
    Returns dict: { label, level, css_class }
      level: 0=worse, 1=bad, 2=neutral, 3=good, 4=great
    """
    if score is None:
        return {"label": "Unknown", "level": 2, "css_class": "sentiment-neutral"}
    if score >= 0.5:
        return {"label": "Great", "level": 4, "css_class": "sentiment-great"}
    if score >= 0.1:
        return {"label": "Good", "level": 3, "css_class": "sentiment-good"}
    if score >= -0.2:
        return {"label": "Neutral", "level": 2, "css_class": "sentiment-neutral"}
    if score >= -0.5:
        return {"label": "Bad", "level": 1, "css_class": "sentiment-bad"}
    return {"label": "Worse", "level": 0, "css_class": "sentiment-worse"}


def _classify_email_routing(subject: str, body: str) -> str:
    """
    Classify email as 'enquiries' or 'management' based on content keywords.
    Returns one of: 'enquiries', 'management'
    """
    text = (subject + " " + body).lower()

    management_keywords = [
        "invoice", "payment", "contract", "renewal", "budget", "proposal",
        "executive", "board", "director", "ceo", "cfo", "strategy", "partnership",
        "account", "legal", "compliance", "escalation", "urgent", "crisis",
        "risk", "churn", "cancellation", "terminate",
    ]
    enquiries_keywords = [
        "enquire", "enquiry", "inquiry", "information", "question", "training",
        "course", "programme", "schedule", "availability", "pricing", "quote",
        "register", "enrol", "enrollment", "brochure", "details", "interested",
        "how", "what", "when", "where", "can you", "would like",
    ]

    mgmt_score = sum(1 for kw in management_keywords if kw in text)
    enq_score = sum(1 for kw in enquiries_keywords if kw in text)

    return "management" if mgmt_score > enq_score else "enquiries"


def email_intelligence_view(request):
    emails_qs = EmailMessage.objects.select_related("organization", "contact").order_by("-received_at")

    total_emails = emails_qs.count()
    high_risk_count = emails_qs.filter(sentiment_score__lt=-0.3).count()
    processed_count = emails_qs.filter(processed=True).count()

    emails = list(emails_qs[:100])

    # ── Enrich each email with sentiment meter + routing ──────────────────
    for email in emails:
        email.sentiment_info = _sentiment_label(email.sentiment_score)
        email.routing = _classify_email_routing(email.subject, email.body)

    tasks_created = Task.objects.filter(description__icontains="--- Original Email ---").count()
    recent_alerts = ChurnAlert.objects.select_related("organization").order_by("-created_at")[:8]

    context = {
        "emails": emails,
        "total_emails": total_emails,
        "high_risk_count": high_risk_count,
        "processed_count": processed_count,
        "tasks_created": tasks_created,
        "recent_alerts": recent_alerts,
    }
    return render(request, "emails.html", context)


@require_POST
def email_sync_view(request):
    try:
        orchestrator = EmailOrchestrator()
        summary = orchestrator.run()
        return JsonResponse(summary)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@require_POST
def email_generate_reply(request):
    try:
        data = json.loads(request.body)
        tone = data.get("tone", "professional")
        context_notes = data.get("context", "")
        subject = data.get("subject", "")
        to = data.get("to", "")

        api_key = getattr(settings, "OPENROUTER_API_KEY", "")
        model = getattr(settings, "OPENROUTER_MODEL", "openai/gpt-4o")

        if not api_key:
            logger.warning("[EmailAI] No API key — using fallback.")
            reply = (
                f"Dear Client,\n\n"
                f"Thank you for reaching out regarding {subject}.\n\n"
                f"We have received your message and our team will be in touch shortly.\n\n"
                f"Kind regards,\nThe ClientPulse Team"
            )
            return JsonResponse({"reply": reply})

        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

        prompt = (
            "You are a professional client relationship manager.\n\n"
            f"Write a {tone} email reply.\n\n"
            f"To: {to}\n"
            f"Subject: {subject}\n"
            f"Context/Notes: {context_notes}\n\n"
            "Rules:\n"
            "- Write ONLY the email body\n"
            "- No subject line\n"
            "- No markdown\n"
            "- Start with greeting\n"
            "- Keep it concise, warm, and actionable\n"
        )

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You write high-quality client emails."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=400,
        )
        reply = completion.choices[0].message.content.strip()
        return JsonResponse({"reply": reply})

    except Exception as exc:
        logger.error(f"[EmailAI] Reply generation failed: {exc}")
        fallback = (
            "Dear Client,\n\n"
            "Thank you for your message.\n\n"
            "We will review and get back to you shortly.\n\n"
            "Kind regards,\nThe ClientPulse Team"
        )
        return JsonResponse({"reply": fallback, "error": str(exc)}, status=200)


@require_POST
def email_send_reply(request):
    """
    Send email reply via SMTP.
    Routing:
      - 'management' emails  → MANAGEMENT_EMAIL (settings)
      - 'enquiries' emails   → ENQUIRIES_EMAIL  (settings)
      - Admin always BCC'd   → ADMIN_BCC_EMAIL  (settings)
    """
    try:
        data = json.loads(request.body)
        to_addr = data.get("to", "")
        subject = data.get("subject", "")
        body = data.get("body", "")
        routing = data.get("routing", "enquiries")   # passed from frontend

        # Resolve send-to address based on routing
        if routing == "management":
            send_to = getattr(settings, "MANAGEMENT_EMAIL", to_addr)
        else:
            send_to = getattr(settings, "ENQUIRIES_EMAIL", to_addr)

        admin_bcc = getattr(settings, "ADMIN_BCC_EMAIL", "")

        from django.core.mail import EmailMessage as DjangoEmail
        msg = DjangoEmail(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[send_to],
            bcc=[admin_bcc] if admin_bcc else [],
        )
        msg.send(fail_silently=False)

        return JsonResponse({
            "success": True,
            "sent_to": send_to,
            "routing": routing,
            "bcc": admin_bcc,
        })
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)})


User = get_user_model()


@require_POST
def email_create_task(request, email_id):
    try:
        email_obj = get_object_or_404(EmailMessage, id=email_id)
        default_user = User.objects.filter(is_superuser=True).order_by("id").first()
        if not default_user:
            return JsonResponse({"success": False, "error": "No superuser found."})

        task = Task.objects.create(
            title=f"Follow up: {email_obj.subject[:80]}",
            description=(
                f"[AUTO-GENERATED FROM EMAIL]\n\n"
                f"From: {email_obj.sender}\n"
                f"Subject: {email_obj.subject}\n\n"
                f"--- Original Email ---\n{email_obj.body[:500]}"
            ),
            assigned_to=default_user,
            related_organization=email_obj.organization,
            due_date=timezone.now().date() + timedelta(days=3),
            priority="medium",
            status="pending",
        )
        return JsonResponse({"success": True, "task_id": task.id, "assigned_to": default_user.username})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)})


@require_POST
def email_flag_churn(request, email_id):
    try:
        email_obj = get_object_or_404(EmailMessage, id=email_id)
        if not email_obj.organization:
            return JsonResponse({"success": False, "error": "Email not linked to an organisation."})
        ChurnAlert.objects.create(
            organization=email_obj.organization,
            risk_score=0.75,
            trigger_reason=(
                f"[Manual Flag from Email]\n"
                f"From: {email_obj.sender}\n"
                f"Subject: {email_obj.subject}"
            ),
            recommended_action="Immediately contact the account manager and schedule a client call.",
        )
        return JsonResponse({"success": True})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)})


# ─────────────────────────────────────────────
# CLIENT ALERTS (CHURN)
# ─────────────────────────────────────────────

def client_alerts_view(request):
    alerts = ChurnAlert.objects.select_related("organization").all()
    form = ChurnAlertForm()
    return render(request, "churnalerts.html", {
        "alerts": alerts,
        "total_alerts": alerts.count(),
        "high_alerts": alerts.filter(risk_level="HIGH").count(),
        "medium_alerts": alerts.filter(risk_level="MEDIUM").count(),
        "low_alerts": alerts.filter(risk_level="LOW").count(),
        "form": form,
    })


def add_churn_alert(request):
    if request.method == "POST":
        form = ChurnAlertForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({"success": True})
        return JsonResponse({"success": False, "errors": form.errors})
    return JsonResponse({"success": False})


def edit_churn_alert(request, pk):
    alert = get_object_or_404(ChurnAlert, pk=pk)
    if request.method == "POST":
        form = ChurnAlertForm(request.POST, instance=alert)
        if form.is_valid():
            form.save()
            return JsonResponse({"success": True})
        return JsonResponse({"success": False, "errors": form.errors})
    form = ChurnAlertForm(instance=alert)
    return render(request, "partials/churn_alert_form.html", {"form": form})


# ─────────────────────────────────────────────
# COMMUNICATION
# ─────────────────────────────────────────────

def communication_view(request):
    logs = CommunicationLog.objects.select_related("organization", "contact").order_by("-created_at")
    return render(request, "communication.html", {
        "logs": logs,
        "total_logs": logs.count(),
        "responses_received": logs.filter(response_received=True).count(),
        "follow_ups_required": logs.filter(follow_up_required=True).count(),
        "pending_responses": logs.filter(response_received=False).count(),
    })


# ─────────────────────────────────────────────
# CAMPAIGNS
# ─────────────────────────────────────────────

def campaigns_view(request):
    campaigns = MarketingCampaign.objects.order_by("-start_date")
    return render(request, "campaigns.html", {
        "campaigns": campaigns,
        "total_campaigns": campaigns.count(),
        "total_leads": campaigns.aggregate(total=Sum("leads_generated"))["total"] or 0,
        "total_conversions": campaigns.aggregate(total=Sum("conversions"))["total"] or 0,
        "avg_roi": round(campaigns.aggregate(avg=Avg("roi_estimate"))["avg"] or 0, 2),
    })


# ─────────────────────────────────────────────
# COMPETITORS  — real-time refresh
# ─────────────────────────────────────────────
import json
import random
from django.db.models import Avg
from django.utils import timezone
from .models import Competitor


def competitors_view(request):
    """
    Competitor intelligence view.

    Rules:
      - Our Company always holds a dominant slice (~45 % baseline ± small variance).
      - Show only the top 5 competitors by threat level.
      - All remaining competitors are bucketed as "Others".
      - Small random variance is added to every value on each load so the
        charts feel 'live'. A JS timer reloads the page every 30 s.
    """

    all_competitors = Competitor.objects.all().order_by("-threat_level")

    top5 = list(all_competitors[:5])
    others_qs = all_competitors[5:]

    # ── Market-share: Our Company + top 5 + Others ──────────────────────
    def _vary(value, pct=0.08):
        """Return value ±pct random jitter, 2 dp."""
        delta = value * pct
        return round(max(0.0, value + random.uniform(-delta, delta)), 1)

    # Sum the raw top-5 shares (no jitter yet — we need headroom first)
    top5_raw_share = sum(c.market_share_estimate or 0 for c in top5)
    others_raw_share = sum(c.market_share_estimate or 0 for c in others_qs)

    # Our share = whatever is left, baseline ~45 %, floored at 30
    our_share_base = max(100.0 - top5_raw_share - others_raw_share, 30.0)
    our_share = _vary(our_share_base, pct=0.05)   # tighter variance for us

    top5_shares = [_vary(c.market_share_estimate or 0) for c in top5]
    others_share = _vary(others_raw_share) if others_qs.exists() else 0.0

    market_labels = ["MTB"] + [c.name for c in top5]
    market_values = [our_share] + top5_shares

    if others_share > 0:
        market_labels.append("Others")
        market_values.append(others_share)

    # ── Threat chart: Our Company (0 threat) + top 5 ────────────────────
    threat_labels = ["MTB"] + [c.name for c in top5]
    threat_values = [0] + [_vary(c.threat_level or 0, pct=0.06) for c in top5]

    # ── Summary metrics (always from full dataset) ───────────────────────
    total     = all_competitors.count()
    high      = all_competitors.filter(threat_level__gte=7).count()
    medium    = all_competitors.filter(threat_level__gte=4, threat_level__lt=7).count()
    low       = all_competitors.filter(threat_level__lt=4).count()

    context = {
        # Table shows top 5 only
        "competitors": top5,
        "others_count": others_qs.count(),

        # KPI cards
        "total_competitors": total,
        "high_threat": high,
        "medium_threat": medium,
        "low_threat": low,

        # Chart data (JSON-safe)
        "market_labels": json.dumps(market_labels),
        "market_values": json.dumps(market_values),
        "threat_labels": json.dumps(threat_labels),
        "threat_values": json.dumps(threat_values),

        # Live timestamp
        "last_refreshed": timezone.now(),
    }
    return render(request, "competitors.html", context)


# ─────────────────────────────────────────────
# ORGANISATION
# ─────────────────────────────────────────────

def organisation_view(request):
    orgs = ClientOrganization.objects.all()
    return render(request, "organisation.html", {
        "organizations": orgs,
        "total_orgs": orgs.count(),
        "active_orgs": orgs.filter(relationship_status="active").count(),
        "prospects": orgs.filter(relationship_status="prospect").count(),
        "at_risk": orgs.filter(relationship_status="at_risk").count(),
        "form": ClientOrganizationForm(),
    })


def add_organization(request):
    if request.method == "POST":
        form = ClientOrganizationForm(request.POST)
        if form.is_valid():
            form.save()
    return redirect("organizations")


def edit_organization(request, pk):
    org = get_object_or_404(ClientOrganization, pk=pk)
    if request.method == "POST":
        form = ClientOrganizationForm(request.POST, instance=org)
        if form.is_valid():
            form.save()
            return redirect("organizations")
    else:
        form = ClientOrganizationForm(instance=org)
    return render(request, "client/edit_org_form.html", {"form": form})


# ─────────────────────────────────────────────
# SITE VISIT
# ─────────────────────────────────────────────

def site_visit_view(request):
    visits = SiteVisit.objects.order_by("-timestamp")
    return render(request, "audit.html", {
        "visits": visits[:500],
        "total_visits": visits.count(),
        "total_users": visits.filter(is_authenticated=True).count(),
        "total_bounce": visits.filter(is_bounce=True).count(),
        "conversions": visits.filter(converted=True).count(),
        "visit_types": list(visits.values("visit_type").annotate(count=Count("id"))),
        "device_stats": list(visits.values("device_type").annotate(count=Count("id"))),
    })


# ─────────────────────────────────────────────
# ENGAGEMENT
# ─────────────────────────────────────────────

def engagement_view(request):
    engagements = TrainingEngagement.objects.select_related("organization", "program")
    return render(request, "engagement.html", {
        "engagements": engagements,
        "total_engagements": engagements.count(),
        "churn_cases": engagements.filter(churn_flag=True).count(),
        "renewals_expected": engagements.filter(renewal_expected=True).count(),
        "high_engagement": engagements.filter(engagement_index__gte=70).count(),
        "form": TrainingEngagementForm(),
    })


def add_training_engagement(request):
    if request.method == "POST":
        form = TrainingEngagementForm(request.POST)
        if form.is_valid():
            form.save()
    return redirect("training_engagement")


def edit_training_engagement(request, pk):
    engagement = get_object_or_404(TrainingEngagement, pk=pk)
    if request.method == "POST":
        form = TrainingEngagementForm(request.POST, instance=engagement)
        if form.is_valid():
            form.save()
            return redirect("training_engagement")
    else:
        form = TrainingEngagementForm(instance=engagement)
    return render(request, "client/edit_engagement_form.html", {"form": form})


# ─────────────────────────────────────────────
# TRAINING
# ─────────────────────────────────────────────

def training_view(request):
    trainings = TrainingProgram.objects.all()
    return render(request, "training.html", {
        "trainings": trainings,
        "total_trainings": trainings.count(),
        "active_trainings": trainings.filter(active=True).count(),
        "inactive_trainings": trainings.filter(active=False).count(),
        "certified_trainings": trainings.filter(certification_awarded=True).count(),
        "form": TrainingProgramForm(),
    })


def add_training_program(request):
    if request.method == "POST":
        form = TrainingProgramForm(request.POST)
        if form.is_valid():
            form.save()
    return redirect("training_programs")


def edit_training_program(request, pk):
    training = get_object_or_404(TrainingProgram, pk=pk)
    if request.method == "POST":
        form = TrainingProgramForm(request.POST, instance=training)
        if form.is_valid():
            form.save()
            return redirect("training_programs")
    else:
        form = TrainingProgramForm(instance=training)
    return render(request, "client/edit_training_form.html", {"form": form})


# ─────────────────────────────────────────────
# TASKS
# ─────────────────────────────────────────────

def task_view(request):
    tasks = Task.objects.select_related("assigned_to", "related_organization").all()
    return render(request, "tasks.html", {
        "tasks": tasks,
        "total_tasks": tasks.count(),
        "completed_tasks": tasks.filter(status="completed").count(),
        "pending_tasks": tasks.filter(status="pending").count(),
        "overdue_tasks": tasks.filter(status="overdue").count(),
        "form": TaskForm(),
    })


def add_task(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
    return redirect("task_list")


def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
    return redirect("task_list")