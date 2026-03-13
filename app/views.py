from django.shortcuts import render, get_object_or_404
from app.models import *
from django.shortcuts import render
from .forms import *
# Dashboard
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import ChurnAlert
from .forms import *

from django.contrib.auth import logout
from django.shortcuts import redirect
from django.db.models import *

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages

def logout_view(request):
    """
    Logs out the user and redirects to login page
    """
    logout(request)
    return redirect('login')  # Replace 'login' with your login URL name
def dashboard_view(request):
        # -------------------------
   # -----------------------------
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status='completed').count()
    pending_tasks = Task.objects.filter(status='pending').count()
    overdue_tasks = Task.objects.filter(status='overdue').count()

    total_churn_alerts = ChurnAlert.objects.count()
    high_risk_alerts = ChurnAlert.objects.filter(risk_level='HIGH').count()
    medium_risk_alerts = ChurnAlert.objects.filter(risk_level='MEDIUM').count()
    low_risk_alerts = ChurnAlert.objects.filter(risk_level='LOW').count()

    # -----------------------------
    # Training Engagement Chart Data
    # -----------------------------
    engagements = (
        TrainingEngagement.objects
        .values('program__title')
        .annotate(avg_engagement=Avg('engagement_index'))
    )

    engagement_labels = [e['program__title'] for e in engagements]
    engagement_values = [round(e['avg_engagement'] or 0, 2) for e in engagements]

    # -----------------------------
    # Calendar Events (Tasks)
    # -----------------------------
    tasks = Task.objects.all()
    calendar_events = [
        {
            "title": t.title,
            "start": t.due_date.isoformat() if t.due_date else "",
            "color": "green" if t.status=="completed" else "red" if t.status=="overdue" else "orange"
        }
        for t in tasks if t.due_date
    ]
    
    print(calendar_events)
    # -----------------------------
    # DataTables
    # -----------------------------
    tasks_table = tasks.select_related('assigned_to', 'related_organization')
    churn_table = ChurnAlert.objects.select_related('organization')

    context = {
        # Cards
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'overdue_tasks': overdue_tasks,
        'total_churn_alerts': total_churn_alerts,
        'high_risk_alerts': high_risk_alerts,
        'medium_risk_alerts': medium_risk_alerts,
        'low_risk_alerts': low_risk_alerts,
        
        # Charts
        'engagement_labels': engagement_labels,
        'engagement_values': engagement_values,

        # Calendar
        'calendar_events': calendar_events,

        # Tables
        'tasks_table': tasks_table,
        'churn_table': churn_table,
    }

    return render(request, "dashboard.html", context)

# Client Alerts
def client_alerts_view(request):
    alerts = ChurnAlert.objects.select_related("organization").all()
    
    total_alerts = alerts.count()
    high_alerts = alerts.filter(risk_level="HIGH").count()
    medium_alerts = alerts.filter(risk_level="MEDIUM").count()
    low_alerts = alerts.filter(risk_level="LOW").count()

    form = ChurnAlertForm()

    return render(request, "churnalerts.html", {
        "alerts": alerts,
        "total_alerts": total_alerts,
        "high_alerts": high_alerts,
        "medium_alerts": medium_alerts,
        "low_alerts": low_alerts,
        "form": form,
    })


def add_churn_alert(request):
    if request.method == "POST":
        form = ChurnAlertForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({"success": True})
        return JsonResponse({"success": False, "errors": form.errors})
    return JsonResponse({"success": False, "error": "Invalid request"})


def edit_churn_alert(request, pk):
    alert = get_object_or_404(ChurnAlert, pk=pk)
    if request.method == "POST":
        form = ChurnAlertForm(request.POST, instance=alert)
        if form.is_valid():
            form.save()
            return JsonResponse({"success": True})
        return JsonResponse({"success": False, "errors": form.errors})
    
    # GET request, return form HTML
    form = ChurnAlertForm(instance=alert)
    return render(request, "partials/churn_alert_form.html", {"form": form})

# Communication
def communication_view(request):
    logs = CommunicationLog.objects.select_related('organization', 'contact').all().order_by('-created_at')

    # Pre-calculate counts
    total_logs = logs.count()
    responses_received = logs.filter(response_received=True).count()
    follow_ups_required = logs.filter(follow_up_required=True).count()
    pending_responses = logs.filter(response_received=False).count()

    context = {
        "logs": logs,
        "total_logs": total_logs,
        "responses_received": responses_received,
        "follow_ups_required": follow_ups_required,
        "pending_responses": pending_responses,
    }
    return render(request, "communication.html", context)
