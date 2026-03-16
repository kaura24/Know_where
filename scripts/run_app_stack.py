from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"
RUNTIME_DIR = SCRIPTS_DIR / ".runtime"
DESKTOP_PID_PATH = RUNTIME_DIR / "desktop_app.pid"


def _is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _run_windows_stack() -> int:
    pwsh_path = Path(r"C:\Program Files\PowerShell\7\pwsh.exe")
    stack_script = SCRIPTS_DIR / "run_app_stack.ps1"
    if not pwsh_path.exists() or not stack_script.exists():
        print("Windows stack script is unavailable.")
        return 1
    command = [
        str(pwsh_path),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(stack_script),
    ]
    return subprocess.run(command, cwd=str(ROOT_DIR), check=False).returncode  # noqa: S603


def _run_non_windows_stack() -> int:
    desktop_app_path = ROOT_DIR / "desktop_app.py"
    if not desktop_app_path.exists():
        print("desktop_app.py is unavailable.")
        return 1

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    if DESKTOP_PID_PATH.exists():
        raw = DESKTOP_PID_PATH.read_text(encoding="utf-8").strip()
        if raw.isdigit() and _is_process_running(int(raw)):
            print(f"desktop_app already running: pid={raw}")
            return 0
        DESKTOP_PID_PATH.unlink(missing_ok=True)

    command = [sys.executable, str(desktop_app_path)]
    process = subprocess.Popen(  # noqa: S603
        command,
        cwd=str(ROOT_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    DESKTOP_PID_PATH.write_text(str(process.pid), encoding="utf-8")
    print(f"desktop_app started: pid={process.pid}")
    return 0


def main() -> int:
    system = platform.system().lower()
    if system == "windows":
        return _run_windows_stack()
    return _run_non_windows_stack()


if __name__ == "__main__":
    raise SystemExit(main())
