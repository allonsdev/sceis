from django.db.models.signals import post_save
from django.dispatch import receiver
from app.notifications import send_churn_alert_email

from .models import (
    ClientOrganization,
    TrainingEngagement,
    CommunicationLog,
    SiteVisit,
    ChurnAlert
)

from app.analytics.scoring import (
    calculate_engagement_score,
    calculate_rule_based_churn,
)


def update_scores(org):
    engagement = calculate_engagement_score(org)
    churn_risk = calculate_rule_based_churn(org)

    org.churn_risk_score = churn_risk
    org.save(update_fields=["churn_risk_score"])

    if churn_risk >= 60:
        ChurnAlert.objects.create(
            organization=org,
            risk_score=churn_risk,
            risk_level="high",
            trigger_reason="Automated behavioral analysis"
        )


@receiver(post_save, sender=TrainingEngagement)
def training_update(sender, instance, **kwargs):
    update_scores(instance.organization)


@receiver(post_save, sender=CommunicationLog)
def communication_update(sender, instance, **kwargs):
    update_scores(instance.organization)


@receiver(post_save, sender=SiteVisit)
def visit_update(sender, instance, **kwargs):
    if instance.organization:
        update_scores(instance.organization)