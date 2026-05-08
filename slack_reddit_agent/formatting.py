import re
from pathlib import Path
from typing import Any

import slack_reddit_agent.state as state

from .config import (
    SLACK_BLOCK_TEXT_LIMIT,
    SLACK_CONTEXT_ELEMENTS_LIMIT,
    SLACK_HEADER_TEXT_LIMIT,
    SLACK_MESSAGE_LIMIT,
    SLACK_METADATA_LABELS,
)


def strip_bot_mention(text: str) -> str:
    """Remove the bot mention from a Slack message."""
    if not state.BOT_USER_ID:
        return text.strip()
    pattern = rf"<@{re.escape(state.BOT_USER_ID)}>"
    return re.sub(pattern, "", text).strip()


def sanitize_agent_message(text: str) -> str:
    """Remove raw tool traces and other internal run artifacts before posting to Slack."""
    if not text.strip():
        return ""

    tool_trace_patterns = (
        r"^\s*(?::[a-z0-9_+-]+:\s*)?(?:[^\w\s]+\s*)?browser_[a-z0-9_]+.*$",
        r"^\s*(?::[a-z0-9_+-]+:\s*)?(?:[^\w\s]+\s*)?(?:tool|function|observation|action|result|skills)_[a-z0-9_]+.*$",
        r"^\s*(?::[a-z0-9_+-]+:\s*)?(?:[^\w\s]+\s*)?(?:browser navigate|browser snapshot|tool call|function call|skills list)\b.*$",
        r"^\s*[^\w\s]?\s*[A-Za-z0-9_]+\s*:\s*\"https?://[^\"]+\"\s*$",
    )

    cleaned_lines: list[str] = []
    in_code_block = False

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            cleaned_lines.append(raw_line)
            continue

        if not in_code_block and any(
            re.match(pattern, stripped, re.IGNORECASE)
            for pattern in tool_trace_patterns
        ):
            continue

        if not in_code_block and stripped in {"(edited)", "edited"}:
            continue

        cleaned_lines.append(raw_line)

    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def normalize_markdown_for_slack(text: str) -> str:
    """Convert common Markdown patterns into Slack-friendly mrkdwn."""
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return ""

    normalized = re.sub(
        r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
        r"<\2|\1>",
        normalized,
    )
    normalized = re.sub(r"```[A-Za-z0-9_+-]+\n", "```\n", normalized)
    normalized = re.sub(r"(?m)^#{1,6}\s+(.+)$", r"*\1*", normalized)
    normalized = re.sub(r"(?<!\*)\*\*(.+?)\*\*(?!\*)", r"*\1*", normalized)
    normalized = re.sub(r"(?<!_)__(.+?)__(?!_)", r"*\1*", normalized)
    normalized = re.sub(r"~~(.+?)~~", r"~\1~", normalized)
    normalized = re.sub(r"(?m)^\s*[*+]\s+", "- ", normalized)
    normalized = re.sub(r"(?m)^(\s*)(\d+)\)\s+", r"\1\2. ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def clean_slack_header_text(line: str) -> str:
    """Strip lightweight Slack formatting so a title fits a header block."""
    header = line.strip()
    for pattern, replacement in (
        (r"^\*(.+)\*$", r"\1"),
        (r"^_(.+)_$", r"\1"),
        (r"^~(.+)~$", r"\1"),
        (r"^`(.+)`$", r"\1"),
    ):
        header = re.sub(pattern, replacement, header)
    header = re.sub(r"\s+", " ", header).strip()
    return header[:SLACK_HEADER_TEXT_LIMIT].strip()


def extract_slack_header_and_body(text: str) -> tuple[str | None, str]:
    """Promote a short first-line title into a Slack header block when possible."""
    lines = text.splitlines()
    if len(lines) < 3:
        return None, text

    title_line = lines[0].strip()
    if not title_line or lines[1].strip():
        return None, text

    if title_line.startswith(("```", "> ", "- ", "* ", "+ ")):
        return None, text

    if re.match(r"^\d+[.)]\s+", title_line):
        return None, text

    header_text = clean_slack_header_text(title_line)
    if not header_text or len(header_text) > SLACK_HEADER_TEXT_LIMIT:
        return None, text

    body = "\n".join(lines[2:]).strip()
    if not body:
        return None, text

    return header_text, body


def extract_slack_context_metadata(text: str) -> tuple[list[str], str]:
    """Extract compact metadata lines that render well in a Slack context block."""
    metadata_lines: list[str] = []
    body_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = re.match(
            r"^\*?([A-Za-z][A-Za-z ]{1,20})\*?:\s+(.+)$",
            line,
        )
        if not match:
            body_lines.append(raw_line)
            continue

        label = match.group(1).strip().lower()
        value = match.group(2).strip()
        if label not in SLACK_METADATA_LABELS or not value:
            body_lines.append(raw_line)
            continue

        pretty_label = match.group(1).strip().title()
        metadata_lines.append(f"*{pretty_label}:* {value}")

    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()

    return metadata_lines[:SLACK_CONTEXT_ELEMENTS_LIMIT], "\n".join(body_lines).strip()


def split_slack_paragraphs(text: str) -> list[str]:
    """Split Slack mrkdwn text into paragraphs without breaking fenced code blocks."""
    paragraphs: list[str] = []
    current_lines: list[str] = []
    in_code_block = False

    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            current_lines.append(line)
            continue

        if not in_code_block and not line.strip():
            paragraph = "\n".join(current_lines).strip()
            if paragraph:
                paragraphs.append(paragraph)
            current_lines = []
            continue

        current_lines.append(line)

    paragraph = "\n".join(current_lines).strip()
    if paragraph:
        paragraphs.append(paragraph)
    return paragraphs


def is_standalone_slack_section_label(paragraph: str) -> bool:
    """Return whether a paragraph is a Slack-style section label."""
    return bool(re.fullmatch(r"\*[^\n*][^\n]*\*", paragraph.strip()))


def build_slack_sections(text: str) -> list[str]:
    """Group text into section-sized chunks for Block Kit rendering."""
    paragraphs = split_slack_paragraphs(text)
    sections: list[str] = []
    index = 0

    while index < len(paragraphs):
        current = paragraphs[index].strip()
        if is_standalone_slack_section_label(current) and index + 1 < len(paragraphs):
            sections.append(f"{current}\n{paragraphs[index + 1].strip()}")
            index += 2
            continue

        sections.append(current)
        index += 1

    return [section for section in sections if section.strip()]


def split_slack_chunks(text: str, limit: int) -> list[str]:
    """Split text into Slack-safe chunks without shredding line structure."""
    if not text.strip():
        return ["No response generated."]

    chunks: list[str] = []
    current_lines: list[str] = []
    current_length = 0

    for line in text.split("\n"):
        line_length = len(line)
        separator = 0 if not current_lines else 1

        if current_lines and current_length + separator + line_length > limit:
            chunks.append("\n".join(current_lines).strip())
            current_lines = []
            current_length = 0

        if line_length <= limit:
            current_lines.append(line)
            current_length += (0 if len(current_lines) == 1 else 1) + line_length
            continue

        if current_lines:
            chunks.append("\n".join(current_lines).strip())
            current_lines = []
            current_length = 0

        start = 0
        while start < line_length:
            chunks.append(line[start : start + limit].strip())
            start += limit

    if current_lines:
        chunks.append("\n".join(current_lines).strip())

    return [chunk for chunk in chunks if chunk] or ["No response generated."]


def chunk_slack_sections(sections: list[str], limit: int) -> list[list[str]]:
    """Pack section blocks into message-sized chunks."""
    if not sections:
        return [[]]

    message_chunks: list[list[str]] = []
    current_group: list[str] = []
    current_length = 0

    for section in sections:
        normalized_section = section.strip()
        if not normalized_section:
            continue

        split_sections = (
            split_slack_chunks(normalized_section, limit)
            if len(normalized_section) > limit
            else [normalized_section]
        )

        for item in split_sections:
            separator = 2 if current_group else 0
            if current_group and current_length + separator + len(item) > limit:
                message_chunks.append(current_group)
                current_group = []
                current_length = 0
                separator = 0

            current_group.append(item)
            current_length += separator + len(item)

    if current_group:
        message_chunks.append(current_group)

    return message_chunks or [[]]


async def post_chunked_message(
    client,
    channel: str,
    text: str,
    thread_ts: str | None = None,
) -> None:
    """Post Slack-safe chunks to a channel or thread."""
    formatted_text = normalize_markdown_for_slack(text)
    header_text, body_text = extract_slack_header_and_body(formatted_text)
    metadata_lines, render_text = extract_slack_context_metadata(body_text or formatted_text)
    sections = build_slack_sections(render_text)
    chunks = chunk_slack_sections(sections, SLACK_BLOCK_TEXT_LIMIT)

    for index, section_group in enumerate(chunks):
        blocks: list[dict[str, Any]] = []
        fallback_parts: list[str] = []

        if index == 0 and header_text:
            blocks.append(
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": header_text,
                        "emoji": True,
                    },
                }
            )
            fallback_parts.append(header_text)

        if index == 0 and metadata_lines:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": line,
                        }
                        for line in metadata_lines
                    ],
                }
            )
            fallback_parts.extend(metadata_lines)

        if blocks and section_group:
            blocks.append({"type": "divider"})

        for section_index, section_text in enumerate(section_group):
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": section_text,
                        "verbatim": True,
                    },
                }
            )
            fallback_parts.append(section_text)

            if section_index < len(section_group) - 1:
                blocks.append({"type": "divider"})

        payload = {
            "channel": channel,
            "text": "\n\n".join(part for part in fallback_parts if part)[:SLACK_MESSAGE_LIMIT],
            "blocks": blocks,
        }
        if thread_ts:
            payload["thread_ts"] = thread_ts
        await client.chat_postMessage(**payload)


async def upload_generated_file(
    client,
    channel: str,
    file_path: Path,
    title: str,
    thread_ts: str | None = None,
) -> None:
    """Upload a generated file into Slack."""
    payload: dict[str, Any] = {
        "channel": channel,
        "file": str(file_path),
        "filename": file_path.name,
        "title": title,
    }
    if thread_ts:
        payload["thread_ts"] = thread_ts

    await client.files_upload_v2(**payload)


async def upload_excel_report(
    client,
    channel: str,
    file_path: Path,
    title: str,
    thread_ts: str | None = None,
) -> None:
    """Backward-compatible wrapper for Excel uploads."""
    await upload_generated_file(client, channel, file_path, title, thread_ts)
