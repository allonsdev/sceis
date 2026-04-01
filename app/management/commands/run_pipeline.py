import time
from django.core.management.base import BaseCommand
from app.services import run_pipeline


class Command(BaseCommand):
    help = "Runs pipeline every 10 seconds"

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting 10-second loop...")

        creds = None  # later plug Gmail OAuth here

        while True:
            try:
                run_pipeline(creds)
                self.stdout.write("Pipeline executed successfully")

            except Exception as e:
                self.stderr.write(f"Error: {e}")

            time.sleep(10)