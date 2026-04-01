"""
urls.py — full updated URL configuration
Place in: your_project/urls.py  OR  app/urls.py (whichever is your main router)
"""

from django.contrib import admin
from django.urls import path
from app import views

urlpatterns = [
    # ── Auth ──────────────────────────────────
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # ── Dashboard ─────────────────────────────
    path("dashboard/", views.dashboard_view, name="dashboard"),

    # ── Email Intelligence ────────────────────
    path("email-intelligence/", views.email_intelligence_view, name="email_intelligence"),
    path("email/sync/",          views.email_sync_view,        name="email_sync"),
    path("email/generate-reply/",views.email_generate_reply,   name="email_generate_reply"),
    path("email/send/",          views.email_send_reply,        name="email_send_reply"),
    path("email/<int:email_id>/create-task/", views.email_create_task, name="email_create_task"),
    path("email/<int:email_id>/flag-churn/",  views.email_flag_churn,  name="email_flag_churn"),

    # ── Client Alerts ─────────────────────────
    path("client/",             views.client_alerts_view, name="client_alerts"),
    path("churn/add/",          views.add_churn_alert,    name="add_churn_alert"),
    path("churn/edit/<int:pk>/",views.edit_churn_alert,   name="edit_churn_alert"),

    # ── Communication ─────────────────────────
    path("communication/", views.communication_view, name="communication"),

    # ── Campaigns ─────────────────────────────
    path("campaigns/", views.campaigns_view, name="campaigns"),

    # ── Competitors ───────────────────────────
    path("competitors/", views.competitors_view, name="competitors"),

    # ── Organisation ──────────────────────────
    path("organisation/",             views.organisation_view,  name="organizations"),
    path("organisations/add/",        views.add_organization,   name="add_organization"),
    path("organizations/edit/<int:pk>/", views.edit_organization, name="edit_organization"),

    # ── Site Visit ────────────────────────────
    path("site-visit/", views.site_visit_view, name="site_visit"),

    # ── Engagement ────────────────────────────
    path("engagement/",                        views.engagement_view,          name="training_engagement"),
    path("engagement/add/",                    views.add_training_engagement,  name="add_training_engagement"),
    path("training-engagement/edit/<int:pk>/", views.edit_training_engagement, name="edit_training_engagement"),

    # ── Training ──────────────────────────────
    path("training/",             views.training_view,         name="training_programs"),
    path("training/add/",         views.add_training_program,  name="add_training_program"),
    path("training/edit/<int:pk>/", views.edit_training_program, name="edit_training_program"),
    path("lifecycle/run/", views.run_lifecycle_view, name="run_lifecycle"),

    # ── Tasks ─────────────────────────────────
    path("task/",             views.task_view, name="task_list"),
    path("tasks/add/",        views.add_task,  name="add_task"),
    path("tasks/edit/<int:pk>/", views.edit_task, name="edit_task"),
]