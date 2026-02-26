from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta

from app.models import (
    ClientOrganization,
    TrainingEngagement,
    SiteVisit,
)


def churn_risk_distribution():
    return ClientOrganization.objects.values(
        "relationship_status"
    ).annotate(total=Count("id"))


def engagement_trend():
    last_6_months = timezone.now() - timedelta(days=180)

    return SiteVisit.objects.filter(
        timestamp__gte=last_6_months
    ).extra(
        {"month": "date(timestamp)"}
    ).values("month").annotate(total=Count("id"))


def program_effectiveness():
    return TrainingEngagement.objects.values(
        "program__title"
    ).annotate(
        avg_satisfaction=Avg("satisfaction_score"),
        avg_completion=Avg("completion_rate"),
        total_clients=Count("organization", distinct=True)
    )