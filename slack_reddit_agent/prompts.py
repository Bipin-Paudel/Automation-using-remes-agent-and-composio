import asyncio
import re
from typing import Any

from agents import Agent, Runner

import slack_reddit_agent.state as state

from .config import (
    DEFAULT_MODEL,
    MAX_EXPORT_ROWS,
    REDDIT_BRAND_CONTEXT,
    REDDIT_BRAND_NAME,
    REDDIT_CONTENT_GOALS,
    REDDIT_PRIORITY_SUBREDDITS,
    REDDIT_PROHIBITED_CLAIMS,
    REDDIT_TARGET_AUDIENCES,
    SLACK_CASUAL_PATTERNS,
    SLACK_CONTEXT_CHAR_LIMIT,
    SLACK_CONTEXT_MESSAGE_LIMIT,
)
from .document_access import build_document_prompt_context
from .formatting import strip_bot_mention
from .reddit_tools import build_reddit_tool_capability_guide, get_reddit_agent_tools
from .sessions import get_or_create_memory


def format_prompt_list(values: list[str], fallback: str = "not specified") -> str:
    """Format a list for prompt text."""
    return ", ".join(values) if values else fallback


def build_reddit_brand_context() -> str:
    """Build environment-driven brand context for the Reddit agent."""
    lines = [
        f"Brand name: {REDDIT_BRAND_NAME}",
        f"Primary goals: {format_prompt_list(REDDIT_CONTENT_GOALS)}",
        f"Priority subreddits: {format_prompt_list(REDDIT_PRIORITY_SUBREDDITS, 'discover based on the request')}",
        f"Target audiences: {format_prompt_list(REDDIT_TARGET_AUDIENCES, 'infer from the request')}",
    ]
    if REDDIT_BRAND_CONTEXT:
        lines.append(f"Brand context: {REDDIT_BRAND_CONTEXT}")
    if REDDIT_PROHIBITED_CLAIMS:
        lines.append(
            f"Prohibited claims or phrasing: {format_prompt_list(REDDIT_PROHIBITED_CLAIMS)}"
        )
    return "\n".join(lines)


def workflow_hint(text: str) -> tuple[str, str]:
    """Infer the likely Reddit workflow and response requirements."""
    normalized = text.lower().strip()
    has_reddit_url = bool(re.search(r"https?://(?:www\.)?reddit\.com/\S+", normalized))
    has_google_workspace_doc_url = bool(
        re.search(r"https?://docs\.google\.com/(?:spreadsheets|document)/\S+", normalized)
    )

    if has_google_workspace_doc_url or any(
        phrase in normalized
        for phrase in (
            "google sheet",
            "google sheets",
            "google doc",
            "google docs",
            "spreadsheet link",
            "document link",
            "sheet link",
            "read this sheet",
            "read this spreadsheet",
            "read this doc",
            "read this document",
            "read this file",
            "open this file",
            "summarize this sheet",
            "summarize this spreadsheet",
            "summarize this doc",
            "summarize this document",
            "summarize this file",
        )
    ):
        return (
            "document_access",
            "Handle requests to read or summarize external files and links. If a URL is publicly reachable and your tools can access it, read it and summarize the actual contents. If the data is not directly accessible in the current Slack environment, say that clearly, avoid pretending the file was read, and ask for the smallest next input needed such as pasted rows, CSV upload, or a screenshot.",
        )

    if any(re.match(pattern, normalized) for pattern in SLACK_CASUAL_PATTERNS):
        return (
            "chat_support",
            "Respond naturally and conversationally. If the user is redirecting or refining the task, adapt without forcing a research workflow.",
        )

    if any(keyword in normalized for keyword in ("excel", "xlsx", "spreadsheet", "export report")):
        return (
            "report_export",
            "Prioritize structured research and include a compact Slack summary plus the required Excel JSON block.",
        )
    if has_reddit_url or "analyze thread" in normalized or "summarize thread" in normalized:
        return (
            "thread_analysis",
            "Analyze the linked Reddit thread, summarize the current context, sentiment, objections, opportunities, and suggested next action.",
        )
    if any(keyword in normalized for keyword in ("where to post", "which subreddit", "best subreddit", "subreddit for")):
        return (
            "subreddit_selection",
            "Recommend the best subreddit options, explain why each fits, note audience fit, posting risk, and which one to prioritize first.",
        )
    if any(keyword in normalized for keyword in ("what to post", "content plan", "content calendar", "campaign plan", "post ideas")):
        return (
            "content_strategy",
            "Create a Reddit content strategy with post angles, recommended subreddits, hooks, timing guidance, and context on why the content should work now.",
        )
    if any(keyword in normalized for keyword in ("draft post", "write post", "create post")):
        return (
            "post_drafting",
            "Draft Reddit-ready post options with title, body, subreddit fit, risk checks, and any comments needed to support the post.",
        )
    if any(keyword in normalized for keyword in ("draft comment", "write comment", "reply comment", "comment draft")):
        return (
            "comment_drafting",
            "Draft concise Reddit comments or replies that match subreddit tone, avoid spam signals, and feel native to the thread.",
        )
    return (
        "research_strategy",
        "Research the topic deeply, explain what is happening now, where it belongs on Reddit, what content should be created, and the best next action.",
    )


