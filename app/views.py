"""
views.py — full updated file
Adds: email intelligence, sync, reply generation, send, task-from-email, flag-churn
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



from django.views.decorators.http import require_POST   # already imported
from django.http import JsonResponse                     # already imported
 
@require_POST
def run_lifecycle_view(request):
    """
    POST /lifecycle/run/
    Manually trigger the lifecycle engine from the dashboard.
    """
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

def email_intelligence_view(request):
    emails_qs = EmailMessage.objects.select_related("organization", "contact").order_by("-received_at")

    total_emails = emails_qs.count()
    high_risk_count = emails_qs.filter(sentiment_score__lt=-0.3).count()
    processed_count = emails_qs.filter(processed=True).count()

    emails = emails_qs[:100]  
    for email in emails:
        email.neg_sentiment = abs(email.sentiment_score) # Slice only for display

    # Tasks that were created from emails (heuristic: title contains "Email" or description has "---")
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
    """
    Trigger Gmail fetch + AI analysis. Returns JSON summary.
    """
    try:
        orchestrator = EmailOrchestrator()
        summary = orchestrator.run()
        return JsonResponse(summary)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@require_POST
def email_generate_reply(request):
    """
    Generate a professional email reply using OpenRouter (OpenAI client).
    """
    try:
        data = json.loads(request.body)

        tone = data.get("tone", "professional")
        context_notes = data.get("context", "")
        subject = data.get("subject", "")
        to = data.get("to", "")

        # ✅ Init AI client
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

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

        # ✅ Build prompt
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

        # ✅ Call OpenRouter
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

        return JsonResponse({
            "reply": fallback,
            "error": str(exc)
        }, status=200)
        
        

@require_POST
def email_send_reply(request):
    """
    Send a reply via SMTP (uses Django EMAIL_* settings).
    Settings needed:
        EMAIL_HOST         = "smtp.gmail.com"
        EMAIL_PORT         = 587
        EMAIL_USE_TLS      = True
        EMAIL_HOST_USER    = "you@gmail.com"
        EMAIL_HOST_PASSWORD = "app-password"
        DEFAULT_FROM_EMAIL = "you@gmail.com"
    """
    try:
        data = json.loads(request.body)
        to_addr = data.get("to", "")
        subject = data.get("subject", "")
        body = data.get("body", "")

        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_addr],
            fail_silently=False,
        )
        return JsonResponse({"success": True})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)})


from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from app.models import EmailMessage, Task

User = get_user_model()


@require_POST
def email_create_task(request, email_id):
    """Manually create a task from an email."""
    try:
        email_obj = get_object_or_404(EmailMessage, id=email_id)

        # ✅ Get first superuser
        default_user = User.objects.filter(is_superuser=True).order_by("id").first()

        if not default_user:
            return JsonResponse({
                "success": False,
                "error": "No superuser found to assign the task."
            })

        task = Task.objects.create(
            title=f"Follow up: {email_obj.subject[:80]}",
            description=(
                f"[AUTO-GENERATED FROM EMAIL]\n\n"
                f"From: {email_obj.sender}\n"
                f"Subject: {email_obj.subject}\n\n"
                f"--- Original Email ---\n{email_obj.body[:500]}"
            ),
            assigned_to=default_user,  # ✅ key fix
            related_organization=email_obj.organization,
            due_date=timezone.now().date() + timedelta(days=3),
            priority="medium",
            status="pending",
        )

        return JsonResponse({
            "success": True,
            "task_id": task.id,
            "assigned_to": default_user.username
        })

    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)})


@require_POST
def email_flag_churn(request, email_id):
    """Manually create a churn alert from an email."""
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
# COMPETITORS
# ─────────────────────────────────────────────

def competitors_view(request):
    competitors = Competitor.objects.all()
    return render(request, "competitors.html", {
        "competitors": competitors,
        "total_competitors": competitors.count(),
        "high_threat": competitors.filter(threat_level__gte=7).count(),
        "medium_threat": competitors.filter(threat_level__gte=4, threat_level__lt=7).count(),
        "low_threat": competitors.filter(threat_level__lt=4).count(),
        "avg_market_share": competitors.aggregate(avg=Avg("market_share_estimate"))["avg"] or 0,
    })


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