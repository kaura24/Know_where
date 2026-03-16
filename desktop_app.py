from __future__ import annotations

import argparse
import atexit
import ctypes
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import webview


ROOT_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = ROOT_DIR / "scripts" / ".runtime"
WINDOW_STATE_PATH = RUNTIME_DIR / "window_state.json"
WEBVIEW_STORAGE_DIR = RUNTIME_DIR / "webview"
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
BACKEND_URL = "http://127.0.0.1:8000/api/health/"
FRONTEND_URL = "http://127.0.0.1:5173"
MIN_WINDOW_SIZE = (1080, 720)


@dataclass
class WindowState:
    width: int
    height: int
    x: int | None = None
    y: int | None = None


def _creation_flags() -> int:
    flags = 0
    for flag_name in ("CREATE_NEW_PROCESS_GROUP", "DETACHED_PROCESS", "CREATE_NO_WINDOW"):
        flags |= getattr(subprocess, flag_name, 0)
    return flags


def _get_screen_size() -> tuple[int, int]:
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def _default_window_state() -> WindowState:
    screen_width, screen_height = _get_screen_size()
    width = max(MIN_WINDOW_SIZE[0], int(screen_width * 0.88))
    height = max(MIN_WINDOW_SIZE[1], int(screen_height * 0.88))
    width = min(width, screen_width - 80)
    height = min(height, screen_height - 80)
    x = max(20, int((screen_width - width) / 2))
    y = max(20, int((screen_height - height) / 2))
    return WindowState(width=width, height=height, x=x, y=y)


def _load_window_state() -> WindowState:
    default_state = _default_window_state()
    if not WINDOW_STATE_PATH.exists():
        return default_state

    try:
        data = json.loads(WINDOW_STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default_state

    screen_width, screen_height = _get_screen_size()

    raw_width = int(data.get("width", default_state.width))
    raw_height = int(data.get("height", default_state.height))
    if raw_width < MIN_WINDOW_SIZE[0] or raw_height < MIN_WINDOW_SIZE[1]:
        return default_state

    width = max(MIN_WINDOW_SIZE[0], min(raw_width, screen_width - 40))
    height = max(MIN_WINDOW_SIZE[1], min(raw_height, screen_height - 40))
    x = data.get("x", default_state.x)
    y = data.get("y", default_state.y)

    if isinstance(x, int):
        if x <= -10000:
            return default_state
        x = min(max(0, x), max(0, screen_width - width))
    else:
        x = default_state.x

    if isinstance(y, int):
        if y <= -10000:
            return default_state
        y = min(max(0, y), max(0, screen_height - height))
    else:
        y = default_state.y

    return WindowState(width=width, height=height, x=x, y=y)


def _save_window_state(state: WindowState) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    WINDOW_STATE_PATH.write_text(
        json.dumps(
            {
                "width": state.width,
                "height": state.height,
                "x": state.x,
                "y": state.y,
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )


@dataclass
class ManagedProcess:
    name: str
    command: list[str]
    cwd: Path
    process: subprocess.Popen[str] | None = None

    def start(self) -> None:
        if self.process and self.process.poll() is None:
            return
        self.process = subprocess.Popen(  # noqa: S603
            self.command,
            cwd=str(self.cwd),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            creationflags=_creation_flags(),
        )

    def stop(self) -> None:
        if not self.process or self.process.poll() is not None:
            return

        self.process.terminate()
        try:
            self.process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=3)


class ServiceManager:
    def __init__(self) -> None:
        npm_executable = shutil.which("npm.cmd") or shutil.which("npm")
        if not npm_executable:
            raise RuntimeError("npm executable was not found in PATH.")

        python_executable = sys.executable

        self.processes = [
            ManagedProcess(
                name="backend",
                command=[python_executable, "manage.py", "runserver", "127.0.0.1:8000"],
                cwd=BACKEND_DIR,
            ),
            ManagedProcess(
                name="worker",
                command=[python_executable, "manage.py", "run_worker"],
                cwd=BACKEND_DIR,
            ),
            ManagedProcess(
                name="frontend",
                command=[npm_executable, "run", "dev", "--", "--host", "127.0.0.1"],
                cwd=FRONTEND_DIR,
            ),
        ]

    def start(self) -> None:
        for process in self.processes:
            process.start()
            time.sleep(0.8)

        self._wait_for_url(BACKEND_URL, timeout=25)
        self._wait_for_url(FRONTEND_URL, timeout=30)

    def stop(self) -> None:
        for process in reversed(self.processes):
            process.stop()

    def _wait_for_url(self, url: str, timeout: int) -> None:
        deadline = time.time() + timeout
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if 200 <= response.status < 500:
                        return
            except Exception as error:  # noqa: BLE001
                last_error = error
                time.sleep(1)
        raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-start-services",
        action="store_true",
        help="Do not start backend/worker/frontend; assume they are already running.",
    )
    args = parser.parse_args()

    manager = ServiceManager()
    atexit.register(manager.stop)
    if args.no_start_services:
        manager._wait_for_url(BACKEND_URL, timeout=10)
        manager._wait_for_url(FRONTEND_URL, timeout=10)
    else:
        manager.start()
    WEBVIEW_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    initial_state = _load_window_state()
    current_state = initial_state

    window = webview.create_window(
        "Know Where",
        FRONTEND_URL,
        width=initial_state.width,
        height=initial_state.height,
        x=initial_state.x,
        y=initial_state.y,
        min_size=MIN_WINDOW_SIZE,
        confirm_close=True,
    )

    def handle_resized(width: int, height: int) -> None:
        nonlocal current_state
        current_state = WindowState(width=width, height=height, x=current_state.x, y=current_state.y)
        _save_window_state(current_state)

    def handle_moved(x: int, y: int) -> None:
        nonlocal current_state
        current_state = WindowState(width=current_state.width, height=current_state.height, x=x, y=y)
        _save_window_state(current_state)

    def handle_closed() -> None:
        _save_window_state(
            WindowState(width=window.width, height=window.height, x=window.x, y=window.y)
        )
        manager.stop()

    window.events.resized += handle_resized
    window.events.moved += handle_moved
    window.events.closed += handle_closed
    webview.start(private_mode=False, storage_path=str(WEBVIEW_STORAGE_DIR))


if __name__ == "__main__":
    main()
