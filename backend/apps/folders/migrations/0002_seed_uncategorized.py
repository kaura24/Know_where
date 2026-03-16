from django.db import migrations


def seed_uncategorized(apps, schema_editor):
    Folder = apps.get_model("folders", "Folder")
    Folder.objects.get_or_create(
        slug="uncategorized",
        defaults={
            "name": "미분류",
            "color": "gray",
            "sort_order": 0,
            "is_system": True,
        },
    )


def remove_uncategorized(apps, schema_editor):
    Folder = apps.get_model("folders", "Folder")
    Folder.objects.filter(slug="uncategorized", is_system=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("folders", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_uncategorized, remove_uncategorized),
    ]
