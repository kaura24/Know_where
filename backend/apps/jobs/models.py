from django.db import models


class Job(models.Model):
    class JobStatus(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    job_type = models.CharField(max_length=50)
    target_type = models.CharField(max_length=50)
    target_id = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.QUEUED)
    priority = models.IntegerField(default=100)
    attempt_count = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    payload_json = models.JSONField(blank=True, null=True)
    last_error = models.TextField(blank=True, null=True)
    scheduled_at = models.DateTimeField()
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
