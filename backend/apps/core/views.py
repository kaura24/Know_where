import logging
from pathlib import Path
import subprocess
import sys
import threading
import time

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def _run_shutdown_script(script_path: Path, working_dir: Path) -> None:
    time.sleep(0.8)
    command = [sys.executable, str(script_path)]
    try:
        subprocess.run(  # noqa: S603
            command,
            cwd=str(working_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to run shutdown script.")


@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok"})


@api_view(["POST"])
def shutdown_app(request):
    script_path = settings.BASE_DIR.parent / "scripts" / "stop_app_stack.py"

    if not script_path.exists():
        return Response(
            {"code": "SHUTDOWN_UNAVAILABLE", "message": "Shutdown script is unavailable.", "details": {}},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    shutdown_thread = threading.Thread(
        target=_run_shutdown_script,
        args=(script_path, settings.BASE_DIR.parent),
        daemon=True,
    )
    shutdown_thread.start()

    return Response({"status": "shutting_down"})
