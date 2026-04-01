from .access_control import (
    extract_user_ids,
    get_admin_users,
    load_access_control,
    save_access_control,
)
from .config import ENV_ALLOWED_USERS
from .formatting import post_chunked_message
from .reddit_tools import (
    build_reddit_tool_capability_guide,
    get_reddit_agent_tool_groups,
    get_reddit_agent_tool_names,
)


async def send_access_help(
    client,
    channel: str,
    thread_ts: str | None = None,
) -> None:
    """Explain how to manage the Slack allowlist dynamically."""
    help_text = (
        "*Slack Access Commands*\n"
        "Use these commands in a DM with the bot:\n"
        "- `admin claim` to become the first access admin\n"
        "- `admin list` to see current access admins\n"
        "- `admin add <@user>` to add another admin\n"
        "- `admin remove <@user>` to remove an admin\n"
        "- `allowlist list` to see allowed users\n"
        "- `allowlist add <@user>` to allow a user\n"
        "- `allowlist remove <@user>` to remove a user\n"
        "If `.env` still contains `SLACK_ALLOWED_USERS`, those users remain allowed too."
    )
    await post_chunked_message(client, channel, help_text, thread_ts)


async def handle_access_command(
    client,
    channel: str,
    user_id: str,
    text: str,
    thread_ts: str | None,
    is_dm: bool,
) -> bool:
    """Handle admin and allowlist commands sent from Slack."""
    command_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(command_lines) > 1 and all(
        line.lower().startswith(("admin", "allowlist", "access"))
        for line in command_lines
    ):
        for line in command_lines:
            await handle_access_command(
                client,
                channel,
                user_id,
                line,
                thread_ts,
                is_dm,
            )
        return True

    normalized = text.lower().strip()
    reply_thread_ts = None if is_dm else thread_ts
    if not normalized.startswith(("admin", "allowlist", "access")):
        return False

    if not is_dm:
        await post_chunked_message(
            client,
            channel,
            "Manage access in a DM with me so user permissions stay private.",
            reply_thread_ts,
        )
        return True

    if normalized in {"access", "access help", "allowlist help", "admin help"}:
        await send_access_help(client, channel, reply_thread_ts)
        return True

    access_control = load_access_control()
    admins = set(access_control["admins"])
    allowed_users = set(access_control["allowed_users"])
    tokens = text.strip().split()

    if normalized == "admin claim":
        if admins:
            await post_chunked_message(
                client,
                channel,
                "An access admin already exists. Ask a current admin to add you with `admin add <@user>`.",
                reply_thread_ts,
            )
            return True

        admins.add(user_id)
        allowed_users.add(user_id)
        save_access_control({"admins": admins, "allowed_users": allowed_users})
        await post_chunked_message(
            client,
            channel,
            "You are now the first Slack access admin. You have also been added to the allowlist.",
            reply_thread_ts,
        )
        return True

    if normalized == "admin list":
        admin_text = ", ".join(f"<@{admin_id}>" for admin_id in sorted(admins)) or "No Slack admins yet."
        await post_chunked_message(
            client,
            channel,
            f"*Slack Access Admins*\n{admin_text}",
            reply_thread_ts,
        )
        return True

    if normalized == "allowlist list":
        dynamic_text = ", ".join(f"<@{member_id}>" for member_id in sorted(allowed_users))
        env_text = ", ".join(f"`{member_id}`" for member_id in sorted(ENV_ALLOWED_USERS))
        parts = ["*Allowed Slack Users*"]
        parts.append(f"Dynamic: {dynamic_text or 'none'}")
        if ENV_ALLOWED_USERS:
            parts.append(f".env fallback: {env_text}")
        await post_chunked_message(
            client,
            channel,
            "\n".join(parts),
            reply_thread_ts,
        )
        return True

    if user_id not in admins:
        await post_chunked_message(
            client,
            channel,
            "Only Slack access admins can manage allowed users. If this is a new setup, send `admin claim` first.",
            reply_thread_ts,
        )
        return True

    target_ids = extract_user_ids(text)
    if len(tokens) >= 3 and tokens[0].lower() == "admin" and tokens[1].lower() == "add":
        if not target_ids:
            await post_chunked_message(
                client,
                channel,
                "Use `admin add <@user>`.",
                reply_thread_ts,
            )
            return True

        admins.update(target_ids)
        allowed_users.update(target_ids)
        save_access_control({"admins": admins, "allowed_users": allowed_users})
        await post_chunked_message(
            client,
            channel,
            f"Added admin access for {', '.join(f'<@{target_id}>' for target_id in target_ids)}.",
            reply_thread_ts,
        )
        return True

    if len(tokens) >= 3 and tokens[0].lower() == "admin" and tokens[1].lower() == "remove":
        if not target_ids:
            await post_chunked_message(
                client,
                channel,
                "Use `admin remove <@user>`.",
                reply_thread_ts,
            )
            return True

        remaining_admins = admins - set(target_ids)
        if not remaining_admins:
            await post_chunked_message(
                client,
                channel,
                "You must keep at least one Slack access admin.",
                reply_thread_ts,
            )
            return True

        admins = remaining_admins
        save_access_control({"admins": admins, "allowed_users": allowed_users})
        await post_chunked_message(
            client,
            channel,
            f"Removed admin access for {', '.join(f'<@{target_id}>' for target_id in target_ids)}.",
            reply_thread_ts,
        )
        return True

    if len(tokens) >= 3 and tokens[0].lower() == "allowlist" and tokens[1].lower() == "add":
        if not target_ids:
            await post_chunked_message(
                client,
                channel,
                "Use `allowlist add <@user>`.",
                reply_thread_ts,
            )
            return True

        allowed_users.update(target_ids)
        save_access_control({"admins": admins, "allowed_users": allowed_users})
        await post_chunked_message(
            client,
            channel,
            f"Allowed {', '.join(f'<@{target_id}>' for target_id in target_ids)} to use the bot.",
            reply_thread_ts,
        )
        return True

    if len(tokens) >= 3 and tokens[0].lower() == "allowlist" and tokens[1].lower() == "remove":
        if not target_ids:
            await post_chunked_message(
                client,
                channel,
                "Use `allowlist remove <@user>`.",
                reply_thread_ts,
            )
            return True

        allowed_users.difference_update(target_ids)
        save_access_control({"admins": admins, "allowed_users": allowed_users})
        await post_chunked_message(
            client,
            channel,
            f"Removed {', '.join(f'<@{target_id}>' for target_id in target_ids)} from the allowlist.",
            reply_thread_ts,
        )
        return True

    await send_access_help(client, channel, reply_thread_ts)
    return True


