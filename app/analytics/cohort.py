from django.utils import timezone
from datetime import timedelta
from collections import defaultdict

from app.models import ClientOrganization, TrainingEngagement


def compute_retention_by_month():
    cohorts = defaultdict(list)

    for org in ClientOrganization.objects.all():
        start = org.relationship_start_date
        if not start:
            continue

        cohort_key = start.strftime("%Y-%m")

        active = TrainingEngagement.objects.filter(
            organization=org,
            end_date__gte=start + timedelta(days=90)
        ).exists()

        cohorts[cohort_key].append(1 if active else 0)

    retention = {}

    for cohort, values in cohorts.items():
        retention[cohort] = sum(values) / len(values)

    return retention