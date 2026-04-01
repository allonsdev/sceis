from django.core.management.base import BaseCommand
from app.models import ClientOrganization


class Command(BaseCommand):
    help = "Set primary_email for all ClientOrganization records"

    def handle(self, *args, **kwargs):
        email = "kudzie556@gmail.com"

        updated_count = ClientOrganization.objects.update(primary_email=email)

        self.stdout.write(self.style.SUCCESS(
            f"✅ Successfully updated {updated_count} organizations."
        ))