def build_fast_chat_reply(text: str) -> str | None:
    """Return an instant local reply for simple casual Slack messages."""
    normalized = re.sub(r"\s+", " ", text.lower()).strip()

    if re.match(r"^(hi|hello|hey)\b", normalized):
        return (
            "Hello! I can help with Reddit research, document reading, drafting, and exports. "
            "Tell me what you want to work on."
        )

    if re.match(r"^thank(s| you)\b", normalized):
        return "You're welcome. If you want, send the next task and I'll keep going."

    if re.match(r"^(ok|okay|got it)\b", normalized):
        return "Sounds good. Send the next task whenever you’re ready."

    if re.match(r"^can you help\b", normalized) or re.match(r"^help me\b", normalized):
        return (
            "Yes. I can help with Reddit tasks, Google Sheets, Google Docs, text summaries, "
            "and file exports. Send the task or paste the link."
        )

    return None


def strip_engine_prefix(text: str) -> tuple[str | None, str]:
    """Detect and remove explicit engine prefixes from a Slack message."""
    normalized = text.strip()
    for engine, prefixes in (
        ("hermes", ("hermes:", "general:")),
        ("reddit", ("reddit:",)),
    ):
        for prefix in prefixes:
            if normalized.lower().startswith(prefix):
                stripped = normalized[len(prefix) :].strip()
                return engine, stripped or normalized
    return None, normalized


def _is_general_task(text: str) -> bool:
    """Infer whether a request is broader than Reddit ops and should use Hermes."""
    normalized = text.lower().strip()
    document_markers = (
        "docs.google.com/spreadsheets",
        "docs.google.com/document",
        "google sheet",
        "google sheets",
        "google doc",
        "google docs",
        "spreadsheet link",
        "document link",
        "sheet link",
        "read this sheet",
        "read this spreadsheet",
        "read this doc",
        "read this document",
        "read this file",
        "open this file",
        "summarize this doc",
        "summarize this document",
        "summarize this spreadsheet",
        "summarize this file",
    )
    reddit_markers = (
        "reddit",
        "subreddit",
        "r/",
        "thread",
        "comment",
        "post",
        "retinol",
        "niacinamide",
        "skincareaddiction",
        "analyze thread",
        "where should we post",
        "what should we post",
        "export",
        "xlsx",
        "excel",
    )
    general_markers = (
        "rewrite",
        "rephrase",
        "simplify",
        "summarize this",
        "make this clearer",
        "brainstorm",
        "strategy memo",
        "memo",
        "email",
        "proposal",
        "presentation",
        "turn this into",
    )
    if any(marker in normalized for marker in document_markers):
        return True
    return any(marker in normalized for marker in general_markers) and not any(
        marker in normalized for marker in reddit_markers
    )


