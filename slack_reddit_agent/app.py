import asyncio
import os
from time import monotonic
from typing import Any

from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp

import slack_reddit_agent.state as state
from .access_control import is_allowed_user
from .commands import (
    handle_access_command,
    send_help,
    send_reddit_capabilities_help,
    send_reddit_workflow_help,
    send_tools_list,
)
from .config import (
    ALLOW_HERMES_GATEWAY_CONFLICT,
    DEFAULT_TOOLKITS,
    HERMES_ENABLED,
    SHARED_COMPOSIO_USER_ID,
    SHARED_CONNECTED_ACCOUNT_ID,
)
from .document_access import build_direct_document_reply
from .exports import create_excel_report, extract_excel_payload
from .formatting import post_chunked_message, sanitize_agent_message, strip_bot_mention, upload_excel_report
from .hermes_bridge import run_hermes_orchestrator, run_hermes_task
from .progress import (
    add_reaction,
    cycle_progress_message,
    delete_progress_message,
    post_progress_message,
    remove_reaction,
    update_progress_message,
)
from .prompts import (
    build_hermes_orchestrator_prompt,
    build_hermes_task_prompt,
    build_prompt_document_context,
    build_reddit_task_prompt,
    choose_response_engine,
    fetch_slack_context,
    run_user_task,
)
from .runtime import acquire_single_instance_lock, find_running_hermes_gateway_pids
from .sessions import validate_shared_account_config


def build_app() -> AsyncApp:
    """Create and configure the Slack Bolt app."""
    app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])

    async def process_event(event: dict[str, Any], logger, is_dm: bool) -> None:
        """Process either a DM message event or a channel app mention event."""
        if event.get("subtype") or event.get("bot_id"):
            return

        user_id = str(event.get("user") or "").strip()
        channel = str(event.get("channel") or "").strip()
        text = str(event.get("text") or "").strip()
        timestamp = str(event.get("ts") or "").strip()

        if not user_id or not channel:
            return

        thread_ts = event.get("thread_ts") or (None if is_dm else timestamp)

        if not is_dm:
            if not state.BOT_MENTION or state.BOT_MENTION not in text:
                return
            text = strip_bot_mention(text)

        normalized = text.lower().strip()
        client = app.client

        if await handle_access_command(
            client,
            channel,
            user_id,
            text,
            thread_ts,
            is_dm,
        ):
            return

        if not is_allowed_user(user_id):
            logger.info("Ignoring unauthorized Slack user: %s", user_id)
            await post_chunked_message(
                client,
                channel,
                "You are not allowed to use this bot yet. If this is the first setup, DM me `admin claim`. Otherwise ask an admin to DM me with `allowlist add <@your_name>`.",
                thread_ts,
            )
            return

        if not text:
            await post_chunked_message(
                client,
                channel,
                "Tell me what Reddit task you want help with.",
                thread_ts,
            )
            return

        if normalized in {"help", "/help"}:
            await send_help(client, channel, thread_ts)
            return

        if normalized in {"reddit help", "workflow help", "workflows", "/reddit"}:
            await send_reddit_workflow_help(client, channel, thread_ts)
            return

        if normalized in {"tools", "/tools"}:
            await send_tools_list(client, channel, user_id, thread_ts)
            return

        if normalized in {"reddit capabilities", "capabilities", "/capabilities"}:
            await send_reddit_capabilities_help(
                client,
                channel,
                user_id,
                thread_ts,
            )
            return

        await add_reaction(client, channel, timestamp, "eyes")
        progress_started_at = monotonic()
        progress_ts = await post_progress_message(
            client,
            channel,
            thread_ts,
            stage_index=0,
            started_at=progress_started_at,
            status="Thinking",
        )

        try:
            response_text = ""
            routing_reason = ""
            routed_text = text
            document_context = ""
            progress_stop_event: asyncio.Event | None = None
            progress_task: asyncio.Task | None = None

            await update_progress_message(
                client,
                channel,
                progress_ts,
                stage_index=1,
                started_at=progress_started_at,
                status="Gathering information",
            )
            slack_context = await fetch_slack_context(
                client=client,
                channel=channel,
                timestamp=timestamp,
                thread_ts=thread_ts,
                is_dm=is_dm,
            )
            response_text = await build_direct_document_reply(
                text,
                context_text=slack_context,
            )
            if not response_text:
                document_context = await build_prompt_document_context(text)
                if HERMES_ENABLED:
                    orchestration_prompt = await build_hermes_orchestrator_prompt(
                        client=client,
                        channel=channel,
                        text=text,
                        timestamp=timestamp,
                        thread_ts=thread_ts,
                        is_dm=is_dm,
                        document_context=document_context,
                    )
                else:
                    orchestration_prompt = ""

                await update_progress_message(
                    client,
                    channel,
                    progress_ts,
                    stage_index=2,
                    started_at=progress_started_at,
                    status="Consulting Hermes" if HERMES_ENABLED else "Researching",
                )
                progress_stop_event = asyncio.Event()
                progress_task = asyncio.create_task(
                    cycle_progress_message(
                        client,
                        channel,
                        progress_ts,
                        progress_started_at,
                        progress_stop_event,
                    )
                )

                if HERMES_ENABLED:
                    try:
                        hermes_decision = await run_hermes_orchestrator(orchestration_prompt)
                    except Exception as exc:
                        logger.warning(
                            "Hermes orchestration failed for Slack user %s: %s",
                            user_id,
                            exc,
                        )
                        fallback_engine, fallback_text = choose_response_engine(text)
                        if fallback_engine == "hermes":
                            fallback_prompt = await build_hermes_task_prompt(
                                client=client,
                                channel=channel,
                                text=fallback_text,
                                timestamp=timestamp,
                                thread_ts=thread_ts,
                                is_dm=is_dm,
                                document_context=document_context,
                            )
                            response_text = await run_hermes_task(fallback_prompt)
                        else:
                            routed_text = fallback_text
                            routing_reason = (
                                "Hermes orchestration failed, so the bot used the built-in Reddit fallback."
                            )
                    else:
                        routing_reason = hermes_decision.reason
                        if hermes_decision.route == "respond":
                            response_text = hermes_decision.reply
                        else:
                            routed_text = hermes_decision.handoff_prompt

            if not response_text:
                await update_progress_message(
                    client,
                    channel,
                    progress_ts,
                    stage_index=2,
                    started_at=progress_started_at,
                    status="Researching",
                )
                task_prompt = await build_reddit_task_prompt(
                    client=client,
                    channel=channel,
                    text=routed_text,
                    timestamp=timestamp,
                    thread_ts=thread_ts,
                    is_dm=is_dm,
                    document_context=document_context,
                    original_text=text,
                    routing_reason=routing_reason,
                )
                response_text = await run_user_task(user_id, task_prompt)

            if progress_stop_event and progress_task:
                progress_stop_event.set()
                await progress_task

            await update_progress_message(
                client,
                channel,
                progress_ts,
                stage_index=3,
                started_at=progress_started_at,
                status="Generating",
                detail="Formatting the final Slack reply and checking for exports.",
            )
            message_text, export_payload = extract_excel_payload(response_text)
            message_text = sanitize_agent_message(message_text)

            if message_text:
                await post_chunked_message(client, channel, message_text, thread_ts)

            if export_payload:
                await update_progress_message(
                    client,
                    channel,
                    progress_ts,
                    stage_index=3,
                    started_at=progress_started_at,
                    status="Generating",
                    detail="Preparing the Excel report and uploading it to Slack.",
                )
                file_path = create_excel_report(export_payload)
                title = str(export_payload.get("workbook_name") or "reddit_report")
                await upload_excel_report(
                    client,
                    channel,
                    file_path,
                    title=title,
                    thread_ts=thread_ts,
                )

                if not message_text:
                    await post_chunked_message(
                        client,
                        channel,
                        "Excel report created and uploaded.",
                        thread_ts,
                    )

            await delete_progress_message(client, channel, progress_ts)
            await remove_reaction(client, channel, timestamp, "eyes")
            await add_reaction(client, channel, timestamp, "white_check_mark")
        except Exception as exc:
            if "progress_stop_event" in locals() and progress_stop_event:
                progress_stop_event.set()
            if "progress_task" in locals() and progress_task:
                try:
                    await progress_task
                except Exception:
                    pass
            await delete_progress_message(client, channel, progress_ts)
            await remove_reaction(client, channel, timestamp, "eyes")
            await add_reaction(client, channel, timestamp, "x")
            await post_chunked_message(
                client,
                channel,
                f"Error: {str(exc)[:1500]}",
                thread_ts,
            )

    @app.event("message")
    async def handle_message_events(body, logger):
        event = body.get("event", {})
        channel_type = str(event.get("channel_type") or "").strip()
        if channel_type != "im":
            return

        await process_event(event, logger, is_dm=True)

    @app.event("app_mention")
    async def handle_app_mention_events(body, logger):
        event = body.get("event", {})
        await process_event(event, logger, is_dm=False)

    return app


