from rest_framework import serializers

from .models import Folder


class FolderSerializer(serializers.ModelSerializer):
    card_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Folder
        fields = [
            "id",
            "name",
            "slug",
            "color",
            "sort_order",
            "is_system",
            "card_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "is_system", "created_at", "updated_at"]


class FolderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ["name", "color"]