def choose_response_engine(text: str) -> tuple[str, str]:
    """Choose the best engine for a Slack request and return cleaned user text."""
    explicit_engine, cleaned_text = strip_engine_prefix(text)
    if explicit_engine:
        return explicit_engine, cleaned_text

    workflow_name, _ = workflow_hint(cleaned_text)
    if workflow_name == "chat_support" or _is_general_task(cleaned_text):
        return "hermes", cleaned_text
    return "reddit", cleaned_text


def workflow_output_requirements(workflow: str) -> str:
    """Return response structure guidance for a workflow."""
    workflow_map = {
        "chat_support": (
            "Use a natural chat reply. Keep it short, helpful, and adaptive. Do not force Reddit sections unless the user is explicitly asking for Reddit work."
        ),
        "document_access": (
            "If you successfully read the file or URL, use this structure when possible: short title, *Summary*, *Key Findings*, *Next Step*. "
            "If access is blocked, use this structure when possible: short title, *What I Can Access*, *What I Need*, *Fastest Next Step*. "
            "Do not include Reddit-specific sections like subreddits, posting strategy, or content opportunities unless the user explicitly combines the file with a Reddit task."
        ),
        "report_export": (
            "Use this structure when possible: short title, *Summary*, *Current Context*, "
            "*Recommended Subreddits*, *Content Opportunities*, *Next Step*."
        ),
        "thread_analysis": (
            "Use this structure when possible: short title, *Summary*, *Current Context*, "
            "*Sentiment*, *Key Pain Points*, *Opportunity*, *Next Step*."
        ),
        "subreddit_selection": (
            "Use this structure when possible: short title, *Summary*, *Best Subreddits*, "
            "*Why These Fit*, *Posting Risks*, *Next Step*."
        ),
        "content_strategy": (
            "Use this structure when possible: short title, *Summary*, *Current Context*, "
            "*Recommended Subreddits*, *Content Plan*, *Risks*, *Next Step*."
        ),
        "post_drafting": (
            "Use this structure when possible: short title, *Goal*, *Recommended Subreddit*, "
            "*Draft Post*, *Support Comment*, *Risks*, *Next Step*."
        ),
        "comment_drafting": (
            "Use this structure when possible: short title, *Summary*, *Thread Context*, "
            "*Draft Comment*, *Why It Works*, *Risks*, *Next Step*."
        ),
    }
    return workflow_map.get(
        workflow,
        "Use this structure when possible: short title, *Summary*, *Current Context*, "
        "*Recommended Subreddits*, *Content Recommendation*, *Risks*, *Next Step*.",
    )