async def main() -> None:
    """Start the Slack bot using Socket Mode."""
    validate_shared_account_config()

    slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
    slack_app_token = os.getenv("SLACK_APP_TOKEN")

    if not slack_bot_token or not slack_app_token:
        missing = [
            name
            for name, value in {
                "SLACK_BOT_TOKEN": slack_bot_token,
                "SLACK_APP_TOKEN": slack_app_token,
            }.items()
            if not value
        ]
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    if not acquire_single_instance_lock():
        raise RuntimeError(
            "Another slack_bot.py instance is already running. "
            "Stop the previous process first to avoid duplicate responses."
        )

    app = build_app()

    auth = await app.client.auth_test()
    state.BOT_USER_ID = str(auth.get("user_id") or "")
    state.BOT_MENTION = f"<@{state.BOT_USER_ID}>" if state.BOT_USER_ID else ""

    print(f"✅ Slack bot connected as {auth.get('user')}")
    print(f"✅ Reddit toolkit default: {', '.join(DEFAULT_TOOLKITS)}")
    if SHARED_COMPOSIO_USER_ID:
        print(f"✅ Shared Reddit account mode: {SHARED_COMPOSIO_USER_ID}")
        if SHARED_CONNECTED_ACCOUNT_ID:
            print(f"✅ Shared connected account: {SHARED_CONNECTED_ACCOUNT_ID}")
    else:
        print("✅ Shared Reddit account mode: disabled")
    hermes_gateway_pids = [
        pid for pid in find_running_hermes_gateway_pids() if pid != os.getpid()
    ]
    if hermes_gateway_pids:
        message = (
            "Hermes gateway is also running "
            f"({', '.join(str(pid) for pid in hermes_gateway_pids)}). "
            "This bot already uses Hermes as a sidecar, so running the Hermes Slack gateway on the same app can cause mixed replies. "
            "Stop the Hermes gateway or use a different Slack app for it. "
            "Set ALLOW_HERMES_GATEWAY_CONFLICT=true only if you intentionally want both."
        )
        if ALLOW_HERMES_GATEWAY_CONFLICT:
            print(f"⚠️ {message}")
        else:
            raise RuntimeError(message)
    print("✅ Slack bot is ready to receive DMs and @mentions")

    handler = AsyncSocketModeHandler(app, slack_app_token)
    await handler.start_async()
