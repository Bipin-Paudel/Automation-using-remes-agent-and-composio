# Automation Bots for Complete Beginners

This project helps you build AI assistants powered by Composio and OpenAI.

Right now this repo supports:

1. Discord bot mode
2. Slack setup guide for Hermes + Composio
3. Custom Slack bot mode with Composio
4. CLI terminal mode
5. Sheet and docs ingest for Google Sheets, Google Docs, CSV/text exports, Word docs, and Excel URLs

If you are new, follow this README from top to bottom once and then open the setup guide for the platform you want.

## What You Will Build

After setup, your bot can:

- respond to slash commands like `/ask`, `/help`, `/tools`
- respond directly to plain DM messages (no `/ask` needed)
- respond in server channels when you mention it (example: `@mybot summarize this`)
- use Composio-connected tools (Gmail, GitHub, Supabase, and more)
- support Slack setup through Hermes Agent with Composio tools
- support a custom `slack_bot.py` with real per-user Composio sessions
- format custom Slack bot replies with Slack-native Block Kit + `mrkdwn`
- export Reddit research and analysis results from the custom Slack bot into Excel files
- read public Google Sheets and Google Docs links directly in Slack
- turn a readable Google Sheet into a new Excel export file from Slack
- turn a readable Google Doc or text document into a new `.docx` export file from Slack
- manage Slack allowed users dynamically from Slack DMs instead of editing `.env` every time
- optionally let all Slack users share one Reddit connection instead of connecting Reddit one-by-one

## Requirements

- macOS, Linux, or Windows terminal
- Python 3.14+ (this project currently requires Python >= 3.14)
- Discord account
- A Discord server where you can add bots
- Slack workspace access if you want the Slack bot
- API credentials:
	- OpenAI API key
	- Composio API key
	- Discord bot token
	- Slack bot/app tokens for Slack setup

## Project Structure

- `discord_bot.py`: Discord bot app
- `slack_bot.py`: thin entrypoint for the custom Slack Reddit bot
- `slack_reddit_agent/`: package for the Slack Reddit bot implementation
- `slack_reddit_agent/app.py`: Slack app wiring and request flow
- `slack_reddit_agent/config.py`: environment loading and constants
- `slack_reddit_agent/prompts.py`: agent instructions, workflow detection, and prompt building
- `slack_reddit_agent/reddit_tools.py`: direct Reddit tool resolution from Composio
- `slack_reddit_agent/hermes_bridge.py`: Hermes-first orchestration and Hermes response cleanup
- `slack_reddit_agent/formatting.py`: Slack Block Kit formatting and message sanitization
- `slack_reddit_agent/progress.py`: lightweight progress status updates
- `slack_reddit_agent/commands.py`: help, tools, and access commands
- `slack_reddit_agent/exports.py`: generated file payload parsing and `.xlsx` / `.docx` creation
- `slack_reddit_agent/document_access.py`: direct document reading and export flow for Slack
- `sheet_document_ingest/`: Python sheet and document reader package used by the Slack bot
- `sheet_document_ingest/sheet_reader.py`: Google Sheets / CSV / XLSX reader logic
- `sheet_document_ingest/document_reader.py`: Google Docs / text / DOCX reader logic
- `main.py`: terminal chat app (optional)
- `.env.example`: safe template for local environment variables
- `.env.discord.example`: focused template for Discord-only setup
- `.env.slack.example`: focused template for the Slack Reddit bot
- `.env`: local secret keys (keep this file private)
- `DISCORD_SETUP.md`: detailed Discord portal steps
- `QUICK_START_DISCORD.md`: short checklist
- `SLACK_SETUP.md`: detailed Slack + Hermes + Composio setup guide
- `SLACK_REDDIT_AGENT_README.md`: dedicated setup and usage guide for the custom Slack Reddit worker

## Step 1: Open the Project

```bash
cd ~/path/to/automation
```

## Step 2: Install Dependencies

Recommended:

```bash
uv sync
```

Alternative:

```bash
pip install -e .
```

If you want the Slack Hermes bot on this machine too, also install Hermes:

```bash
uv add hermes-agent composio
```

## Step 3: Create or Update .env

Start from the template in the project root:

```bash
cp .env.example .env
```

If you only want one mode, you can also start from a focused template:

- `.env.discord.example` for Discord-only setup
- `.env.slack.example` for the Slack Reddit bot

Then update `.env` with the values you actually need. Minimum Discord example:

```env
OPENAI_API_KEY=your_openai_key
COMPOSIO_API_KEY=your_composio_key
DISCORD_BOT_TOKEN=your_discord_bot_token
```

Important:

- no quotes around keys
- no extra spaces around `=`
- keep this file private
- do not commit `.env` to GitHub

## Choose Your Platform

For Discord:

- follow the Discord steps below in this README
- or open `DISCORD_SETUP.md`

For Slack:

- open `SLACK_SETUP.md`
- open `SLACK_REDDIT_AGENT_README.md` if you want one clean doc for setup, usage, settings, access, and commands for the custom Reddit Slack bot
- recommended app name: `SkinPal Reddit Ops`
- this is the clean guide for a Reddit-focused AI employee in your SkinPal Slack workspace
- if you want direct Composio integration per Slack user, Reddit-only behavior, Google Sheet reading, and Excel report uploads, use the custom `slack_bot.py` section below

## Sheet And Docs Ingest

This repo includes a Python-based sheet-and-docs ingest layer that the Slack bot uses directly.

It supports:

- Google Sheets edit links
- Google Sheets CSV export links
- Google Docs links
- direct text file URLs
- direct `.docx` file URLs
- direct `.xlsx` file URLs

Typical Slack flow:

- paste a public Google Sheet or Google Doc link and say `read this`
- for sheets, follow up with `give me all that data in a new excel file`
- for docs, follow up with `export file` or `create docx file`

What happens:

- Google Sheets edit links are converted into CSV export URLs automatically
- Google Docs links are converted into text export URLs automatically
- the bot reads and analyzes the full document when access allows it
- Google Docs are summarized as readable text previews, not spreadsheet-style table summaries
- if the document is private, the bot asks for `Anyone with the link` access
- export requests can generate a new `.xlsx` file for sheet-like sources
- export requests can generate a new `.docx` file for Google Docs and text-like sources

Main implementation:

- [sheet_reader.py](sheet_document_ingest/sheet_reader.py)
- [document_reader.py](sheet_document_ingest/document_reader.py)
- [document_access.py](slack_reddit_agent/document_access.py)

Detailed reference:

- [sheet_document_ingest/README.md](sheet_document_ingest/README.md)

## Discord Setup

## Step 4: Create Discord Bot (Developer Portal)

1. Open: https://discord.com/developers/applications
2. Click `New Application`
3. Name it and create
4. Open `Bot` tab and click `Add Bot`
5. Copy your bot token
6. Put that token in `.env` as `DISCORD_BOT_TOKEN`

## Step 5: Invite Bot to Your Server

In `OAuth2` -> `URL Generator`:

1. Select scopes:
	 - `bot`
	 - `applications.commands`
2. Select bot permissions:
	 - `View Channels`
	 - `Send Messages`
	 - `Read Message History`
	 - `Embed Links`
	 - `Attach Files`
	 - `Use Slash Commands`
3. Copy generated URL
4. Open URL and invite bot to your server

## Step 6: Run the Bot

From project root:

```bash
python3 discord_bot.py
```

Expected startup logs:

```text
Bot logged in as <bot-name>
Bot is ready to use!
Synced 3 command(s)
```

Do not run this command in multiple terminals at the same time.

## Step 7: Use the Bot

You have 3 interaction styles.

### A) Slash Commands

- `/help`
- `/tools`
- `/ask <task>`

Example:

- `/ask establish connection with supabase`

### B) Direct Message Mode (No Slash Needed)

Open DM with your bot and type plain text:

- `summarize my latest emails`
- `draft a reply to my client`

### C) Mention Mode in Server Channels

In a server channel, mention the bot:

- `@mybot what is h2o?`

## Step 8: Stop and Restart Safely

To stop:

- Press `Ctrl + C` in the running bot terminal

To restart:

```bash
python3 discord_bot.py
```

If you see duplicate replies, you likely had multiple running processes previously.

## Common Issues and Fixes

### 1) Duplicate responses

Cause: multiple bot processes were running.

Fix:

```bash
pkill -f discord_bot.py
python3 discord_bot.py
```

### 2) Unknown interaction (404 / error code 10062)

Cause: interaction expired before acknowledgment.

Fix:

- run latest code from this repo
- retry command once
- avoid heavy network delay when first invoking

### 3) Slash commands do not appear

Fix:

- wait 30 to 60 seconds after startup
- type `/` again
- confirm `applications.commands` scope was selected during invite

### 4) DISCORD_BOT_TOKEN not found

Fix:

- ensure `.env` exists in project root
- ensure variable name is exactly `DISCORD_BOT_TOKEN`

### 5) Warning: davey is not installed

This warning only affects voice support. Normal text chat still works.

## Optional: Run Terminal Assistant Instead of Discord

```bash
python3 main.py
```

This opens an interactive terminal assistant using the same Composio setup.

## Security Checklist (Important)

- Never share `.env` publicly
- Never commit `.env` to git
- If keys are exposed, rotate immediately:
	- OpenAI key
	- Composio key
	- Discord bot token

## Quick Success Test

After setup, confirm all of these:

1. Bot shows online in Discord
2. `/help` returns command list
3. DM plain text message gets one response
4. Mention in server gets one response

If all 4 pass, your automation setup is complete.

## Slack Setup Summary

If you want Slack instead of Discord, this is the exact step-by-step flow that worked for us. You can also open `SLACK_SETUP.md` for the Slack-only version.

## Slack Setup: Exact Working Flow

This section documents the full Slack setup path we used for:

- Hermes Agent
- Composio
- a Reddit-focused Slack bot
- the app name `SkinPal Reddit Ops`

### Step 1: Install Project Dependencies

From the project root:

```bash
cd ~/path/to/automation
uv sync
```

If you want Hermes on this machine too:

```bash
uv add hermes-agent composio
```

### Step 2: Create the Slack App

1. Open `https://api.slack.com/apps`
2. Click `Create New App`
3. Choose `From scratch`
4. Name the app `SkinPal Reddit Ops`
5. Choose your Slack workspace
6. Click `Create App`

### Step 3: Add Bot Token Scopes

In Slack app settings:

1. Open `OAuth & Permissions`
2. Under `Bot Token Scopes`, add:
   - `chat:write`
   - `app_mentions:read`
   - `channels:history`
   - `channels:read`
   - `groups:history`
   - `im:history`
   - `im:read`
   - `im:write`
   - `users:read`
   - `files:write`
3. Save the changes

If you add or change scopes later, reinstall the app again.

### Step 4: Enable Socket Mode

In Slack app settings:

1. Open `Socket Mode`
2. Turn `Enable Socket Mode` on
3. Click `Generate Token and Scopes`
4. Give the token a name like `hermes-socket`
5. Add the scope `connections:write`
6. Generate the token
7. Copy the token that starts with `xapp-`

Important:

- this is your `SLACK_APP_TOKEN`
- this must come from `Socket Mode`
- this is not the same as the bot token

### Step 5: Enable Event Subscriptions

In Slack app settings:

1. Open `Event Subscriptions`
2. Turn `Enable Events` on
3. Under `Subscribe to bot events`, add:
   - `message.im`
   - `message.channels`
   - `message.groups`
   - `app_mention`
4. Save the changes

Why this matters:

- `message.im` is for DMs
- `message.channels` is for public channels
- `message.groups` is for private channels
- `app_mention` is for mentions in channels

### Step 6: Enable App Home Messages

In Slack app settings:

1. Open `App Home`
2. Find `Show Tabs`
3. Turn on `Messages Tab`
4. If Slack shows an extra checkbox allowing users to send messages, enable it

This is required so the bot can be used in DMs properly.

### Step 7: Install the App to the Workspace

In Slack app settings:

1. Go back to `OAuth & Permissions`
2. Click `Install to Workspace`
3. Approve the installation
4. Copy the bot token that starts with `xoxb-`

Important:

- this is your `SLACK_BOT_TOKEN`
- it is different from `SLACK_APP_TOKEN`

### Step 8: Find Your Slack Member ID

Hermes uses allowed Slack user IDs.

To find yours:

1. Open Slack
2. Click your profile
3. Open your profile details
4. Copy your `Member ID`

It looks like this:

```text
U01234567890
```

This becomes:

```env
SLACK_ALLOWED_USERS=U01234567890
```

### Step 9: Create the Hermes Environment File

Hermes does not use the project `.env` for Slack gateway startup. It uses:

```text
~/.hermes/.env
```

Create and open it:

```bash
mkdir -p ~/.hermes
touch ~/.hermes/.env
open -a TextEdit ~/.hermes/.env
```

Or in VS Code:

```bash
code ~/.hermes/.env
```

Add:

```env
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token
SLACK_ALLOWED_USERS=U01234567890
COMPOSIO_API_KEY=your-composio-api-key
OPENAI_API_KEY=your-openai-api-key
```

Very important:

- use real values
- no quotes
- no spaces around `=`
- correct: `SLACK_BOT_TOKEN=xoxb-...`
- wrong: `SLACK_BOT_TOKEN = xoxb-...`

Lock down the file:

```bash
chmod 600 ~/.hermes/.env
```

### Step 10: If Hermes Says `slack-bolt not installed`

We hit this during setup.

If Hermes logs show `slack-bolt not installed`, install it into Hermes' own runtime:

```bash
~/.hermes/hermes-agent/venv/bin/python -m ensurepip --upgrade
~/.hermes/hermes-agent/venv/bin/python -m pip install slack-bolt
```

This is different from installing into the project environment.

### Step 11: If You Only Want Slack, Disable Discord in Hermes

We also hit this during setup.

If Hermes keeps trying Discord and failing first, comment out Discord variables in `~/.hermes/.env`:

```env
# DISCORD_BOT_TOKEN=...
# DISCORD_ALLOWED_USERS=...
# DISCORD_HOME_CHANNEL=...
```

That keeps the gateway focused on Slack only.

### Step 12: Start or Restart Hermes

Start the gateway:

```bash
uv run hermes gateway
```

If another gateway is already running:

```bash
uv run hermes gateway restart
```

### Step 13: Invite the Bot and Test It

In Slack:

1. Open a public or private channel
2. Invite the bot
3. Test DMs first
4. Test public channel mentions second
5. Test private channel mentions third

Example invite:

```text
/invite @Reddit Agent
```

Test messages:

```text
hello
```

In DMs, plain text should work.

In channels, including private channels, mention the bot:

```text
@Reddit Agent hello
```

Important private-channel rule:

- private channels do not behave like DMs
- Hermes treats them like channels
- the bot must be invited there
- the bot usually needs an `@mention` there

### Step 14: Optional But Recommended: Set a Slack Home Channel

Hermes can use one Slack channel as its home channel for cron job results and cross-platform messages.

If you want to set it from the environment, add these to `~/.hermes/.env`:

```env
SLACK_HOME_CHANNEL=your_channel_id
SLACK_HOME_CHANNEL_NAME=your-channel-name
```

If Hermes prompts you in Slack, use:

```text
/hermes sethome
```

Important:

- the correct Slack command is `/hermes sethome`
- `/sethome` by itself is not the correct Slack command in this setup

### Step 15: Connect Composio

Once Slack is working:

1. keep `COMPOSIO_API_KEY` in `~/.hermes/.env`
2. connect the accounts and tools you want through Composio
3. start with a small workflow first

Good order:

1. get DMs working
2. get public mentions working
3. get private mentions working
4. then add Composio tool workflows

## Slack Troubleshooting

### 1) Bot does not reply anywhere

Check:

- Hermes is running
- `~/.hermes/.env` exists
- `SLACK_BOT_TOKEN` is correct
- `SLACK_APP_TOKEN` is correct
- no spaces around `=`

Restart:

```bash
uv run hermes gateway restart
```

### 2) `apps.connections.open` shows `invalid_auth`

We hit this too.

This means your `SLACK_APP_TOKEN` is wrong, expired, or not a proper Socket Mode app token.

Fix:

1. go to `Socket Mode`
2. generate a new app-level token
3. add scope `connections:write`
4. replace `SLACK_APP_TOKEN` in `~/.hermes/.env`
5. restart Hermes

### 3) Bot works in DMs but not in public channels

Check:

- `message.channels`
- `app_mention`
- `channels:history`
- the bot was invited to the channel
- you mentioned the bot with `@Reddit Agent`

### 4) Bot works in DMs but not in private channels

Check:

- `message.groups`
- `groups:history`
- the bot was invited to the private channel
- you reinstalled the app after changing scopes or events
- you are mentioning the bot, not sending plain text only

### 5) Hermes tries Discord even though you want Slack

Comment out Discord lines in `~/.hermes/.env` and restart Hermes.

### 6) Hermes says another gateway is already running

Use:

```bash
uv run hermes gateway restart
```

## Final Slack Checklist

Before calling the setup complete, confirm all of these:

1. Slack app created from scratch
2. Bot scopes added
3. Socket Mode enabled
4. `xapp-` app-level token created with `connections:write`
5. Event Subscriptions enabled
6. `message.im`, `message.channels`, `message.groups`, and `app_mention` added
7. Messages Tab enabled
8. App installed to workspace
9. `~/.hermes/.env` created
10. Slack env lines have no spaces around `=`
11. `SLACK_BOT_TOKEN` starts with `xoxb-`
12. `SLACK_APP_TOKEN` starts with `xapp-`
13. `SLACK_ALLOWED_USERS` is your Slack Member ID
14. `COMPOSIO_API_KEY` and `OPENAI_API_KEY` are present
15. `slack-bolt` is available in Hermes if needed
16. Hermes gateway is running
17. DM test passes
18. Public channel mention test passes
19. Private channel mention test passes

## Custom Slack Bot with Composio

Use this section if you want to run the new `slack_bot.py` file instead of the Hermes gateway.

This is the better path if you want:

- real Composio sessions per Slack user
- Reddit-specific tool access
- custom Slack bot logic inside this repo
- behavior closer to your `discord_bot.py`

### What `slack_bot.py` Does

The custom Slack bot:

- connects directly to Slack using Socket Mode
- keeps a Composio session per Slack user for auth and session context
- keeps memory per Slack user with `SQLiteSession`
- is Reddit-focused by default
- can act like a Reddit operations employee instead of a generic chatbot
- responds to DMs directly
- responds in channels and private channels when mentioned
- formats replies for Slack using official Block Kit patterns
- resolves direct Reddit tools from Composio before running the agent
- supports a simple `tools` message to list the real Reddit tools available to the bot
- supports `reddit capabilities` to explain what the loaded Reddit toolkit can do

### Package Layout

The Slack Reddit bot now uses a package layout instead of one large file.

- `slack_bot.py`: wrapper that runs the bot
- `slack_reddit_agent/app.py`: Slack event handling and final response flow
- `slack_reddit_agent/config.py`: `.env` loading and shared constants
- `slack_reddit_agent/sessions.py`: Composio session and memory helpers
- `slack_reddit_agent/reddit_tools.py`: fetches concrete Reddit tools such as search, rules, post read, comments, and posting tools
- `slack_reddit_agent/prompts.py`: workflow routing, Slack context capture, and agent setup
- `slack_reddit_agent/hermes_bridge.py`: Hermes-first orchestration bridge and Hermes direct-reply integration
- `slack_reddit_agent/formatting.py`: Slack-native rendering and cleanup
- `slack_reddit_agent/progress.py`: temporary `Thinking...` and `Researching...` status updates
- `slack_reddit_agent/commands.py`: `help`, `tools`, `reddit help`, and access-control commands
- `slack_reddit_agent/exports.py`: Excel export parsing and file creation
- `slack_reddit_agent/runtime.py`: startup checks such as Hermes gateway conflict detection

### Runtime Architecture

The current bot is a single Slack responder with a Hermes-first orchestration flow:

- `Hermes orchestrator`: receives every Slack request first, decides whether it can answer directly, and only hands off when Reddit tools or live Reddit context are required
- `Composio + Reddit tools`: used only after Hermes routes the request into Reddit research, subreddit checks, drafts, comments, or export-oriented workflows

This is important operationally:

- run `slack_bot.py` as the Slack-facing bot for this app
- do not run Hermes Slack gateway against the same Slack app at the same time
- if Hermes gateway is active on the same machine and app, the bot now treats that as a conflict by default

### Slack Message Format Used by `slack_bot.py`

The custom Slack bot now formats replies in a Slack-native way:

- top-level `text` fallback for notifications and accessibility
- optional Slack `header` block when the first line is a short title followed by a blank line
- Slack `section` blocks using `mrkdwn` for the main body
- automatic chunking for long replies so messages stay inside Slack-safe limits

Write Slack replies in this style:

- short title on the first line when useful
- one blank line after the title
- short paragraphs
- `*bold*` for section labels
- `_italic_` when needed
- `~strike~` for strike text
- backticks for inline code
- triple backticks for code blocks
- `-` for bullets
- `1.` for numbered lists
- `<https://example.com|label>` for labeled links

Avoid:

- GitHub Markdown headings like `# Heading`
- Markdown tables
- HTML
- nested bullets
- Slack legacy attachments for normal replies

Recommended reply shape:

```text
Reddit Summary

*Summary*
Short plain-language answer.

*Key Points*
- Point one
- Point two

*Recommendation*
1. First action
2. Second action

*Next Step*
Ask a short follow-up or confirm the next action.
```

If the first line is a short title and the second line is blank, the bot will try to send that title as a Slack `header` block and the rest as `mrkdwn` body content.

### Reddit Ops Capabilities

The custom Slack bot is now designed to handle Reddit work such as:

- topic and competitor research
- understanding what people are discussing right now
- deciding where to post on Reddit
- deciding what content should be created
- ranking the best subreddits for a topic or campaign
- drafting Reddit posts and comments
- analyzing Reddit thread sentiment and objections
- turning research into Excel reports when requested

It also pulls recent Slack conversation context into the agent prompt so the bot can understand the current discussion before answering.

### Step 1: Install Dependencies

From the project root:

```bash
cd ~/path/to/automation
uv sync
```

This installs:

- `slack-bolt`
- `composio`
- `openai-agents`
- the rest of the project dependencies

### Step 2: Create the Slack App

Use the same Slack app setup as the Hermes section above.

You still need:

- `chat:write`
- `app_mentions:read`
- `channels:history`
- `channels:read`
- `groups:history`
- `im:history`
- `im:read`
- `im:write`
- `users:read`
- `files:write`
- `message.im`
- `message.channels`
- `message.groups`
- `app_mention`
- Socket Mode enabled
- an app-level token with `connections:write`

### Step 3: Create the Project `.env`

For `slack_bot.py`, use the project `.env` file in this repo.

Add:

```env
OPENAI_API_KEY=your_openai_key
COMPOSIO_API_KEY=your_composio_key
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_APP_TOKEN=xapp-your-slack-app-token
SLACK_ALLOWED_USERS=U01234567890
COMPOSIO_TOOLKITS=reddit
COMPOSIO_TOOLKIT_VERSION_REDDIT=20260316_00
OPENAI_MODEL=gpt-5.2
HERMES_ENABLED=true
ALLOW_HERMES_GATEWAY_CONFLICT=false
HERMES_MODEL=
HERMES_PROVIDER=
HERMES_TIMEOUT_SECONDS=180
REDDIT_BRAND_NAME=SkinPal
REDDIT_BRAND_CONTEXT=We are a skincare brand focused on practical education and trust-building on Reddit.
REDDIT_CONTENT_GOALS=audience research, subreddit discovery, content strategy, post creation, comment drafting, weekly reporting
REDDIT_PRIORITY_SUBREDDITS=r/SkincareAddiction,r/AsianBeauty,r/acne
REDDIT_TARGET_AUDIENCES=people with acne-prone skin, skincare beginners, retinol users
REDDIT_PROHIBITED_CLAIMS=no guaranteed cure claims,no misleading medical claims
```

Important:

- no quotes
- no spaces around `=`
- `SLACK_BOT_TOKEN` starts with `xoxb-`
- `SLACK_APP_TOKEN` starts with `xapp-`
- `COMPOSIO_TOOLKITS=reddit` keeps the bot Reddit-focused by default
- `COMPOSIO_TOOLKIT_VERSION_REDDIT=20260316_00` pins the Reddit toolkit version used by the bot
- `HERMES_ENABLED=true` lets the bot run Hermes-first orchestration and handle direct Hermes replies
- `ALLOW_HERMES_GATEWAY_CONFLICT=false` is the safe default and prevents mixed replies when Hermes Slack gateway is also running
- the optional `REDDIT_*` values make the bot much more specific to your brand and Reddit strategy

### Step 4: Understand the Composio + Hermes Part

This is the important part.

`slack_bot.py` is now a combined Reddit worker with two internal engines.

For Reddit work, it does these things:

1. reads `COMPOSIO_API_KEY`
2. creates a Composio session for each Slack user
3. limits the default toolkit to `reddit`
4. fetches concrete Reddit tools directly from Composio instead of relying only on the 6 session meta-tools
5. gives those direct Reddit tools to the OpenAI agent
6. keeps conversation memory per Slack user

For broader assistant work, it can also call Hermes locally through the orchestration bridge. That path is used for things like:

- general chat and support
- rewriting
- summarization
- strategy synthesis
- polishing Reddit research into cleaner stakeholder-facing output

Typical Reddit tools now available to the bot include:

