from rest_framework import serializers

from apps.folders.models import Folder
from .models import Card


class CardSerializer(serializers.ModelSerializer):
    folder_id = serializers.IntegerField(required=False, allow_null=True)
    tags = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    folder_name = serializers.CharField(source="folder.name", read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    has_memo = serializers.SerializerMethodField()
    tag_names = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Card
        fields = [
            "id",
            "folder_id",
            "folder_name",
            "url",
            "normalized_url",
            "source_domain",
            "title",
            "summary",
            "details",
            "memo",
            "tags",
            "tag_names",
            "has_memo",
            "thumbnail_status",
            "thumbnail_url",
            "thumbnail_error",
            "ingestion_status",
            "ingestion_error",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "folder_id": {"required": False},
            "title": {"required": False, "allow_blank": True},
            "summary": {"required": False, "allow_blank": True},
            "details": {"required": False, "allow_blank": True},
            "memo": {"required": False, "allow_blank": True},
        }
        read_only_fields = [
            "id",
            "normalized_url",
            "source_domain",
            "thumbnail_status",
            "thumbnail_url",
            "thumbnail_error",
            "ingestion_status",
            "ingestion_error",
            "created_at",
            "updated_at",
            "folder_name",
            "has_memo",
            "tag_names",
        ]

    def validate_folder_id(self, value):
        if not Folder.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid folder.")
        return value

    def get_thumbnail_url(self, obj: Card):
        return obj.thumbnail_path

    def get_has_memo(self, obj: Card):
        return bool(obj.memo.strip())

    def get_tag_names(self, obj: Card):
        return list(obj.tags.values_list("name", flat=True))


class CardStatusSerializer(serializers.ModelSerializer):
    card_id = serializers.IntegerField(source="id")
    thumbnail_error = serializers.CharField(allow_null=True)
    ingestion_error = serializers.CharField(allow_null=True)

    class Meta:
        model = Card
        fields = [
            "card_id",
            "thumbnail_status",
            "ingestion_status",
            "thumbnail_error",
            "ingestion_error",
            "updated_at",
        ]