async def send_help(client, channel: str, thread_ts: str | None = None) -> None:
    """Send a simple help message."""
    help_text = (
        "*Reddit Slack Bot*\n"
        "DM me directly for Reddit research, subreddit selection, content planning, drafting, and reporting.\n"
        "Mention me in channels with `@bot_name your task`.\n"
        "Use `reddit: ...` to force the Reddit engine.\n"
        "Use `hermes: ...` or `general: ...` to force the Hermes sidecar.\n"
        "Type `tools` to list available Reddit tools.\n"
        "Type `reddit capabilities` to see what the toolkit can do.\n"
        "Type `reddit help` to see the best Reddit workflows and prompt formats.\n"
        "Type `access help` in DM to manage allowed Slack users dynamically.\n"
        "Ask for Excel exports with prompts like:\n"
        "- `Analyze r/SkincareAddiction and send the result as an Excel file`\n"
        "- `Export the top 25 Reddit posts about retinol this week into Excel with scores and insights`"
    )
    await post_chunked_message(client, channel, help_text, thread_ts)


async def send_reddit_workflow_help(
    client,
    channel: str,
    thread_ts: str | None = None,
) -> None:
    """Show the highest-value Reddit workflows the bot can handle."""
    help_text = (
        "Reddit Workflows\n\n"
        "*Research*\n"
        "- `research retinol concerns for acne-prone skin`\n"
        "- `summarize what people are discussing in r/SkincareAddiction about sunscreen sticks`\n\n"
        "*Where To Post*\n"
        "- `where should we post a hydration success story on Reddit?`\n"
        "- `which subreddit fits a dermatologist-led skincare AMA?`\n\n"
        "*What To Post*\n"
        "- `what should we post this week for our niacinamide launch?`\n"
        "- `create 5 Reddit post ideas for barrier repair content`\n\n"
        "*Draft Content*\n"
        "- `draft a Reddit post for r/SkincareAddiction about retinol purging`\n"
        "- `draft a helpful comment replying to this concern about tret dryness`\n\n"
        "*Analyze Context*\n"
        "- `analyze this Reddit thread and tell me the sentiment and opportunity: <reddit_url>`\n"
        "- `what is the current context around peptide serums on Reddit right now?`\n\n"
        "*Reports And Excel*\n"
        "- `make a weekly Reddit report for sunscreen discussions and export it to Excel`\n"
        "- `export the top content opportunities for acne education into xlsx`"
    )
    await post_chunked_message(client, channel, help_text, thread_ts)


async def send_tools_list(
    client,
    channel: str,
    user_id: str,
    thread_ts: str | None = None,
) -> None:
    """List the available Reddit tools for the current user session."""
    tool_names = get_reddit_agent_tool_names(user_id)

    if not tool_names:
        await post_chunked_message(
            client,
            channel,
            "No Reddit tools are available yet for this user.",
            thread_ts,
        )
        return

    group_lines: list[str] = []
    for title, names in get_reddit_agent_tool_groups(user_id):
        group_lines.append(f"*{title}*")
        group_lines.extend(f"- `{name}`" for name in names)

    await post_chunked_message(
        client,
        channel,
        (
            f"*Available Reddit Tools* ({len(tool_names)} total)\n"
            "These are the direct Reddit tools currently loaded for this bot.\n\n"
            + "\n".join(group_lines)
        ),
        thread_ts,
    )


async def send_reddit_capabilities_help(
    client,
    channel: str,
    user_id: str,
    thread_ts: str | None = None,
) -> None:
    """Explain what the Reddit toolkit can do in grouped, user-facing language."""
    tool_count = len(get_reddit_agent_tool_names(user_id))
    capability_guide = build_reddit_tool_capability_guide()
    help_text = (
        f"Reddit Capabilities\n\n"
        f"*Toolkit Status:* {tool_count} Reddit tools loaded\n\n"
        "*What This Bot Can Do*\n"
        "- research topics across Reddit and inside specific subreddits\n"
        "- discover subreddits and check subreddit rules before posting\n"
        "- read subreddit feeds, posts, comment threads, and specific comments\n"
        "- draft and, with approval, create posts and comments\n"
        "- edit or delete Reddit content after explicit approval\n"
        "- inspect flairs, user info, account scopes, and inbox reply settings\n\n"
        "*How It Uses The Toolkit*\n"
        f"{capability_guide}\n\n"
        "*Best Requests*\n"
        "- `research what people are saying about mineral sunscreen for oily skin`\n"
        "- `which subreddit should we use for a niacinamide troubleshooting post?`\n"
        "- `draft a post for r/SkincareAddiction and prepare comments for approval`\n"
        "- `analyze this Reddit thread and tell me the pain points: <reddit_url>`"
    )
    await post_chunked_message(client, channel, help_text, thread_ts)
