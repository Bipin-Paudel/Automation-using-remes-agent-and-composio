import atexit
import os
import subprocess

from .config import LOCK_FILE


def is_process_running(pid: int) -> bool:
    """Check whether a process ID exists without killing it."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_single_instance_lock() -> bool:
    """Ensure only one slack_bot.py process is active."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r", encoding="utf-8") as file_obj:
                existing_pid = int(file_obj.read().strip())
            if is_process_running(existing_pid):
                return False
        except Exception:
            pass

    with open(LOCK_FILE, "w", encoding="utf-8") as file_obj:
        file_obj.write(str(os.getpid()))

    def cleanup_lock() -> None:
        try:
            if os.path.exists(LOCK_FILE):
                with open(LOCK_FILE, "r", encoding="utf-8") as file_obj:
                    pid_in_file = file_obj.read().strip()
                if pid_in_file == str(os.getpid()):
                    os.remove(LOCK_FILE)
        except Exception:
            pass

    atexit.register(cleanup_lock)
    return True


def find_running_hermes_gateway_pids() -> list[int]:
    """Return running Hermes gateway PIDs when detectable on this machine."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "hermes_cli.main gateway run"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return []

    pids: list[int] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.isdigit():
            pids.append(int(stripped))
    return pids
