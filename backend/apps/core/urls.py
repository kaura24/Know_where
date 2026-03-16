from django.urls import path

from .views import health_check, shutdown_app

urlpatterns = [
    path("", health_check, name="health-check"),
    path("shutdown/", shutdown_app, name="shutdown-app"),
]
