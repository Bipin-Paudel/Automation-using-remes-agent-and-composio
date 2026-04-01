# 🚀 Discord Bot with Composio Integration - Complete Setup Guide

## Prerequisites

You already have:
✅ Composio API Key  
✅ OpenAI API Key  
✅ Python 3.11+  
✅ Virtual environment setup

## Step 1: Get Your Discord Bot Token

### 1.1 Create a Discord Application
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** button (top right)
3. Give it a name (e.g., "Composio Bot")
4. Click **"Create"**

### 1.2 Create a Bot User
1. Go to **"Bot"** section in the left sidebar
2. Click **"Add Bot"** button
3. Under the bot's username, you'll see **"TOKEN"**
4. Click **"Copy"** to copy your bot token

### 1.3 Configure Bot Permissions
1. Still in the **"Bot"** section, scroll down to **"Scopes & Permissions"**
2. Under **TOKEN PERMISSIONS**, select these scopes:
   - ✅ `bot`
   
3. Under **BOT PERMISSIONS**, select:
   - ✅ `Send Messages`
   - ✅ `Read Messages/View Channels`
   - ✅ `Embed Links`
   - ✅ `Attach Files`
   - ✅ `Use Slash Commands`

4. Copy the generated OAuth2 URL from the "Scopes" section

### 1.4 Create a Test Discord Server (Optional but Recommended)
1. Open Discord
2. Click the **+** icon on the left sidebar
3. Click **"Create My Own"** → **"For me and my friends"**
4. Name it "Bot Testing"

### 1.5 Add Bot to Your Server
1. Paste the OAuth2 URL from Step 1.3 in your browser
2. Select your Discord server from the dropdown
3. Click **"Authorize"**

## Step 2: Update Your Environment Variables

Edit `/Users/bipinpaudel/work/automation/.env` and add:

```
DISCORD_BOT_TOKEN=your_bot_token_here
```

Replace `your_bot_token_here` with the token you copied in Step 1.2

## Step 3: Install Dependencies

Run in your terminal:

```bash
cd /Users/bipinpaudel/work/automation
uv sync
```

Or if using pip:

```bash
pip install discord.py aiohttp
```

## Step 4: Run Your Discord Bot

```bash
cd /Users/bipinpaudel/work/automation
python discord_bot.py
```

You should see:
```
✅ Bot logged in as YourBotName#1234
✅ Bot is ready to use!
✅ Synced X command(s)
```

## Step 5: Test Your Bot in Discord

Go to your Discord server and try these commands:

### `/help`
Shows available commands

### `/tools`
Lists all available Composio tools (Gmail, GitHub, Notion, etc.)

### `/ask <task>`
Examples:
- `/ask send a test email to my account`
- `/ask create a github issue in my repository`
- `/ask summarize my recent emails`

## Available Composio Tools

Your bot has access to Composio tools like:
- 📧 Gmail
- 🔗 GitHub
- 📝 Notion
- 📅 Google Calendar
- 📊 Google Sheets
- 💼 Linear
- And many more!

## Troubleshooting

### Bot doesn't appear online
- ❌ Wrong token? Double-check your `DISCORD_BOT_TOKEN` in `.env`
- ❌ Bot not added to server? Use the OAuth2 URL again

### Commands not showing up in Discord
- Try typing `/` and wait a few seconds for slash commands to appear
- If still not showing, disconnect and reconnect your bot

### "DISCORD_BOT_TOKEN not found in .env"
- Make sure you added the token to `.env`
- Restart the bot script

### Rate limiting errors
- Composio tools may take time to execute
- The bot defers responses to give more time

## Next Steps

1. **Customize the bot**: Edit `discord_bot.py` to add more commands
2. **Connect more tools**: Configure additional Composio integrations
3. **Add persistence**: Use the SQLite session to maintain conversation history

## Support

- Composio Docs: https://docs.composio.dev
- Discord.py Docs: https://discordpy.readthedocs.io
- OpenAI API: https://platform.openai.com/docs
