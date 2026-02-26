from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import *


# =====================================================
# CLIENT ORGANIZATION (Aggregates + Churn Badge)
# =====================================================

@admin.register(ClientOrganization)
class ClientOrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization_type",
        "relationship_status",
        "account_manager",
        "churn_badge",
        "task_count",
    )

    list_filter = (
        "organization_type",
        "relationship_status",
        "country",
        "province",
        "industry_sector",
        "created_at",
    )

    search_fields = ("name", "legal_name", "industry_sector")
    autocomplete_fields = ("account_manager",)
    readonly_fields = ("created_at", "updated_at", "churn_level_display")
    date_hierarchy = "created_at"

    def task_count(self, obj):
        return obj.tasks.count()

    task_count.short_description = "Tasks"

    def churn_badge(self, obj):
        level = obj.churn_level()

        color = {
            "HIGH": "red",
            "MEDIUM": "orange",
            "LOW": "green",
        }.get(level, "gray")

        return format_html(
            '<span style="background:{};color:white;padding:4px 8px;border-radius:6px;">{}</span>',
            color,
            level
        )

    churn_badge.short_description = "Churn Risk"

    def churn_level_display(self, obj):
        return obj.churn_level()

    churn_level_display.short_description = "Churn Level"


# =====================================================
# CLIENT CONTACT
# =====================================================

@admin.register(ClientContact)
class ClientContactAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "organization",
        "job_title",
        "decision_maker",
        "primary_contact",
        "engagement_score",
        "last_interaction_date",
    )

    list_filter = (
        "decision_maker",
        "primary_contact",
        "department",
        "seniority_level",
    )

    search_fields = ("first_name", "last_name", "email", "organization__name")
    autocomplete_fields = ("organization",)
    date_hierarchy = "created_at"


# =====================================================
# TRAINING PROGRAM
# =====================================================

@admin.register(TrainingProgram)
class TrainingProgramAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "delivery_mode",
        "duration_days",
        "cost_per_participant",
        "active",
    )

    list_filter = ("category", "delivery_mode", "active")
    search_fields = ("title", "category")
    date_hierarchy = "created_at"


# =====================================================
# TRAINING ENGAGEMENT
# =====================================================

@admin.register(TrainingEngagement)
class TrainingEngagementAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "program",
        "start_date",
        "participants_count",
        "completion_rate",
        "satisfaction_score",
        "renewal_probability",
        "churn_flag",
    )

    list_filter = (
        "program",
        "churn_flag",
        "customized_content_requested",
        "renewal_expected",
        "start_date",
    )

    search_fields = ("organization__name", "program__title", "cohort_name")
    autocomplete_fields = ("organization", "program")
    date_hierarchy = "start_date"


# =====================================================
# COMMUNICATION LOG
# =====================================================

@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "contact",
        "channel",
        "created_at",
        "response_received",
        "sentiment_score",
        "follow_up_required",
    )

    list_filter = (
        "channel",
        "response_received",
        "follow_up_required",
        "created_at",
    )

    search_fields = ("organization__name", "contact__email", "subject")
    autocomplete_fields = ("organization", "contact")
    date_hierarchy = "created_at"


# =====================================================
# MARKETING CAMPAIGN
# =====================================================

@admin.register(MarketingCampaign)
class MarketingCampaignAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "campaign_type",
        "start_date",
        "end_date",
        "budget",
        "leads_generated",
        "conversions",
        "roi_estimate",
    )

    list_filter = ("campaign_type", "start_date", "end_date")
    search_fields = ("name", "campaign_type")
    date_hierarchy = "start_date"


# =====================================================
# TASK MANAGEMENT (Color + Deadline)
# =====================================================

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "assigned_to",
        "related_organization",
        "status_badge",
        "priority",
        "deadline_badge",
    )

    list_filter = (
        "status",
        "priority",
        "due_date",
    )

    search_fields = ("title", "description", "related_organization__name")
    autocomplete_fields = ("assigned_to", "related_organization")
    date_hierarchy = "due_date"
    readonly_fields = ("days_to_deadline",)

    def status_badge(self, obj):
        color = {
            "pending": "blue",
            "in_progress": "orange",
            "completed": "green",
            "overdue": "red",
        }.get(obj.status, "gray")

        return format_html(
            '<span style="background:{};color:white;padding:4px 8px;border-radius:6px;">{}</span>',
            color,
            obj.status
        )

    status_badge.short_description = "Status"

    def deadline_badge(self, obj):
        if not obj.due_date:
            return "No deadline"

        days = (obj.due_date - timezone.now().date()).days

        if days < 0:
            color = "red"
            text = f"Overdue by {abs(days)} days"
        elif days <= 3:
            color = "orange"
            text = f"Due soon ({days} days)"
        else:
            color = "green"
            text = f"{days} days remaining"

        return format_html(
            '<span style="background:{};color:white;padding:4px 8px;border-radius:6px;">{}</span>',
            color,
            text
        )

    deadline_badge.short_description = "Deadline"

    def days_to_deadline(self, obj):
        if not obj.due_date:
            return "No deadline"

        days = (obj.due_date - timezone.now().date()).days

        if days < 0:
            return f"Overdue by {abs(days)} days"

        return f"{days} days remaining"

    days_to_deadline.short_description = "Days"


# =====================================================
# COMPETITOR INTELLIGENCE (Aggregated Summary)
# =====================================================

@admin.register(Competitor)
class CompetitorAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country",
        "threat_level",
        "market_share_estimate",
        "created_at",
    )

    list_filter = ("country", "threat_level")
    search_fields = ("name", "service_focus")
    readonly_fields = ("summary",)
    date_hierarchy = "created_at"

    def summary(self, obj):
        return format_html(
            """
            <div style="padding:15px;background:#f8f9fa;border-radius:10px;">
                <h3>Competitor Overview</h3>
                <ul>
                    <li><strong>Threat Level:</strong> {}</li>
                    <li><strong>Market Share:</strong> {}%</li>
                </ul>
            </div>
            """,
            obj.threat_level,
            obj.market_share_estimate or 0
        )

    summary.short_description = "Summary"


# =====================================================
# CHURN ALERTS (Color + Aggregates)
# =====================================================

@admin.register(ChurnAlert)
class ChurnAlertAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "risk_badge",
        "acknowledged",
        "resolved",
        "created_at",
    )

    list_filter = (
        "risk_level",
        "acknowledged",
        "resolved",
        "created_at",
    )

    search_fields = ("organization__name", "trigger_reason")
    autocomplete_fields = ("organization",)
    date_hierarchy = "created_at"

    def risk_badge(self, obj):
        color = {
            "HIGH": "red",
            "MEDIUM": "orange",
            "LOW": "green",
        }.get(obj.risk_level, "gray")

        return format_html(
            '<span style="background:{};color:white;padding:4px 8px;border-radius:6px;">{}</span>',
            color,
            obj.risk_level
        )

    risk_badge.short_description = "Risk"


# =====================================================
# SITE VISIT ANALYTICS
# =====================================================

@admin.register(SiteVisit)
class SiteVisitAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "user",
        "organization",
        "visit_type",
        "path",
        "duration_seconds",
        "is_authenticated",
        "ip_address",
    )

    list_filter = (
        "visit_type",
        "is_authenticated",
        "organization",
        "timestamp",
    )

    search_fields = (
        "path",
        "user__username",
        "organization__name",
        "ip_address",
    )

    date_hierarchy = "timestamp"