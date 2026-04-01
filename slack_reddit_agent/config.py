import os
from pathlib import Path

from composio import Composio
from composio_openai_agents import OpenAIAgentsProvider
from dotenv import load_dotenv

load_dotenv()

LOCK_FILE = ".slack_bot.lock"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")
HERMES_ENABLED = os.getenv("HERMES_ENABLED", "true").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
ALLOW_HERMES_GATEWAY_CONFLICT = os.getenv(
    "ALLOW_HERMES_GATEWAY_CONFLICT", "false"
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
HERMES_MODEL = os.getenv("HERMES_MODEL", "").strip()
HERMES_PROVIDER = os.getenv("HERMES_PROVIDER", "").strip()
HERMES_TIMEOUT_SECONDS = max(
    30,
    int(os.getenv("HERMES_TIMEOUT_SECONDS", "180").strip() or "180"),
)
REDDIT_TOOLKIT_VERSION = (
    os.getenv("COMPOSIO_TOOLKIT_VERSION_REDDIT", "20260316_00").strip()
    or "20260316_00"
)
DEFAULT_TOOLKITS = [
    toolkit.strip()
    for toolkit in os.getenv("COMPOSIO_TOOLKITS", "reddit").split(",")
    if toolkit.strip()
]
SHARED_COMPOSIO_USER_ID = os.getenv("COMPOSIO_SHARED_USER_ID", "").strip()
SHARED_CONNECTED_ACCOUNT_ID = os.getenv(
    "COMPOSIO_SHARED_CONNECTED_ACCOUNT_ID", ""
).strip()
ENV_ALLOWED_USERS = {
    user_id.strip()
    for user_id in os.getenv("SLACK_ALLOWED_USERS", "").split(",")
    if user_id.strip()
}
SLACK_MESSAGE_LIMIT = 3500
SLACK_BLOCK_TEXT_LIMIT = 2900
SLACK_HEADER_TEXT_LIMIT = 150
SLACK_CONTEXT_MESSAGE_LIMIT = 8
SLACK_CONTEXT_CHAR_LIMIT = 3000
SLACK_CONTEXT_ELEMENTS_LIMIT = 8
SLACK_PROGRESS_UPDATE_SECONDS = 2
SLACK_PROGRESS_STAGE_HOLD_SECONDS = 6
MAX_EXPORT_ROWS = 200
EXPORTS_DIR = Path("exports")
ACCESS_CONTROL_FILE = Path(".slack_access_control.json")
REDDIT_BRAND_NAME = os.getenv("REDDIT_BRAND_NAME", "SkinPal").strip() or "SkinPal"
REDDIT_BRAND_CONTEXT = os.getenv("REDDIT_BRAND_CONTEXT", "").strip()
REDDIT_CONTENT_GOALS = [
    value.strip()
    for value in os.getenv(
        "REDDIT_CONTENT_GOALS",
        "audience research, subreddit discovery, post strategy, content creation, comment drafting, reporting",
    ).split(",")
    if value.strip()
]
REDDIT_PRIORITY_SUBREDDITS = [
    value.strip()
    for value in os.getenv("REDDIT_PRIORITY_SUBREDDITS", "").split(",")
    if value.strip()
]
REDDIT_TARGET_AUDIENCES = [
    value.strip()
    for value in os.getenv("REDDIT_TARGET_AUDIENCES", "").split(",")
    if value.strip()
]
REDDIT_PROHIBITED_CLAIMS = [
    value.strip()
    for value in os.getenv("REDDIT_PROHIBITED_CLAIMS", "").split(",")
    if value.strip()
]

composio = Composio(
    provider=OpenAIAgentsProvider(),
    toolkit_versions={"reddit": REDDIT_TOOLKIT_VERSION},
)

SLACK_METADATA_LABELS = (
    "subreddit",
    "confidence",
    "risk",
    "status",
    "workflow",
    "timeframe",
    "goal",
)
SLACK_PROGRESS_STAGES = (
    (
        "Thinking",
        "Understanding the Reddit task and picking the best workflow.",
    ),
    (
        "Gathering information",
        "Collecting Slack context and preparing the Reddit research path.",
    ),
    (
        "Researching",
        "Running the Reddit workflow and gathering useful signals.",
    ),
    (
        "Generating",
        "Writing the Slack response and preparing any deliverables.",
    ),
)
SLACK_CASUAL_PATTERNS = (
    r"^hi\b",
    r"^hello\b",
    r"^hey\b",
    r"^thanks?\b",
    r"^thank you\b",
    r"^ok\b",
    r"^okay\b",
    r"^got it\b",
    r"^can you help\b",
    r"^help me\b",
    r"^no more research\b",
    r"^stop\b",
    r"^continue\b",
)
