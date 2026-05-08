import asyncio
from time import monotonic

from .config import (
    SLACK_PROGRESS_MIN_VISIBLE_SECONDS,
    SLACK_PROGRESS_STAGE_HOLD_SECONDS,
    SLACK_PROGRESS_STAGES,
    SLACK_PROGRESS_UPDATE_SECONDS,
)


def progress_status_label(
    status: str,
    stage_title: str,
    *,
    complete: bool = False,
    failed: bool = False,
) -> str:
    """Return a human-friendly short progress label for Slack."""
    if complete:
        return "Complete"
    if failed:
        return "Failed"
    if status:
        return status
    return stage_title


def build_progress_text(
    stage_index: int,
    started_at: float,
    *,
    status: str = "Working",
    detail: str | None = None,
    complete: bool = False,
    failed: bool = False,
    tick: int = 0,
) -> str:
    """Build a lightweight text-only progress message."""
    safe_index = min(max(stage_index, 0), len(SLACK_PROGRESS_STAGES) - 1)
    stage_title, _default_detail = SLACK_PROGRESS_STAGES[safe_index]
    short_status = progress_status_label(
        status,
        stage_title,
        complete=complete,
        failed=failed,
    )
    elapsed = max(0, int(monotonic() - started_at))
    elapsed_suffix = f" {elapsed}s" if elapsed >= 2 else ""
    dots = "." * ((tick % 3) + 1)

    if complete:
        return "_Done._"
    if failed:
        return "_Failed._"
    return f"_{short_status}{dots}{elapsed_suffix}_"


async def post_progress_message(
    client,
    channel: str,
    thread_ts: str | None,
    *,
    stage_index: int,
    started_at: float,
    status: str = "Working",
    detail: str | None = None,
) -> str | None:
    """Post the live progress message and return its timestamp."""
    text = build_progress_text(
        stage_index,
        started_at,
        status=status,
        detail=detail,
        tick=0,
    )
    payload: dict[str, str] = {
        "channel": channel,
        "text": text,
    }
    if thread_ts:
        payload["thread_ts"] = thread_ts

    try:
        response = await client.chat_postMessage(**payload)
    except Exception:
        return None

    return str(response.get("ts") or "") or None


async def update_progress_message(
    client,
    channel: str,
    progress_ts: str | None,
    *,
    stage_index: int,
    started_at: float,
    status: str = "Working",
    detail: str | None = None,
    complete: bool = False,
    failed: bool = False,
    tick: int = 0,
) -> None:
    """Update the live progress message if it exists."""
    if not progress_ts:
        return

    text = build_progress_text(
        stage_index,
        started_at,
        status=status,
        detail=detail,
        complete=complete,
        failed=failed,
        tick=tick,
    )
    try:
        await client.chat_update(
            channel=channel,
            ts=progress_ts,
            text=text,
        )
    except Exception:
        return


async def delete_progress_message(
    client,
    channel: str,
    progress_ts: str | None,
) -> None:
    """Delete the temporary progress message once the final reply is ready."""
    if not progress_ts:
        return
    try:
        await client.chat_delete(channel=channel, ts=progress_ts)
    except Exception:
        return


async def ensure_progress_visibility(
    started_at: float,
    *,
    minimum_seconds: int = SLACK_PROGRESS_MIN_VISIBLE_SECONDS,
) -> None:
    """Keep the temporary progress message visible long enough to be noticed."""
    remaining = float(minimum_seconds) - (monotonic() - started_at)
    if remaining > 0:
        await asyncio.sleep(remaining)


async def cycle_progress_message(
    client,
    channel: str,
    progress_ts: str | None,
    started_at: float,
    stop_event,
) -> None:
    """Keep the progress message feeling alive during long tool execution."""
    if not progress_ts:
        return

    stage_index = 2
    tick = 0
    stage_started_at = monotonic()
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=SLACK_PROGRESS_UPDATE_SECONDS,
            )
            break
        except asyncio.TimeoutError:
            tick += 1
            if monotonic() - stage_started_at >= SLACK_PROGRESS_STAGE_HOLD_SECONDS:
                stage_index = min(stage_index + 1, len(SLACK_PROGRESS_STAGES) - 1)
                stage_started_at = monotonic()
            await update_progress_message(
                client,
                channel,
                progress_ts,
                stage_index=stage_index,
                started_at=started_at,
                status=SLACK_PROGRESS_STAGES[stage_index][0],
                tick=tick,
            )


async def add_reaction(client, channel: str, timestamp: str, name: str) -> None:
    """Add a reaction without failing the request flow."""
    try:
        await client.reactions_add(channel=channel, timestamp=timestamp, name=name)
    except Exception:
        pass


async def remove_reaction(client, channel: str, timestamp: str, name: str) -> None:
    """Remove a reaction without failing the request flow."""
    try:
        await client.reactions_remove(channel=channel, timestamp=timestamp, name=name)
    except Exception:
        pass
