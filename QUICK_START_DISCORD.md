# Quick Start: Discord Bot with Composio

Use this short guide for a fast setup. For detailed screenshots and explanation, see `DISCORD_SETUP.md`.

## 1. Create and Configure the Discord Bot

1. Open Discord Developer Portal: https://discord.com/developers/applications
2. Create a new application.
3. Go to `Bot` and click `Add Bot`.
4. Copy the bot token.
5. In OAuth2 URL Generator:
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Send Messages`, `View Channels`, `Read Message History`, `Use Slash Commands`, `Embed Links`
6. Open the generated URL and invite the bot to your server.

## 2. Add Environment Variables

Create or update `.env` in the project root:

```env
OPENAI_API_KEY=your_openai_key
COMPOSIO_API_KEY=your_composio_key
DISCORD_BOT_TOKEN=your_discord_bot_token
```

## 3. Install Dependencies

```bash
cd /Users/bipinpaudel/work/automation
uv sync
```

Or with pip:

```bash
cd /Users/bipinpaudel/work/automation
pip install -e .
```

## 4. Start the Bot

```bash
cd /Users/bipinpaudel/work/automation
python discord_bot.py
```

Expected startup logs:

```text
Bot logged in as <bot-name>
Bot is ready to use
Synced X command(s)
```

## 5. Test Slash Commands

In your Discord server, test:

- `/help`
- `/tools`
- `/ask <task>`

Example:

- `/ask summarize my latest emails`

## Quick Troubleshooting

- Bot offline: verify `DISCORD_BOT_TOKEN` and re-invite the bot if needed.
- Commands missing: wait up to 60 seconds, then restart `discord_bot.py`.
- Auth errors: verify `OPENAI_API_KEY` and `COMPOSIO_API_KEY`.
