from django.core.management.base import BaseCommand
from app.task_email_lifecycle import run_lifecycle_automation
 
 
class Command(BaseCommand):
    help = "Run the client lifecycle automation (follow-up + archive)."
 
    def handle(self, *args, **options):
        result = run_lifecycle_automation()
        self.stdout.write(
            self.style.SUCCESS(
                f"Lifecycle run complete — "
                f"follow-ups sent: {result['followups_sent']}, "
                f"orgs archived: {result['orgs_archived']}"
            )
        )