from django.db import models

from apps.folders.models import Folder


class Tag(models.Model):
    name = models.CharField(max_length=100)
    normalized_name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["normalized_name"]

    def __str__(self) -> str:
        return self.name


class Card(models.Model):
    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    folder = models.ForeignKey(Folder, related_name="cards", on_delete=models.PROTECT)
    url = models.URLField()
    normalized_url = models.URLField()
    source_domain = models.CharField(max_length=255)
    title = models.CharField(max_length=500)
    summary = models.TextField(blank=True, default="")
    details = models.TextField(blank=True, default="")
    memo = models.TextField(blank=True, default="")
    thumbnail_status = models.CharField(max_length=20, choices=ProcessingStatus.choices, default=ProcessingStatus.PENDING)
    thumbnail_path = models.TextField(blank=True, null=True)
    thumbnail_error = models.TextField(blank=True, null=True)
    ingestion_status = models.CharField(max_length=20, choices=ProcessingStatus.choices, default=ProcessingStatus.PENDING)
    ingestion_error = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, through="CardTag", related_name="cards")
    tags_text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class CardTag(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("card", "tag")
