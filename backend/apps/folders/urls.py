from rest_framework.routers import DefaultRouter

from .views import FolderViewSet

router = DefaultRouter()
router.register("", FolderViewSet, basename="folders")

urlpatterns = router.urls
