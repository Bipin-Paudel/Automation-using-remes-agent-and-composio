import json
import re

from .config import ACCESS_CONTROL_FILE, ENV_ALLOWED_USERS


def load_access_control() -> dict[str, set[str]]:
    """Load dynamic Slack access control from local storage."""
    if not ACCESS_CONTROL_FILE.exists():
        return {"admins": set(), "allowed_users": set()}

    try:
        payload = json.loads(ACCESS_CONTROL_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"admins": set(), "allowed_users": set()}

    admins = {
        str(user_id).strip()
        for user_id in payload.get("admins", [])
        if str(user_id).strip()
    }
    allowed_users = {
        str(user_id).strip()
        for user_id in payload.get("allowed_users", [])
        if str(user_id).strip()
    }
    return {"admins": admins, "allowed_users": allowed_users}


def save_access_control(data: dict[str, set[str]]) -> None:
    """Persist dynamic Slack access control to local storage."""
    payload = {
        "admins": sorted(data.get("admins", set())),
        "allowed_users": sorted(data.get("allowed_users", set())),
    }
    ACCESS_CONTROL_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def get_allowed_users() -> set[str]:
    """Return the merged static and dynamic allowlist."""
    access_control = load_access_control()
    return set(ENV_ALLOWED_USERS) | set(access_control["allowed_users"])


def get_admin_users() -> set[str]:
    """Return Slack users allowed to manage access from Slack."""
    access_control = load_access_control()
    return set(access_control["admins"])


def is_allowed_user(user_id: str) -> bool:
    """Restrict use until at least one admin or allowed user has been configured."""
    allowed_users = get_allowed_users()
    admins = get_admin_users()
    if not allowed_users and not admins:
        return False
    return user_id in allowed_users


def is_access_admin(user_id: str) -> bool:
    """Return whether a Slack user can manage the dynamic allowlist."""
    return user_id in get_admin_users()


def extract_user_ids(text: str) -> list[str]:
    """Extract Slack user IDs from mentions or raw user IDs."""
    mention_ids = re.findall(r"<@([A-Z0-9]+)>", text)
    raw_ids = re.findall(r"\bU[A-Z0-9]{8,}\b", text)
    ordered: list[str] = []
    for user_id in mention_ids + raw_ids:
        if user_id not in ordered:
            ordered.append(user_id)
    return ordered
