from django.db import models


class Folder(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    color = models.CharField(max_length=20, blank=True, null=True)
    sort_order = models.IntegerField(default=0)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "folder"
        verbose_name_plural = "folders"

    def __str__(self) -> str:
        return self.name
