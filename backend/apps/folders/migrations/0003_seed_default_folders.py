from django.db import migrations


DEFAULT_FOLDERS = [
    {
        "slug": "coding",
        "name": "코딩",
        "color": "blue",
        "sort_order": 10,
        "is_system": True,
    },
    {
        "slug": "travel",
        "name": "여행",
        "color": "emerald",
        "sort_order": 20,
        "is_system": True,
    },
    {
        "slug": "work",
        "name": "업무",
        "color": "amber",
        "sort_order": 30,
        "is_system": True,
    },
]


def seed_default_folders(apps, schema_editor):
    Folder = apps.get_model("folders", "Folder")
    for folder_data in DEFAULT_FOLDERS:
        Folder.objects.get_or_create(
            slug=folder_data["slug"],
            defaults=folder_data,
        )


def remove_default_folders(apps, schema_editor):
    Folder = apps.get_model("folders", "Folder")
    Folder.objects.filter(
        slug__in=[folder["slug"] for folder in DEFAULT_FOLDERS],
        is_system=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("folders", "0002_seed_uncategorized"),
    ]

    operations = [
        migrations.RunPython(seed_default_folders, remove_default_folders),
    ]
