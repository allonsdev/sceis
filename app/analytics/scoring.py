from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, Count

from app.models import (
    ClientOrganization,
    TrainingEngagement,
    CommunicationLog,
    SiteVisit,
)


# -----------------------------
# ENGAGEMENT SCORE CALCULATOR
# -----------------------------
def calculate_engagement_score(org: ClientOrganization) -> float:
    now = timezone.now()
    last_90_days = now - timedelta(days=90)

    visits = SiteVisit.objects.filter(
        organization=org,
        timestamp__gte=last_90_days
    ).count()

    communications = CommunicationLog.objects.filter(
        organization=org,
        timestamp__gte=last_90_days
    ).count()

    avg_satisfaction = TrainingEngagement.objects.filter(
        organization=org
    ).aggregate(avg=Avg("satisfaction_score"))["avg"] or 0

    completion_rate = TrainingEngagement.objects.filter(
        organization=org
    ).aggregate(avg=Avg("completion_rate"))["avg"] or 0

    # weighted score (tune later)
    score = (
        visits * 0.2 +
        communications * 0.3 +
        avg_satisfaction * 10 +
        completion_rate * 5
    )

    return round(score, 2)


# -----------------------------
# RULE-BASED CHURN SCORE
# -----------------------------
def calculate_rule_based_churn(org: ClientOrganization) -> float:
    now = timezone.now()
    last_60_days = now - timedelta(days=60)

    recent_visits = SiteVisit.objects.filter(
        organization=org,
        timestamp__gte=last_60_days
    ).count()

    last_training = TrainingEngagement.objects.filter(
        organization=org
    ).order_by("-end_date").first()

    satisfaction = 0
    if last_training and last_training.satisfaction_score:
        satisfaction = last_training.satisfaction_score

    risk = 0

    if recent_visits == 0:
        risk += 40

    if satisfaction < 3:
        risk += 30

    if last_training and not last_training.renewal_expected:
        risk += 30

    return min(risk, 100)