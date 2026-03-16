from __future__ import annotations

import os
import platform
import signal
import subprocess
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"
RUNTIME_DIR = SCRIPTS_DIR / ".runtime"
TRACKED_NAMES = ("desktop_app", "frontend", "worker", "backend")
TRACKED_PORTS = (5173, 8000)


def _run_windows_stop() -> int:
    pwsh_path = Path(r"C:\Program Files\PowerShell\7\pwsh.exe")
    stop_script = SCRIPTS_DIR / "stop_app_stack.ps1"
    if not pwsh_path.exists() or not stop_script.exists():
        print("Windows stop script is unavailable.")
        return 1
    command = [
        str(pwsh_path),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(stop_script),
    ]
    return subprocess.run(command, cwd=str(ROOT_DIR), check=False).returncode  # noqa: S603


def _is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _terminate_pid(pid: int) -> None:
    if not _is_pid_running(pid):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    deadline = time.time() + 5
    while time.time() < deadline:
        if not _is_pid_running(pid):
            return
        time.sleep(0.2)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        return


def _stop_tracked_pid_files() -> None:
    if not RUNTIME_DIR.exists():
        return
    for name in TRACKED_NAMES:
        pid_path = RUNTIME_DIR / f"{name}.pid"
        if not pid_path.exists():
            continue
        raw = pid_path.read_text(encoding="utf-8").strip()
        if raw.isdigit():
            _terminate_pid(int(raw))
        pid_path.unlink(missing_ok=True)


def _kill_port_listeners() -> None:
    for port in TRACKED_PORTS:
        result = subprocess.run(  # noqa: S603
            ["lsof", "-ti", f"tcp:{port}"],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in result.stdout.splitlines():
            raw = line.strip()
            if raw.isdigit():
                _terminate_pid(int(raw))


def _pkill_patterns() -> None:
    patterns = [
        "desktop_app.py",
        "manage.py run_worker",
        "manage.py runserver 127.0.0.1:8000",
        "npm run dev -- --host 127.0.0.1",
    ]
    for pattern in patterns:
        subprocess.run(["pkill", "-f", pattern], check=False)  # noqa: S603


def _run_non_windows_stop() -> int:
    _stop_tracked_pid_files()
    _kill_port_listeners()
    _pkill_patterns()
    return 0


def main() -> int:
    system = platform.system().lower()
    if system == "windows":
        return _run_windows_stop()
    return _run_non_windows_stop()


if __name__ == "__main__":
    raise SystemExit(main())
