"""
Management command: python manage.py sync_emails
Place in: app/management/commands/sync_emails.py
(also create app/management/__init__.py and app/management/commands/__init__.py)
"""

from django.core.management.base import BaseCommand
from app.email_automation import EmailOrchestrator


class Command(BaseCommand):
    help = "Fetch unread Gmail emails, analyse with AI, create tasks and churn alerts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max",
            type=int,
            default=50,
            help="Maximum number of unread emails to process (default: 50)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("🔄  Starting email sync…"))

        orchestrator = EmailOrchestrator()
        summary = orchestrator.run()

        self.stdout.write(self.style.SUCCESS(
            f"\n✅  Done!\n"
            f"   Emails processed  : {summary['emails_processed']}\n"
            f"   Tasks created     : {summary['tasks_created']}\n"
            f"   Churn alerts      : {summary['churn_alerts_created']}\n"
            f"   Errors            : {summary['errors']}\n"
        ))