"""
app/tasks.py — Celery background tasks (optional but recommended)
─────────────────────────────────────────────────────────────────
Install: pip install celery redis django-celery-beat
Run:     celery -A your_project worker --loglevel=info
Beat:    celery -A your_project beat --loglevel=info
─────────────────────────────────────────────────────────────────
"""

# Wrap in try/except so the app works without Celery installed
try:
    from celery import shared_task

    @shared_task(bind=True, max_retries=3)
    def sync_emails_task(self):
        """
        Background task: fetch + analyse Gmail emails every N minutes.
        Configured in settings.py CELERY_BEAT_SCHEDULE.
        """
        from app.services.email_automation import EmailOrchestrator
        import logging

        logger = logging.getLogger(__name__)

        try:
            orchestrator = EmailOrchestrator()
            summary = orchestrator.run()
            logger.info(f"[CeleryTask] Email sync complete: {summary}")
            return summary
        except Exception as exc:
            logger.error(f"[CeleryTask] Email sync failed: {exc}")
            raise self.retry(exc=exc, countdown=60)

    @shared_task
    def generate_daily_churn_report():
        """
        Daily task: scan all organisations, compute churn risk, create alerts.
        """
        from django.utils import timezone
        from app.models import ClientOrganization, ChurnAlert, TrainingEngagement

        today = timezone.now().date()
        orgs = ClientOrganization.objects.filter(relationship_status__in=["active", "at_risk"])

        created = 0
        for org in orgs:
            # Rule-based churn signals
            low_engagement = TrainingEngagement.objects.filter(
                organization=org, engagement_index__lt=40
            ).exists()

            no_comms = not org.churn_alerts.filter(
                created_at__gte=today - timezone.timedelta(days=30)
            ).exists()

            if low_engagement or no_comms:
                # Don't duplicate today's alert
                if not ChurnAlert.objects.filter(
                    organization=org,
                    created_at__date=today
                ).exists():
                    reason_parts = []
                    if low_engagement:
                        reason_parts.append("low training engagement index (< 40)")
                    if no_comms:
                        reason_parts.append("no communication in 30+ days")

                    ChurnAlert.objects.create(
                        organization=org,
                        risk_score=0.65 if low_engagement and no_comms else 0.45,
                        trigger_reason=f"[Auto Daily Scan] {', '.join(reason_parts)}",
                        recommended_action="Schedule a check-in call with the account manager.",
                    )
                    created += 1

        return {"churn_alerts_created": created}

except ImportError:
    # Celery not installed — tasks won't be registered but app still works
    pass