from django.apps import AppConfig
import threading
import time
import logging
import os

class MyAppConfig(AppConfig):
    name = 'app'

    def ready(self):
        # ✅ Prevent duplicate threads
        if os.environ.get('RUN_MAIN') != 'true':
            return

        from app.task_email_lifecycle import run_lifecycle_automation

        def background_worker():
            print("🚀 THREAD STARTED")

            while True:
                try:
                    print("⏳ CALLING LIFECYCLE...")
                    run_lifecycle_automation()
                except Exception as e:
                    logging.getLogger(__name__).error(
                        "Lifecycle worker error: %s", e
                    )

                time.sleep(60)

        threading.Thread(target=background_worker, daemon=True).start()