from typing import Any

from agents import SQLiteSession

BOT_USER_ID = ""
BOT_MENTION = ""

user_sessions: dict[str, Any] = {}
memory_sessions: dict[str, SQLiteSession] = {}