# Campaigns
def campaigns_view(request):
    
    campaigns = MarketingCampaign.objects.all().order_by("-start_date")

    total_campaigns = campaigns.count()

    total_leads = campaigns.aggregate(total=Sum("leads_generated"))["total"] or 0

    total_conversions = campaigns.aggregate(total=Sum("conversions"))["total"] or 0

    avg_roi = campaigns.aggregate(avg=Avg("roi_estimate"))["avg"] or 0

    context = {
        "campaigns": campaigns,
        "total_campaigns": total_campaigns,
        "total_leads": total_leads,
        "total_conversions": total_conversions,
        "avg_roi": round(avg_roi, 2),
    }
    return render(request, 'campaigns.html',context)

# Competitors
def competitors_view(request):
    competitors = Competitor.objects.all()

    total_competitors = competitors.count()

    high_threat = competitors.filter(threat_level__gte=7).count()
    medium_threat = competitors.filter(threat_level__gte=4, threat_level__lt=7).count()
    low_threat = competitors.filter(threat_level__lt=4).count()

    avg_market_share = competitors.aggregate(avg=Avg("market_share_estimate"))["avg"]

    context = {
        "competitors": competitors,
        "total_competitors": total_competitors,
        "high_threat": high_threat,
        "medium_threat": medium_threat,
        "low_threat": low_threat,
        "avg_market_share": avg_market_share or 0,
    }

    return render(request, "competitors.html", context)

# Organisation
def organisation_view(request):
    orgs = ClientOrganization.objects.all()

    context = {
        "organizations": orgs,
        "total_orgs": orgs.count(),
        "active_orgs": orgs.filter(relationship_status="active").count(),
        "prospects": orgs.filter(relationship_status="prospect").count(),
        "at_risk": orgs.filter(relationship_status="at_risk").count(),
        "form": ClientOrganizationForm()
    }

    return render(request, "organisation.html", context)


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

# Site Visit
def site_visit_view(request):


    visits = SiteVisit.objects.all().order_by("-timestamp")

    total_visits = visits.count()
    total_users = visits.filter(is_authenticated=True).count()
    total_bounce = visits.filter(is_bounce=True).count()
    conversions = visits.filter(converted=True).count()

    visit_types = visits.values("visit_type").annotate(count=Count("id"))

    device_stats = visits.values("device_type").annotate(count=Count("id"))

    context = {
        "visits": visits[:500],
        "total_visits": total_visits,
        "total_users": total_users,
        "total_bounce": total_bounce,
        "conversions": conversions,
        "visit_types": list(visit_types),
        "device_stats": list(device_stats),
    }

    return render(request, "audit.html", context)
# Engagement
def engagement_view(request):
    engagements = TrainingEngagement.objects.select_related("organization", "program")

    context = {
        "engagements": engagements,
        "total_engagements": engagements.count(),
        "churn_cases": engagements.filter(churn_flag=True).count(),
        "renewals_expected": engagements.filter(renewal_expected=True).count(),
        "high_engagement": engagements.filter(engagement_index__gte=70).count(),
        "form": TrainingEngagementForm()
    }

    return render(request, "engagement.html", context)


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
# Training
def training_view(request):
    trainings = TrainingProgram.objects.all()

    context = {
        "trainings": trainings,
        "total_trainings": trainings.count(),
        "active_trainings": trainings.filter(active=True).count(),
        "inactive_trainings": trainings.filter(active=False).count(),
        "certified_trainings": trainings.filter(certification_awarded=True).count(),
        "form": TrainingProgramForm()
    }

    return render(request, "training.html", context)


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

# Task
def task_view(request):
    tasks = Task.objects.select_related("assigned_to", "related_organization").all()

    # Card data
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status="completed").count()
    pending_tasks = tasks.filter(status="pending").count()
    overdue_tasks = tasks.filter(status="overdue").count()

    context = {
        "tasks": tasks,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "overdue_tasks": overdue_tasks,
        "form": TaskForm(),
    }
    return render(request, "tasks.html", context)


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

def home(request):
    return render(request, "landing/index.html")

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Login successful")
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid username or password")

    return render(request, "login.html")

def dashboard(request):
    return render(request, "dashboard/index.html")







def tasks(request):
    return render(request, "tasks.html")
