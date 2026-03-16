from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.jobs.services import retry_card_jobs
from .models import Card
from .serializers import CardSerializer, CardStatusSerializer
from .services import create_card, update_card


class CardViewSet(viewsets.ModelViewSet):
    queryset = Card.objects.select_related("folder").prefetch_related("tags").all()
    serializer_class = CardSerializer

    def get_queryset(self):
        queryset = self.queryset
        folder_id = self.request.query_params.get("folder_id")
        query = self.request.query_params.get("q")
        sort = self.request.query_params.get("sort", "created_at_desc")
        if folder_id:
            queryset = queryset.filter(folder_id=folder_id)
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(url__icontains=query)
                | Q(summary__icontains=query)
                | Q(details__icontains=query)
                | Q(memo__icontains=query)
                | Q(tags_text__icontains=query)
            )
        sort_map = {
            "created_at_desc": ("-created_at", "-id"),
            "created_at_asc": ("created_at", "id"),
        }
        queryset = queryset.order_by(*sort_map.get(sort, sort_map["created_at_desc"]))
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        card = create_card(serializer.validated_data)
        return Response(self.get_serializer(card).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        card = update_card(instance, serializer.validated_data)
        return Response(self.get_serializer(card).data)

    @action(detail=True, methods=["get"], url_path="status")
    def status_view(self, request, pk=None):
        card = self.get_object()
        return Response(CardStatusSerializer(card).data)

    @action(detail=True, methods=["post"], url_path="retry-jobs")
    def retry_jobs(self, request, pk=None):
        card = self.get_object()
        retry_card_jobs(card)
        return Response(self.get_serializer(card).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="generate-tags")
    def generate_tags(self, request, pk=None):
        return Response(
            {
                "code": "AI_POLICY_RESTRICTED",
                "message": "AI 처리는 신규 저장 또는 새로고침에서만 수행됩니다.",
                "details": {},
            },
            status=status.HTTP_409_CONFLICT,
        )
