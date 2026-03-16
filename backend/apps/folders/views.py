from django.db.models import Count
from django.utils.text import slugify
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Folder
from .serializers import FolderCreateSerializer, FolderSerializer


class FolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.all().annotate(card_count=Count("cards")).order_by("sort_order", "id")
    serializer_class = FolderSerializer
    pagination_class = None

    def _build_unique_slug(self, name: str) -> str:
        base_slug = slugify(name, allow_unicode=True) or "folder"
        candidate = base_slug
        index = 2
        while Folder.objects.filter(slug=candidate).exists():
            candidate = f"{base_slug}-{index}"
            index += 1
        return candidate

    def get_serializer_class(self):
        if self.action == "create":
            return FolderCreateSerializer
        return FolderSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data["name"]
        folder = Folder.objects.create(
            name=name,
            slug=self._build_unique_slug(name),
            color=serializer.validated_data.get("color"),
        )
        return Response(FolderSerializer(folder).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        folder = self.get_object()
        if folder.is_system:
            return Response(
                {"code": "CONFLICT", "message": "System folder cannot be deleted.", "details": {}},
                status=status.HTTP_409_CONFLICT,
            )
        uncategorized, _ = Folder.objects.get_or_create(
            slug="uncategorized",
            defaults={"name": "미분류", "is_system": True, "sort_order": 0},
        )
        folder.cards.update(folder=uncategorized)
        folder.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
