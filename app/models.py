"""
models.py — Updated
Key fixes:
  - ClientOrganization.churn_level: was a method calling self.churn_alerts, fixed as @property
  - EmailMessage: uses auto int pk (not UUID) so Django template {{ email.id }} works in URLs
  - Competitor: added __str__
  - Duplicate relationship_status field removed
  - SiteVisit: added __str__
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


# ─────────────────────────────────────────────
# ABSTRACT BASE MODELS
# ─────────────────────────────────────────────

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="created_%(class)s"
    )
    updated_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="updated_%(class)s"
    )
    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    is_deleted  = models.BooleanField(default=False, db_index=True)
    deleted_at  = models.DateTimeField(null=True, blank=True)
    class Meta:
        abstract = True


# ─────────────────────────────────────────────
# SITE VISIT
# ─────────────────────────────────────────────

class SiteVisit(models.Model):
    VISIT_TYPE = [
        ("page_view", "Page View"),
        ("login", "Login"),
        ("logout", "Logout"),
        ("api_call", "API Call"),
        ("file_download", "File Download"),
        ("form_submit", "Form Submit"),
        ("other", "Other"),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user            = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    session_key     = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    is_authenticated= models.BooleanField(default=False)

    organization    = models.ForeignKey(
        "ClientOrganization", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="site_visits"
    )

    visit_type      = models.CharField(max_length=50, choices=VISIT_TYPE)
    path            = models.CharField(max_length=500, db_index=True)
    view_name       = models.CharField(max_length=255, blank=True)
    http_method     = models.CharField(max_length=10, blank=True)

    timestamp       = models.DateTimeField(default=timezone.now, db_index=True)
    duration_seconds= models.FloatField(null=True, blank=True)

    ip_address      = models.GenericIPAddressField(null=True, blank=True)
    user_agent      = models.TextField(blank=True)
    device_type     = models.CharField(max_length=50, blank=True)
    browser         = models.CharField(max_length=100, blank=True)
    os              = models.CharField(max_length=100, blank=True)

    referrer        = models.URLField(blank=True)
    utm_source      = models.CharField(max_length=255, blank=True)
    utm_medium      = models.CharField(max_length=255, blank=True)
    utm_campaign    = models.CharField(max_length=255, blank=True)

    country         = models.CharField(max_length=100, blank=True)
    city            = models.CharField(max_length=100, blank=True)

    is_bounce       = models.BooleanField(default=False)
    converted       = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["user"]),
            models.Index(fields=["organization"]),
            models.Index(fields=["visit_type"]),
        ]

    def __str__(self):
        return f"{self.visit_type} — {self.path} ({self.timestamp:%Y-%m-%d %H:%M})"


# ─────────────────────────────────────────────
# CLIENT ORGANISATION
# ─────────────────────────────────────────────

class ClientOrganization(TimeStampedModel, SoftDeleteModel):
    ORGANIZATION_TYPE = [
        ("university", "University"),
        ("polytechnic", "Polytechnic"),
        ("training_college", "Training College"),
        ("corporate", "Corporate"),
        ("government", "Government"),
        ("ngo", "NGO"),
        ("other", "Other"),
    ]

    RELATIONSHIP_STATUS = [
        ("prospect", "Prospect"),
        ("active", "Active"),
        ("at_risk", "At Risk"),
        ("churned", "Churned"),
        ("reengage", "Re-engage"),
    ]

    name                    = models.CharField(max_length=255, db_index=True)
    legal_name              = models.CharField(max_length=255, blank=True)
    organization_type       = models.CharField(max_length=50, choices=ORGANIZATION_TYPE)

    registration_number     = models.CharField(max_length=100, blank=True)
    tax_number              = models.CharField(max_length=100, blank=True)

    industry_sector         = models.CharField(max_length=255, blank=True)
    sub_sector              = models.CharField(max_length=255, blank=True)

    country                 = models.CharField(max_length=100, default="Zimbabwe")
    province                = models.CharField(max_length=100, blank=True)
    city                    = models.CharField(max_length=100, blank=True)
    physical_address        = models.TextField(blank=True)

    website                 = models.URLField(blank=True)
    primary_email           = models.EmailField(blank=True)
    primary_phone           = models.CharField(max_length=50, blank=True)

    size_estimate           = models.IntegerField(null=True, blank=True)
    annual_training_budget  = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    relationship_start_date = models.DateField(null=True, blank=True)
    relationship_status     = models.CharField(
        max_length=50, choices=RELATIONSHIP_STATUS, default="prospect"
    )

    account_manager         = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="managed_organizations"
    )

    churn_risk_score        = models.FloatField(default=0.0)
    lifetime_value_estimate = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    notes                   = models.TextField(blank=True)

    def __str__(self):
        return self.name

    @property
    def churn_level(self):
        """Derived from linked ChurnAlerts — HIGH > MEDIUM > LOW"""
        alerts = self.churn_alerts.filter(resolved=False)
        if alerts.filter(risk_level="HIGH").exists():
            return "HIGH"
        if alerts.filter(risk_level="MEDIUM").exists():
            return "MEDIUM"
        return "LOW"


# ─────────────────────────────────────────────
# CLIENT CONTACT
# ─────────────────────────────────────────────

class ClientContact(TimeStampedModel, SoftDeleteModel):
    organization            = models.ForeignKey(
        ClientOrganization, on_delete=models.CASCADE, related_name="contacts"
    )
    first_name              = models.CharField(max_length=100)
    last_name               = models.CharField(max_length=100)
    job_title               = models.CharField(max_length=255, blank=True)
    department              = models.CharField(max_length=255, blank=True)
    seniority_level         = models.CharField(max_length=100, blank=True)
    email                   = models.EmailField(db_index=True)
    phone                   = models.CharField(max_length=50, blank=True)
    decision_maker          = models.BooleanField(default=False)
    primary_contact         = models.BooleanField(default=False)
    engagement_score        = models.FloatField(default=0.0)
    communication_preference= models.CharField(max_length=50, blank=True)
    last_interaction_date   = models.DateTimeField(null=True, blank=True)
    satisfaction_rating     = models.FloatField(null=True, blank=True)
    notes                   = models.TextField(blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# ─────────────────────────────────────────────
# TRAINING PROGRAMS
# ─────────────────────────────────────────────

class TrainingProgram(TimeStampedModel):
    title                   = models.CharField(max_length=255)
    category                = models.CharField(max_length=255)
    delivery_mode           = models.CharField(max_length=100)
    description             = models.TextField(blank=True)
    duration_days           = models.IntegerField(null=True, blank=True)
    cost_per_participant    = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    certification_awarded   = models.BooleanField(default=False)
    accreditation_body      = models.CharField(max_length=255, blank=True)
    target_audience         = models.TextField(blank=True)
    learning_objectives     = models.TextField(blank=True)
    active                  = models.BooleanField(default=True)

    def __str__(self):
        return self.title


# ─────────────────────────────────────────────
# TRAINING ENGAGEMENT
# ─────────────────────────────────────────────

class TrainingEngagement(TimeStampedModel):
    organization                    = models.ForeignKey(ClientOrganization, on_delete=models.CASCADE)
    program                         = models.ForeignKey(TrainingProgram, on_delete=models.CASCADE)
    cohort_name                     = models.CharField(max_length=255, blank=True)
    start_date                      = models.DateField()
    end_date                        = models.DateField(null=True, blank=True)
    participants_count              = models.IntegerField(default=0)
    completion_rate                 = models.FloatField(default=0.0)
    average_attendance_rate         = models.FloatField(default=0.0)
    engagement_index                = models.FloatField(default=0.0)
    satisfaction_score              = models.FloatField(null=True, blank=True)
    net_promoter_score              = models.FloatField(null=True, blank=True)
    customized_content_requested    = models.BooleanField(default=False)
    customization_details           = models.TextField(blank=True)
    renewal_expected                = models.BooleanField(default=True)
    renewal_probability             = models.FloatField(default=0.0)
    revenue_generated               = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    churn_flag                      = models.BooleanField(default=False)
    churn_reason                    = models.TextField(blank=True)
    internal_notes                  = models.TextField(blank=True)

    def __str__(self):
        return f"{self.organization} — {self.program}"


# ─────────────────────────────────────────────
# COMMUNICATION LOG
# ─────────────────────────────────────────────

class CommunicationLog(TimeStampedModel):
    CHANNELS = [
        ("email", "Email"), ("phone", "Phone"), ("meeting", "Meeting"),
        ("sms", "SMS"), ("whatsapp", "WhatsApp"), ("other", "Other"),
    ]
    organization        = models.ForeignKey(ClientOrganization, on_delete=models.CASCADE)
    contact             = models.ForeignKey(ClientContact, null=True, blank=True, on_delete=models.SET_NULL)
    channel             = models.CharField(max_length=50, choices=CHANNELS)
    subject             = models.CharField(max_length=255, blank=True)
    interaction_summary = models.TextField()
    sentiment_score     = models.FloatField(null=True, blank=True)
    response_received   = models.BooleanField(default=False)
    response_time_hours = models.FloatField(null=True, blank=True)
    follow_up_required  = models.BooleanField(default=False)
    follow_up_date      = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.organization} — {self.channel} ({self.created_at:%Y-%m-%d})"


# ─────────────────────────────────────────────
# MARKETING CAMPAIGN
# ─────────────────────────────────────────────

class MarketingCampaign(TimeStampedModel):
    name                = models.CharField(max_length=255)
    campaign_type       = models.CharField(max_length=100)
    start_date          = models.DateField()
    end_date            = models.DateField(null=True, blank=True)
    target_segment      = models.TextField(blank=True)
    budget              = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    leads_generated     = models.IntegerField(default=0)
    conversions         = models.IntegerField(default=0)
    engagement_rate     = models.FloatField(default=0.0)
    roi_estimate        = models.FloatField(default=0.0)
    notes               = models.TextField(blank=True)

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────
# TASK
# ─────────────────────────────────────────────

class Task(TimeStampedModel):
    STATUS = [
        ("pending", "Pending"), ("in_progress", "In Progress"),
        ("completed", "Completed"), ("overdue", "Overdue"),
    ]
    title               = models.CharField(max_length=255)
    description         = models.TextField(blank=True)
    assigned_to         = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks"
    )
    related_organization= models.ForeignKey(
        ClientOrganization, null=True, blank=True, on_delete=models.CASCADE, related_name="tasks"
    )
    due_date            = models.DateField(null=True, blank=True)
    completed_at        = models.DateTimeField(null=True, blank=True)
    priority            = models.CharField(max_length=50, blank=True)
    status              = models.CharField(max_length=50, choices=STATUS, default="pending")

    def save(self, *args, **kwargs):
        if self.due_date and self.status != "completed":
            if self.due_date < timezone.now().date():
                self.status = "overdue"
        super().save(*args, **kwargs)

    def days_to_deadline(self):
        return (self.due_date - timezone.now().date()).days if self.due_date else None

    def is_overdue(self):
        return bool(self.due_date and self.due_date < timezone.now().date())

    def __str__(self):
        return self.title


# ─────────────────────────────────────────────
# COMPETITOR INTELLIGENCE
# ─────────────────────────────────────────────

class Competitor(TimeStampedModel):
    name                    = models.CharField(max_length=255)
    country                 = models.CharField(max_length=100, default="Zimbabwe")
    service_focus           = models.TextField(blank=True)
    pricing_notes           = models.TextField(blank=True)
    strengths               = models.TextField(blank=True)
    weaknesses              = models.TextField(blank=True)
    threat_level            = models.FloatField(default=0.0)
    market_share_estimate   = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────
# CHURN ALERT
# ─────────────────────────────────────────────

class ChurnAlert(TimeStampedModel):
    organization        = models.ForeignKey(
        ClientOrganization, on_delete=models.CASCADE, related_name="churn_alerts"
    )
    risk_score          = models.FloatField()
    risk_level          = models.CharField(max_length=50)
    trigger_reason      = models.TextField()
    recommended_action  = models.TextField(blank=True)
    acknowledged        = models.BooleanField(default=False)
    resolved            = models.BooleanField(default=False)

    def _compute_risk_level(self):
        if self.risk_score >= 0.7:
            return "HIGH"
        elif self.risk_score >= 0.4:
            return "MEDIUM"
        return "LOW"

    def save(self, *args, **kwargs):
        self.risk_level = self._compute_risk_level()
        super().save(*args, **kwargs)

        # Auto-create task for HIGH risk alerts
        if self.risk_level == "HIGH" and not self.resolved:
            existing = Task.objects.filter(
                related_organization=self.organization,
                title__icontains="Churn mitigation"
            ).exists()
            if not existing:
                Task.objects.create(
                    title="Churn mitigation call",
                    description=(
                        f"High churn risk detected for {self.organization}.\n\n"
                        f"Trigger: {self.trigger_reason}\n\n"
                        f"Recommended action: {self.recommended_action}"
                    ),
                    assigned_to=self.organization.account_manager,
                    related_organization=self.organization,
                    due_date=timezone.now().date() + timezone.timedelta(days=3),
                    status="pending",
                    priority="high",
                )

    def __str__(self):
        return f"{self.organization} — {self.risk_level}"


# ─────────────────────────────────────────────
# EMAIL MESSAGE  (from Gmail automation)
# ─────────────────────────────────────────────

class EmailMessageContacts(models.Model):
    """
    Stores emails fetched from Gmail + AI analysis results.
    Uses default auto int pk so {{ email.id }} works in Django URL tags.
    gmail_id stores the IMAP UID string.
    """
    gmail_id        = models.CharField(max_length=255, unique=True)

    organization    = models.ForeignKey(
        ClientOrganization, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="emails"
    )
    contact         = models.ForeignKey(
        ClientContact, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="emails"
    )

    sender          = models.EmailField(db_index=True)
    subject         = models.TextField()
    body            = models.TextField()

    received_at     = models.DateTimeField(db_index=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    # AI analysis results
    sentiment_score = models.FloatField(null=True, blank=True)
    intent          = models.CharField(max_length=100, blank=True)

    processed       = models.BooleanField(default=False)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.sender} — {self.subject[:60]}"
    
from django.db.models.signals import post_save
from django.dispatch import receiver
 
@receiver(post_save, sender=Task)
def task_post_save(sender, instance, created, **kwargs):
    """Fire task-created email the moment any Task is saved for the first time."""
    if created:
        # Import here to avoid circular import at module load time
        from app.task_email_lifecycle import send_task_created_email
        send_task_created_email(instance)
        
        
        

 
class BulkCampaign(models.Model):
    CAMPAIGN_TYPES = [
        ("promotion",    "Promotion"),
        ("discount",     "Discount"),
        ("announcement", "Announcement"),
        ("reminder",     "Reminder"),
        ("seasonal",     "Seasonal"),
    ]
 
    STATUS_CHOICES = [
        ("draft",      "Draft"),
        ("scheduled",  "Scheduled"),
        ("sending",    "Sending"),
        ("sent",       "Sent"),
        ("partial",    "Partially Sent"),
        ("failed",     "Failed"),
    ]
 
    # ── Core fields ────────────────────────────────────────────────────────
    name            = models.CharField(max_length=255)
    campaign_type   = models.CharField(max_length=50, choices=CAMPAIGN_TYPES, default="promotion")
    subject         = models.CharField(max_length=500)
    body            = models.TextField()
 
    # ── Recipients ─────────────────────────────────────────────────────────
    recipient_group  = models.CharField(
        max_length=50, default="all",
        help_text="Slug: all | active | prospects | at_risk | org_<id>"
    )
    # Serialised list of resolved email addresses at send time (JSON array)
    recipient_emails = models.TextField(blank=True, default="[]")
    recipient_count  = models.IntegerField(default=0)
 
    # ── Scheduling & status ────────────────────────────────────────────────
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    scheduled_at     = models.DateTimeField(null=True, blank=True)
    sent_at          = models.DateTimeField(null=True, blank=True)
    sent_count       = models.IntegerField(default=0)
 
    # ── Meta ───────────────────────────────────────────────────────────────
    created_at  = models.DateTimeField(default=timezone.now)
    updated_at  = models.DateTimeField(auto_now=True)
    created_by  = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="bulk_campaigns"
    )
 
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Bulk Campaign"
        verbose_name_plural = "Bulk Campaigns"
 
    def __str__(self):
        return f"{self.name} [{self.get_status_display()}]"
 
    @property
    def delivery_rate(self) -> float:
        """Percentage of recipients successfully reached."""
        if not self.recipient_count:
            return 0.0
        return round(self.sent_count / self.recipient_count * 100, 1)
 