def build_agent(tools: list[Any]) -> Agent:
    """Create the Reddit-specific Slack agent."""
    brand_context = build_reddit_brand_context()
    tool_capability_guide = build_reddit_tool_capability_guide()
    return Agent(
        name="Slack Reddit Agent",
        instructions=(
            f"You are the dedicated Reddit Operations Agent for {REDDIT_BRAND_NAME} working inside Slack. "
            "Own the full Reddit workflow: market research, subreddit selection, content strategy, post ideation, "
            "title testing, post drafting, comment drafting, thread analysis, competitor analysis, trend analysis, "
            "and reporting. "
            "Your job is to decide what should be posted, where it should be posted, what the content should say, "
            "what the current Reddit context is, and what action should happen next. "
            "When the user asks a vague question, do not stall. Infer the most useful Reddit workflow, state assumptions briefly, and provide the best operational recommendation. "
            "Check subreddit rules before recommending posts when possible. "
            "If rules cannot be verified, say so clearly and mark the recommendation as lower confidence. "
            "If shared-account mode is enabled, all Reddit actions happen through the company's shared Reddit account, not the Slack user's personal Reddit account. "
            "Never say a Reddit action was completed unless a tool result confirms it. "
            "Ask for explicit confirmation before creating, editing, deleting, submitting, or replying to anything on Reddit. "
            "Before any execution step, show the exact subreddit, title, content, or comment you want to publish. "
            "Avoid spammy, manipulative, fake-organic, brigading, or misleading behavior. Avoid unverified medical or skincare claims. "
            "Keep responses concise, practical, and friendly for Slack. "
            "Behave like a strong consumer chat assistant too: be natural, warm, adaptive, and easy to talk to. "
            "If the user is greeting you, changing direction, asking for clarification, or speaking casually, respond like a normal assistant instead of forcing a Reddit research workflow. "
            "If the user says to stop researching or wants a simpler answer, switch modes gracefully and help with the new direction. "
            "Never expose internal tool traces, raw tool names, browser logs, navigation steps, snapshots, function-call payloads, or chain-of-thought style work logs. "
            "Users should only see polished conclusions, concise caveats, and next steps. "
            "Format every answer for official Slack Block Kit delivery using Slack mrkdwn, not GitHub Markdown. "
            "When useful, start with one short title line and then leave one blank line before the body so the app can promote that title into a Slack header block. "
            "When useful, include compact metadata lines near the top in this style: `*Subreddit:* r/example`, `*Confidence:* High`, `*Risk:* Low`, `*Status:* Draft ready`. "
            "Use short paragraphs, `*bold*`, `_italic_`, `~strike~`, backticks for inline code, triple backticks for code blocks, `-` for bullets, `1.` for numbered lists, and `<https://example.com|label>` for labeled links. "
            "Prefer Reddit-ops structures such as `*Summary*`, `*Current Context*`, `*Recommended Subreddits*`, `*Content Plan*`, `*Draft Post*`, `*Risks*`, and `*Next Step*` when they fit. "
            "Use standalone bold section labels like `*Summary*` and `*Current Context*` on their own lines so the app can render sections cleanly in Slack. "
            "Do not use Markdown headings like `# Heading`, Markdown tables, HTML, nested bullets, or attachment-style formatting. "
            "If the user wants research, explain what conversations are happening now, what the audience cares about, which subreddits matter, and what content angle is most promising. "
            "If the user wants content, provide subreddit fit, hook, title, body, supporting comments, and posting cautions. "
            "If the user wants recommendations on where to post, rank the best subreddit options with reasons and risks. "
            "If the user wants a report, summarize the findings in Slack and prepare the Excel JSON block. "
            "If the user asks for Excel, XLSX, spreadsheet, sheet, table export, or report export, "
            "end your response with one JSON code block and nothing after it. "
            "That JSON must use this exact shape: "
            '{"workbook_name":"reddit_report","sheet_name":"Report","summary":"short summary","columns":["column_a","column_b"],"rows":[{"column_a":"value","column_b":"value"}]}. '
            "Use only flat text, numbers, or booleans in rows. "
            f"Never return more than {MAX_EXPORT_ROWS} rows in that JSON block.\n\n"
            "Reddit toolkit operating guide:\n"
            f"{tool_capability_guide}\n\n"
            "Brand operating context:\n"
            f"{brand_context}"
        ),
        model=DEFAULT_MODEL,
        tools=tools,
    )


async def run_user_task(user_id: str, task: str) -> str:
    """Run a Slack user task through the Composio-backed agent."""
    memory = get_or_create_memory(user_id)
    tools = get_reddit_agent_tools(user_id)
    agent = build_agent(tools)

    result = await asyncio.to_thread(
        Runner.run_sync,
        starting_agent=agent,
        input=task,
        session=memory,
    )
    return str(result.final_output or "No response generated.")


def clip_text(value: str, limit: int) -> str:
    """Clip prompt text without breaking the request flow."""
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


