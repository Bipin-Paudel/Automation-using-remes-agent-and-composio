from typing import Any

from .config import SHARED_COMPOSIO_USER_ID, composio
from .sessions import get_or_create_session, normalized_tool_names

REDDIT_TOOL_SLUGS = [
    "REDDIT_CREATE_REDDIT_POST",
    "REDDIT_DELETE_REDDIT_COMMENT",
    "REDDIT_DELETE_REDDIT_POST",
    "REDDIT_EDIT_REDDIT_COMMENT_OR_POST",
    "REDDIT_GET",
    "REDDIT_GET_CONTROVERSIAL_POSTS",
    "REDDIT_GET_ME_PREFS",
    "REDDIT_GET_NEW",
    "REDDIT_GET_RANDOM",
    "REDDIT_GET_REDDIT_USER_ABOUT",
    "REDDIT_GET_R_TOP",
    "REDDIT_GET_SCOPES",
    "REDDIT_GET_SUBREDDIT_RULES",
    "REDDIT_GET_SUBREDDITS_SEARCH",
    "REDDIT_GET_USER_FLAIR",
    "REDDIT_GET_USERNAME_AVAILABLE",
    "REDDIT_LIST_SUBREDDIT_POST_FLAIRS",
    "REDDIT_POST_REDDIT_COMMENT",
    "REDDIT_RETRIEVE_POST_COMMENTS",
    "REDDIT_RETRIEVE_REDDIT_POST",
    "REDDIT_RETRIEVE_SPECIFIC_COMMENT",
    "REDDIT_SEARCH_ACROSS_SUBREDDITS",
    "REDDIT_TOGGLE_INBOX_REPLIES",
]

REDDIT_TOOL_GROUPS: list[tuple[str, list[str]]] = [
    (
        "Research and discovery",
        [
            "REDDIT_SEARCH_ACROSS_SUBREDDITS",
            "REDDIT_GET_SUBREDDITS_SEARCH",
            "REDDIT_RETRIEVE_REDDIT_POST",
            "REDDIT_GET",
            "REDDIT_GET_R_TOP",
            "REDDIT_GET_NEW",
            "REDDIT_GET_CONTROVERSIAL_POSTS",
            "REDDIT_GET_RANDOM",
        ],
    ),
    (
        "Thread and comment analysis",
        [
            "REDDIT_RETRIEVE_POST_COMMENTS",
            "REDDIT_RETRIEVE_SPECIFIC_COMMENT",
            "REDDIT_GET_REDDIT_USER_ABOUT",
            "REDDIT_GET_USER_FLAIR",
        ],
    ),
    (
        "Posting preparation and safety",
        [
            "REDDIT_GET_SUBREDDIT_RULES",
            "REDDIT_LIST_SUBREDDIT_POST_FLAIRS",
            "REDDIT_GET_USERNAME_AVAILABLE",
            "REDDIT_GET_SCOPES",
            "REDDIT_GET_ME_PREFS",
        ],
    ),
    (
        "Publishing and editing",
        [
            "REDDIT_CREATE_REDDIT_POST",
            "REDDIT_POST_REDDIT_COMMENT",
            "REDDIT_EDIT_REDDIT_COMMENT_OR_POST",
            "REDDIT_TOGGLE_INBOX_REPLIES",
        ],
    ),
    (
        "Deletion and cleanup",
        [
            "REDDIT_DELETE_REDDIT_POST",
            "REDDIT_DELETE_REDDIT_COMMENT",
        ],
    ),
]

REDDIT_DISCOVERY_QUERY = (
    "reddit search posts comments subreddits subreddit rules create post reply comment"
)

_reddit_tools_cache: dict[str, list[Any]] = {}


def resolve_composio_user_id(user_id: str) -> str:
    """Resolve the effective Composio user for direct Reddit tool access."""
    return SHARED_COMPOSIO_USER_ID or user_id


def _merge_tools(tools: list[Any]) -> list[Any]:
    """Merge provider tool objects by name while preserving order."""
    merged: list[Any] = []
    seen: set[str] = set()
    for tool in tools:
        name = (
            tool.get("name", "").strip()
            if isinstance(tool, dict)
            else str(getattr(tool, "name", "") or "").strip()
        )
        if not name or name in seen:
            continue
        merged.append(tool)
        seen.add(name)
    return merged


def get_reddit_agent_tools(user_id: str) -> list[Any]:
    """Fetch concrete Reddit tools for the agent, falling back to session meta-tools."""
    composio_user_id = resolve_composio_user_id(user_id)
    if composio_user_id in _reddit_tools_cache:
        return _reddit_tools_cache[composio_user_id]

    direct_tools: list[Any] = []

    try:
        explicit_tools = list(
            composio.tools.get(
                user_id=composio_user_id,
                tools=REDDIT_TOOL_SLUGS,
            )
            or []
        )
        search_tools = list(
            composio.tools.get(
                user_id=composio_user_id,
                search=REDDIT_DISCOVERY_QUERY,
                limit=10,
            )
            or []
        )
        direct_tools = _merge_tools(explicit_tools + search_tools)
    except Exception:
        direct_tools = []

    if direct_tools:
        _reddit_tools_cache[composio_user_id] = direct_tools
        return direct_tools

    fallback_tools = list(get_or_create_session(user_id).tools() or [])
    _reddit_tools_cache[composio_user_id] = fallback_tools
    return fallback_tools


def get_reddit_agent_tool_names(user_id: str) -> list[str]:
    """Return the concrete Reddit tool names currently available to the bot."""
    return normalized_tool_names(get_reddit_agent_tools(user_id))


def get_reddit_agent_tool_groups(user_id: str) -> list[tuple[str, list[str]]]:
    """Return available Reddit tools grouped by operational use case."""
    available = set(get_reddit_agent_tool_names(user_id))
    groups: list[tuple[str, list[str]]] = []
    for title, slugs in REDDIT_TOOL_GROUPS:
        present = [slug for slug in slugs if slug in available]
        if present:
            groups.append((title, present))
    return groups


def build_reddit_tool_capability_guide() -> str:
    """Return a concise operating guide for the Reddit toolkit."""
    return (
        "Use the Reddit tools deliberately. "
        "For broad discovery and live research, prefer REDDIT_SEARCH_ACROSS_SUBREDDITS and REDDIT_GET_SUBREDDITS_SEARCH. "
        "For a specific subreddit feed, use REDDIT_RETRIEVE_REDDIT_POST, REDDIT_GET, REDDIT_GET_R_TOP, REDDIT_GET_NEW, or REDDIT_GET_CONTROVERSIAL_POSTS depending on the request. "
        "For thread analysis, use REDDIT_RETRIEVE_POST_COMMENTS and REDDIT_RETRIEVE_SPECIFIC_COMMENT. "
        "Before recommending or publishing content in a subreddit, check REDDIT_GET_SUBREDDIT_RULES and, when posting, REDDIT_LIST_SUBREDDIT_POST_FLAIRS. "
        "Before creating, editing, deleting, or replying, show the exact planned action to the user and wait for explicit approval. "
        "When creating a post, confirm subreddit, title, kind, and body or URL. "
        "After publishing, mention the returned permalink or confirmation result if available. "
        "Use account and preference tools only when troubleshooting auth, flair, or account context. "
        "Never expose raw tool output or traces to the Slack user."
    )
