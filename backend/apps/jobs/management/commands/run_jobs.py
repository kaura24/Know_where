from django.core.management.base import BaseCommand

from apps.jobs.services import process_jobs


class Command(BaseCommand):
    help = "Process queued background jobs."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **options):
        processed = process_jobs(limit=options["limit"])
        self.stdout.write(self.style.SUCCESS(f"Processed {processed} job(s)."))