async def fetch_slack_context(
    client,
    channel: str,
    timestamp: str,
    thread_ts: str | None,
    is_dm: bool,
) -> str:
    """Fetch recent Slack context so the Reddit agent can see surrounding discussion."""
    try:
        if thread_ts:
            response = await client.conversations_replies(
                channel=channel,
                ts=thread_ts,
                limit=SLACK_CONTEXT_MESSAGE_LIMIT,
            )
        else:
            response = await client.conversations_history(
                channel=channel,
                latest=timestamp,
                inclusive=True,
                limit=SLACK_CONTEXT_MESSAGE_LIMIT,
            )
    except Exception:
        return ""

    messages = response.get("messages") or []
    if not messages:
        return ""

    def ts_value(message: dict[str, Any]) -> float:
        try:
            return float(str(message.get("ts") or "0"))
        except Exception:
            return 0.0

    lines: list[str] = []
    total_length = 0
    for message in sorted(messages, key=ts_value):
        if message.get("subtype"):
            continue

        raw_text = str(message.get("text") or "").strip()
        if not raw_text:
            continue

        text = raw_text if is_dm else strip_bot_mention(raw_text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue

        author = "assistant" if (
            message.get("bot_id")
            or str(message.get("user") or "").strip() == state.BOT_USER_ID
        ) else "user"
        line = f"{author}: {text}"
        if total_length + len(line) + 1 > SLACK_CONTEXT_CHAR_LIMIT:
            break
        lines.append(line)
        total_length += len(line) + 1

    return "\n".join(lines)


async def build_reddit_task_prompt(
    client,
    channel: str,
    text: str,
    timestamp: str,
    thread_ts: str | None,
    is_dm: bool,
    *,
    document_context: str | None = None,
    original_text: str | None = None,
    routing_reason: str | None = None,
) -> str:
    """Turn a Slack message into a structured Reddit-ops request for the agent."""
    workflow_name, workflow_goal = workflow_hint(text)
    context_block = await fetch_slack_context(
        client=client,
        channel=channel,
        timestamp=timestamp,
        thread_ts=thread_ts,
        is_dm=is_dm,
    )

    prompt_parts = [
        "Handle this as a Slack conversation for a Reddit-focused AI worker.",
        f"Workflow hint: {workflow_name}",
        f"Workflow goal: {workflow_goal}",
        f"Response format requirement: {workflow_output_requirements(workflow_name)}",
    ]

    if workflow_name not in {"chat_support", "document_access"}:
        prompt_parts.append(
            "Operational priorities: identify what is happening on Reddit now, decide where content should be posted, "
            "recommend what content should be created, explain why the subreddit fit makes sense, and suggest the next action."
        )

    if routing_reason:
        prompt_parts.append(f"Hermes routing note: {routing_reason.strip()}")

    prompt_parts.extend(
        [
            f"Slack surface: {'direct message' if is_dm else 'channel mention'}",
            f"Slack context:\n{clip_text(context_block, SLACK_CONTEXT_CHAR_LIMIT) if context_block else 'No additional Slack context available.'}",
        ]
    )
    if document_context:
        prompt_parts.append(f"Fetched document context:\n{document_context}")
    prompt_parts.append(f"User request:\n{text.strip()}")
    if original_text and original_text.strip() and original_text.strip() != text.strip():
        prompt_parts.append(f"Original Slack request:\n{original_text.strip()}")
    return "\n\n".join(prompt_parts).strip()


async def build_hermes_task_prompt(
    client,
    channel: str,
    text: str,
    timestamp: str,
    thread_ts: str | None,
    is_dm: bool,
    *,
    document_context: str | None = None,
) -> str:
    """Build a general-assistant prompt for Hermes using recent Slack context."""
    context_block = await fetch_slack_context(
        client=client,
        channel=channel,
        timestamp=timestamp,
        thread_ts=thread_ts,
        is_dm=is_dm,
    )

    prompt_parts = [
        "You are the general assistant sidecar for a Slack Reddit operations bot.",
        "Help with broader reasoning, rewriting, synthesis, planning, and natural conversation.",
        "When the request is about opening a file, reading a Google Sheet, or accessing an external document, try to read the actual content if the URL is publicly reachable and the available tools support access.",
        "Do not imply that you successfully read a file or URL unless you actually obtained the content through Slack context or tool access.",
        "If fetched document contents are provided below, treat them as the real source material and answer from them directly.",
        "If direct access is unavailable because the file requires sign-in, extra permissions, or unsupported tools, say that plainly in one sentence, avoid Reddit-specific sections, and give 1 to 3 concrete next-step options such as paste rows, upload CSV, or send a screenshot with headers.",
        "If the user only wants data extraction from a file, keep the reply focused on access and the next input needed rather than drifting into broader strategy advice.",
        "If the request references earlier Slack discussion, use the context below.",
        "Keep the reply concise, practical, and suitable for Slack.",
        f"Slack context:\n{clip_text(context_block, SLACK_CONTEXT_CHAR_LIMIT) if context_block else 'No additional Slack context available.'}",
    ]
    if document_context:
        prompt_parts.append(f"Fetched document context:\n{document_context}")
    prompt_parts.append(f"User request:\n{text.strip()}")
    return "\n\n".join(prompt_parts).strip()


async def build_hermes_orchestrator_prompt(
    client,
    channel: str,
    text: str,
    timestamp: str,
    thread_ts: str | None,
    is_dm: bool,
    *,
    document_context: str | None = None,
) -> str:
    """Build a Hermes-first routing prompt that decides between direct reply and Reddit handoff."""
    context_block = await fetch_slack_context(
        client=client,
        channel=channel,
        timestamp=timestamp,
        thread_ts=thread_ts,
        is_dm=is_dm,
    )

    prompt = "\n\n".join(
        [
            "You are Hermes, the first-pass orchestrator for a Slack Reddit operations bot.",
            "Your job is to inspect every Slack message before any Reddit or Composio tools run.",
            "Choose `respond` when you can fully complete the request yourself with normal assistant skills such as chat, planning, rewriting, summarization, synthesis, or strategy explanation.",
            "Choose `reddit` when fulfilling the request requires Reddit research, subreddit discovery, live Reddit context, subreddit rules, Reddit post or comment retrieval, Reddit account-aware drafting, or any external Reddit action through Composio.",
            "If the request is ambiguous and might need live Reddit information, prefer `reddit`.",
            "If fetched document contents are provided below and the user is asking to read, summarize, or explain that document, prefer `respond` unless the user explicitly asks for Reddit research on top of it.",
            "Return JSON only. Do not add code fences, prose, or extra commentary.",
            'Use this exact schema: {"route":"respond|reddit","reason":"short reason","reply":"final Slack-ready reply when route=respond, otherwise empty string","handoff_prompt":"clear task for the Reddit/Composio engine when route=reddit, otherwise empty string"}.',
            "When route=respond, `reply` must be a polished final answer suitable for Slack and `handoff_prompt` must be an empty string.",
            "When route=reddit, `handoff_prompt` must preserve the user's real goal, include any important constraints or desired output, and must not mention internal routing, Hermes, JSON, or Composio.",
            "Do not claim that Reddit research or any Reddit action already happened unless tool results are available in the provided context.",
            f"Slack surface: {'direct message' if is_dm else 'channel mention'}",
            f"Slack context:\n{clip_text(context_block, SLACK_CONTEXT_CHAR_LIMIT) if context_block else 'No additional Slack context available.'}",
        ]
    ).strip()
    if document_context:
        prompt = f"{prompt}\n\nFetched document context:\n{document_context}"
    return f"{prompt}\n\nUser request:\n{text.strip()}".strip()


async def build_prompt_document_context(text: str) -> str:
    """Resolve prompt-ready document context for supported public URLs."""
    return await build_document_prompt_context(text)
