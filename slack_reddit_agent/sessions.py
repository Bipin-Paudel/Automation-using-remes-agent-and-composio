import re
from typing import Any

from agents import SQLiteSession

from .config import (
    DEFAULT_TOOLKITS,
    SHARED_COMPOSIO_USER_ID,
    SHARED_CONNECTED_ACCOUNT_ID,
    composio,
)
from .state import memory_sessions, user_sessions


def tool_name(tool: Any) -> str:
    """Return tool name for both object-style and dict-style tool payloads."""
    if isinstance(tool, dict):
        return str(tool.get("name") or "").strip()
    return str(getattr(tool, "name", "") or "").strip()


def normalized_tool_names(tools: list[Any]) -> list[str]:
    """Collect tool names and filter out missing or empty entries."""
    return [name for name in (tool_name(tool) for tool in tools) if name]


def get_or_create_session(user_id: str):
    """Create a Composio session for a Slack user or a shared service account."""
    composio_user_id = SHARED_COMPOSIO_USER_ID or user_id
    cache_key = f"{composio_user_id}:{SHARED_CONNECTED_ACCOUNT_ID}"

    if cache_key not in user_sessions:
        create_kwargs: dict[str, Any] = {
            "user_id": composio_user_id,
            "toolkits": DEFAULT_TOOLKITS,
        }
        if SHARED_CONNECTED_ACCOUNT_ID:
            create_kwargs["connected_accounts"] = {
                "reddit": SHARED_CONNECTED_ACCOUNT_ID
            }
        user_sessions[cache_key] = composio.create(**create_kwargs)
    return user_sessions[cache_key]


def get_or_create_memory(user_id: str) -> SQLiteSession:
    """Get or create per-user conversation memory."""
    if user_id not in memory_sessions:
        memory_sessions[user_id] = SQLiteSession(f"slack_{user_id}")
    return memory_sessions[user_id]


def validate_shared_account_config() -> None:
    """Fail fast on common shared-account configuration mistakes."""
    if SHARED_CONNECTED_ACCOUNT_ID and not SHARED_COMPOSIO_USER_ID:
        raise RuntimeError(
            "COMPOSIO_SHARED_CONNECTED_ACCOUNT_ID is set, but COMPOSIO_SHARED_USER_ID is missing. "
            "Set both for shared Reddit account mode, or remove COMPOSIO_SHARED_CONNECTED_ACCOUNT_ID."
        )

    if re.fullmatch(r"U[A-Z0-9]{8,}", SHARED_CONNECTED_ACCOUNT_ID):
        raise RuntimeError(
            "COMPOSIO_SHARED_CONNECTED_ACCOUNT_ID looks like a Slack user ID. "
            "Use a Composio connected account ID for Reddit instead, or remove this variable if your shared Composio user has only one Reddit connection."
        )