- `REDDIT_SEARCH_ACROSS_SUBREDDITS`
- `REDDIT_GET_SUBREDDITS_SEARCH`
- `REDDIT_GET_SUBREDDIT_RULES`
- `REDDIT_RETRIEVE_REDDIT_POST`
- `REDDIT_RETRIEVE_POST_COMMENTS`
- `REDDIT_CREATE_REDDIT_POST`
- `REDDIT_POST_REDDIT_COMMENT`

### Step 4.1: Best Prompt Patterns For Reddit Work

Good examples:

- `research what people are saying about mineral sunscreen for oily skin`
- `where should we post a barrier-repair educational post on Reddit?`
- `what should we post this week for niacinamide users?`
- `draft a Reddit post for r/SkincareAddiction about retinol purging`
- `analyze this thread and explain the sentiment and opportunity: https://reddit.com/...`
- `make a weekly Reddit report and export it to Excel`
- `reddit: export the top 25 Reddit posts about retinol this week into Excel with scores and insights`

For Hermes-side tasks, use:

- `hermes: turn this Reddit research into a founder update`
- `general: rewrite this in simpler language`
- `general: turn this analysis into a short strategy memo`

You can also ask:

- `reddit help`
- `tools`
- `reddit capabilities`

That shows the bot's main Reddit workflows directly in Slack.

### Step 5: Connect Your Reddit Account in Composio

Before Reddit actions can work properly, your Composio setup must have access to Reddit.

Do this:

1. open your Composio dashboard
2. connect the Reddit account you want to use
3. make sure Reddit access is available for the user/session you plan to use
4. then start the Slack bot

If the bot starts but Reddit actions are unavailable, this is usually the missing step.

### Step 6: Run the Custom Slack Bot

Start it from the project root:

```bash
uv run python slack_bot.py
```

Expected startup output is similar to:

```text
Slack bot connected as reddit_agent
Reddit toolkit default: reddit
Slack bot is ready to receive DMs and @mentions
```

If shared Reddit mode is enabled, you should also see a line similar to:

```text
Shared Reddit account mode: skinpal_reddit_shared
```

### Step 7: How to Use It

In DMs:

- send plain text directly
- example: `find good subreddits for skincare product feedback`

In public or private channels:

- mention the bot
- example: `@Reddit Agent draft a Reddit post for SkinPal`

Special message:

- send `tools`
- the bot will list the real Reddit tools currently available to your session
- send `reddit capabilities`
- the bot will explain its Reddit research, thread analysis, posting, and moderation capabilities
- start a message with `reddit:` to force the Reddit engine
- start a message with `hermes:` or `general:` to force the Hermes direct-reply path

### Step 7.1: How to Verify Hermes-First Routing

Use this exact test order after startup.

1. Check startup health in the terminal.
   You should see the bot connect, print the default Reddit toolkit, and not raise any Hermes gateway conflict error.
2. Check access control in Slack.
   If this is the first run, DM the bot `admin claim`, then allow yourself or teammates with `allowlist add <@user>`.
3. Test a Hermes direct-reply request in a DM.
   Send `hello` or `rewrite this in a friendlier tone: our meeting is delayed`.
   Expected result: the bot replies directly without Reddit-specific sections.
4. Test a Reddit handoff request in a DM.
   Send `where should we post about niacinamide on Reddit this week?`
   Expected result: the progress text moves through Hermes and then research, and the final answer talks about Reddit context or subreddit fit.
5. Test explicit routing prefixes.
   Send `hermes: turn this into a short founder update` and then `reddit: analyze Reddit sentiment around tretinoin dryness this week`.
   Expected result: the prefix forces the intended engine path.
6. Test channel behavior.
   Mention the bot in a public channel, and then in a private channel after inviting it.
   Expected result: no reply without a mention in channels, and normal replies once mentioned.
7. Test tool visibility.
   Send `tools`.
   Expected result: you should see concrete Reddit tools such as `REDDIT_SEARCH_ACROSS_SUBREDDITS` instead of only generic Composio meta-tools.
8. Test shared-account mode if enabled.
   Ask two different Slack users to send Reddit research requests.
   Expected result: both users can use the bot, while Reddit actions still run through the same shared Composio identity.

Healthy signs:

- casual chat and rewriting requests get direct Hermes-style answers
- Reddit requests produce research-oriented answers
- `tools` shows real Reddit tools
- the bot does not send duplicate replies
- the bot does not claim a Reddit action already happened unless a tool actually did it

Warning signs:

