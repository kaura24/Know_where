import time

from django.core.management.base import BaseCommand

from apps.jobs.services import process_jobs


class Command(BaseCommand):
    help = "Continuously poll and process queued background jobs."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument("--interval", type=float, default=5.0)
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        limit = options["limit"]
        interval = options["interval"]
        once = options["once"]

        while True:
            processed = process_jobs(limit=limit)
            self.stdout.write(f"Processed {processed} job(s).")
            if once:
                break
            time.sleep(interval)
