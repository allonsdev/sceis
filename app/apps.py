from django.apps import AppConfig

import threading
import time

class AppConfig(AppConfig):
    name = 'app'
    
    
    def ready(self):
        from app.task_email_lifecycle import run_lifecycle_automation

        def background_worker():
            while True:
                try:
                    run_lifecycle_automation()
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error("Lifecycle worker error: %s", e)

                time.sleep(60)  # run every 60 seconds

        thread = threading.Thread(target=background_worker, daemon=True)
        thread.start()