- every request gets Reddit-style sections even for simple chat
- `tools` only shows generic Composio tools
- duplicate replies appear in Slack
- startup fails with a Hermes gateway conflict
- Hermes requests return raw JSON or CLI chrome instead of a clean reply

### Step 7.2: Access Roles

The bot has three practical user roles:

- `No access`
  The user cannot use the bot normally. The bot tells them to ask an admin for access, or to use `admin claim` if this is the first setup.
- `Allowed user`
  The user can use the bot for normal work such as Reddit research, drafting, subreddit analysis, Hermes-assisted rewrites, and Excel exports.
- `Access admin`
  The user can do everything an allowed user can do, and can also manage admins and the allowlist from a DM with the bot.

Important access behavior:

- `admin claim` works only when no admin exists yet
- `admin add <@user>` also adds that user to the allowlist
- `admin remove <@user>` removes admin permission only
- `allowlist remove <@user>` removes only the dynamic allowlist entry
- if `.env` still contains `SLACK_ALLOWED_USERS`, those users remain allowed as fallback users

### Step 8: How It Behaves in Channels

DMs:

- plain messages work

Public channels:

- mention required

Private channels:

- bot must be invited
- mention required

This is expected behavior in `slack_bot.py`.

### Step 9: How to Stop and Restart

Stop:

- press `Ctrl + C` in the terminal where it is running

Restart:

```bash
uv run python slack_bot.py
```

If you think another copy is already running:

```bash
pkill -f slack_bot.py
uv run python slack_bot.py
```

### Step 10: Common Problems

#### 1) `Unhandled request ... app_mention`

This was caused by missing `app_mention` handling.

It is already fixed in the current `slack_bot.py`.

If you still see it:

- make sure you are running the latest file from this repo
- restart the bot

#### 2) Bot replies in DMs but not in channels

Check:

- `app_mention` is enabled
- `message.channels` is enabled
- bot was invited to the channel
- you mentioned the bot

#### 3) Bot replies in DMs but not in private channels

Check:

- `message.groups` is enabled
- `groups:history` scope is present
- bot was invited to the private channel
- you mentioned the bot

#### 4) Slack tokens are invalid

Check:

- `SLACK_BOT_TOKEN` is a valid `xoxb-` token
- `SLACK_APP_TOKEN` is a valid `xapp-` token
- Socket Mode is enabled

#### 5) Reddit tools are missing or only generic meta-tools appear

Check:

- `COMPOSIO_API_KEY` is correct
- `COMPOSIO_TOOLKITS=reddit` is present
- your Reddit account is connected in Composio
- restart the bot after config changes
- send `tools` and confirm you see Reddit tools like `REDDIT_SEARCH_ACROSS_SUBREDDITS`

If `tools` only shows entries like `COMPOSIO_MANAGE_CONNECTIONS` or `COMPOSIO_MULTI_EXECUTE_TOOL`, you are likely running an older process or older code path.

#### 6) Duplicate Slack replies

Cause:

- more than one Slack responder is running for the same app

Common examples:

- more than one `slack_bot.py` process is running
- Hermes Slack gateway is also running against the same Slack app

Fix:

```bash
pkill -f "hermes_cli.main gateway run"
pkill -f slack_bot.py
uv run python slack_bot.py
```

#### 7) Raw lines like `browser_navigate` or `skills_list` appear in Slack

Cause:

- Hermes Slack gateway or another Slack responder is still replying directly
- an older process is still running

Fix:

```bash
pkill -f "hermes_cli.main gateway run"
pkill -f slack_bot.py
uv run python slack_bot.py
```

The intended production setup for this repo is:

- one Slack-facing bot process: `uv run python slack_bot.py`
- Hermes used internally as the first-pass orchestrator, not as a second Slack gateway for the same app

### Step 11: Quick Success Test

Before calling the custom Slack bot ready, confirm all of these:

1. `uv sync` completed successfully
2. Slack app scopes and events are set
3. Socket Mode is enabled
4. `.env` contains Slack, OpenAI, and Composio keys
5. `COMPOSIO_TOOLKITS=reddit` is set
6. Reddit is connected in Composio
7. `uv run python slack_bot.py` starts cleanly
8. DM test works
9. Channel mention test works
10. Private channel mention test works
11. `tools` shows available Composio tools
12. `reddit capabilities` explains Reddit powers cleanly
13. `hermes: rewrite this in simpler language` returns a Hermes-side answer without duplicate Slack replies
