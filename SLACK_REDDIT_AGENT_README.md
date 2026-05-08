# Slack Reddit Agent Guide

This guide is the single place for running this project as a Reddit-focused AI worker inside Slack.

It covers:

- what the bot does
- how to set it up
- how to launch it
- how to use it
- how to change settings
- how to manage access
- which commands are available
- how Excel export works

## What This Bot Does

The Slack Reddit bot is designed to work like a Reddit operations assistant for your team.

It can help with:

- Reddit research
- subreddit discovery
- deciding where to post
- deciding what content to create
- drafting Reddit posts
- drafting Reddit comments
- analyzing Reddit threads
- summarizing current Reddit context
- creating Excel reports when requested
- reading public Google Sheets and Google Docs links directly inside Slack
- exporting a previously read Google Sheet into a new Excel file
- exporting a previously read Google Doc into a new `.docx` file

The bot uses:

- Slack for chat
- Composio for Reddit tool access
- Hermes as the first-pass orchestrator and direct-reply engine
- OpenAI for reasoning and drafting
- a shared or per-user Reddit connection depending on your setup

## Main Files

- `slack_bot.py`: thin entrypoint that starts the Slack Reddit worker
- `slack_reddit_agent/`: package that holds the Slack Reddit bot implementation
- `slack_reddit_agent/app.py`: Slack app wiring and runtime
- `slack_reddit_agent/config.py`: `.env` loading and shared constants
- `slack_reddit_agent/sessions.py`: Composio session and SQLite memory helpers
- `slack_reddit_agent/reddit_tools.py`: direct Reddit tool resolver
- `slack_reddit_agent/prompts.py`: workflow routing, Slack context capture, and agent setup
- `slack_reddit_agent/hermes_bridge.py`: local Hermes bridge used for general chat, rewriting, and synthesis
- `slack_reddit_agent/formatting.py`: Slack formatting and cleanup
- `slack_reddit_agent/progress.py`: temporary `Thinking...` and `Researching...` status updates
- `slack_reddit_agent/commands.py`: help, tools, workflow help, and access commands
- `slack_reddit_agent/exports.py`: Excel export parsing and file generation
- `slack_reddit_agent/document_access.py`: direct document reading and export flow for Slack
- `slack_reddit_agent/runtime.py`: startup checks and Hermes gateway conflict detection
- `sheet_document_ingest/sheet_reader.py`: Python sheet reader used by the Slack bot
- `sheet_document_ingest/document_reader.py`: Python document reader used by the Slack bot
- `connect_shared_reddit.py`: helper to connect a shared Reddit account in Composio
- `.env`: local project settings and secrets
- `.slack_access_control.json`: dynamic allowlist and admin state
- `exports/`: generated Excel files
- `README.md`: main project overview
- `SLACK_SETUP.md`: broader Slack setup instructions

## Architecture

The Slack Reddit bot now works as one Slack responder with three internal layers:

1. Slack app layer
   - receives DMs and `@mentions`
   - shows lightweight status like `Thinking...`
   - formats final answers into Slack-native Block Kit
2. Hermes orchestration layer
   - receives every Slack request first
   - decides whether Hermes can answer directly or whether Reddit tools are required
   - handles broader assistant work such as rewriting, summarization, synthesis, and general chat support
3. Composio Reddit layer
   - keeps Composio session context per Slack user
   - resolves direct Reddit tools before running the agent
   - gives the agent concrete tools for search, subreddit discovery, rule lookup, post retrieval, comments, and posting
   - runs only when Hermes routes the task into the Reddit workflow

This matters because the older `session.tools()` path often exposed only 6 generic Composio meta-tools. The current bot now fetches real Reddit tools directly and uses those for the actual Reddit workflow, while Hermes now acts as the first-pass orchestrator and direct-reply engine.

There is also a direct document layer before the Hermes/Reddit routing path for supported file links. When a user sends a public Google Sheet, Google Doc, CSV export, text file, `.docx`, or `.xlsx` URL and asks to read it, the bot can answer from the document directly instead of falling back to Reddit analysis.

## Document Access And Sheet And Docs Ingest

The custom Slack bot includes a Python-based sheet-and-docs ingest flow.

Supported document inputs:

- Google Sheets edit links
- Google Sheets CSV export links
- Google Docs links
- direct text URLs
- direct `.docx` URLs
- direct `.xlsx` URLs

Supported Slack actions:

- `read this`
- `summarize this sheet`
- `open this file`
- `give me all that data in a new excel file`
- `export file`
- `create docx file`

How it works:

1. the bot finds the supported URL in the current Slack message or recent Slack context
2. for Google Sheets edit links, it converts the link into a CSV export URL automatically
3. for Google Docs links, it converts the link into a plain-text export URL automatically
4. it reads the full document when the document is publicly accessible
5. for Google Docs and text-like documents, it returns a text-first Slack summary such as `Document Read`
6. for sheet-like sources, it returns a structured row-and-column summary
7. if the next message asks for an export, it reuses the same document link from the Slack thread/context
8. sheet-like sources export to `.xlsx`, while Google Docs and text-like sources export to `.docx` by default unless the user explicitly asks for Excel

Requirements:

- Google Sheets must allow `Anyone with the link` access
- Google Docs must allow `Anyone with the link` access
- `.xlsx` links must point directly to a downloadable file

Important notes:

- the `Slackbot` Google Drive install suggestion is Slack’s own product behavior, not this repo’s bot logic
- the active sheet-and-docs ingest runtime is Python
- the Slack bot uses `sheet_document_ingest/` through `slack_reddit_agent/document_access.py`

## Setup Overview

You need four things ready:

1. Slack app and tokens
2. OpenAI API key
3. Composio API key
4. Reddit connected in Composio

## Step 1: Install Dependencies

From the project root:

```bash
cd ~/path/to/automation
uv sync
```

## Step 2: Create the Slack App

In Slack app settings, make sure you configure:

- Socket Mode enabled
- bot token created
- app-level token created with `connections:write`
- bot installed to workspace

Important scopes:

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

Important events:

- `message.im`
- `message.channels`
- `message.groups`
- `app_mention`

If you want the full click-by-click Slack app setup, open `SLACK_SETUP.md`.

## Step 3: Create `.env`

Create or update the project `.env` file with:

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

COMPOSIO_SHARED_USER_ID=skinpal_reddit_shared
# Optional if the shared Composio user has multiple Reddit accounts:
# COMPOSIO_SHARED_CONNECTED_ACCOUNT_ID=ca_xxxxx

REDDIT_BRAND_NAME=SkinPal
REDDIT_BRAND_CONTEXT=We are a skincare brand focused on trustworthy education and useful Reddit-native content.
REDDIT_CONTENT_GOALS=audience research, subreddit discovery, content strategy, post creation, comment drafting, reporting
REDDIT_PRIORITY_SUBREDDITS=r/SkincareAddiction,r/AsianBeauty,r/acne
REDDIT_TARGET_AUDIENCES=people with acne-prone skin, skincare beginners, retinol users
REDDIT_PROHIBITED_CLAIMS=no guaranteed cure claims,no misleading medical claims
```

Important:

- do not put spaces around `=`
- `SLACK_BOT_TOKEN` must start with `xoxb-`
- `SLACK_APP_TOKEN` must start with `xapp-`
- `COMPOSIO_TOOLKITS=reddit` keeps the bot focused on Reddit work
- `COMPOSIO_TOOLKIT_VERSION_REDDIT=20260316_00` pins the Reddit toolkit version used by the bot
- `HERMES_ENABLED=true` lets the bot route broader assistant tasks to Hermes
- `ALLOW_HERMES_GATEWAY_CONFLICT=false` keeps this Slack app protected from duplicate Hermes gateway replies

## Step 4: Connect Reddit in Composio

Before the bot can actually do Reddit work, Composio must have a Reddit connection.

If you want one shared Reddit account for the whole Slack team:

```bash
uv run python connect_shared_reddit.py
```

That helper:

- reads `COMPOSIO_SHARED_USER_ID`
- prints a browser connection URL
- waits for Reddit login to finish
- prints connected account details

If your shared Composio user has only one connected Reddit account, you usually do not need `COMPOSIO_SHARED_CONNECTED_ACCOUNT_ID`.

If there are multiple Reddit accounts under that shared Composio user, set the exact one with:

```env
COMPOSIO_SHARED_CONNECTED_ACCOUNT_ID=ca_xxxxx
```

## Step 5: Launch the Bot

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

If shared-account mode is enabled, you should also see:

```text
Shared Reddit account mode: skinpal_reddit_shared
```

Important operational rule:

- use `uv run python slack_bot.py` as the Slack-facing bot for this app
- do not run Hermes Slack gateway on the same Slack app at the same time
- Hermes is meant to run through this bot as the first-pass orchestrator, not as a second responder

If another copy is already running:

```bash
pkill -f slack_bot.py
uv run python slack_bot.py
```

## Step 6: First-Time Access Setup

The bot has access control.

If no admin exists yet:

1. open a DM with the bot in Slack
2. send `admin claim`
3. you become the first access admin
4. add users with `allowlist add <@user>`

Important:

- access management commands only work in DM
- normal users cannot use the bot until they are allowed
- `.env` `SLACK_ALLOWED_USERS` still works as a fallback allowlist

## How to Use the Bot

In DMs:

- send normal plain-text messages directly

In public channels:

- mention the bot

In private channels:

- invite the bot first
- then mention the bot

The bot is designed for requests like:

- research what Reddit users are discussing
- decide which subreddit fits a topic
- decide what content should be posted
- draft a Reddit post or comment
- analyze a Reddit thread
- export a research report to Excel

It also supports explicit engine routing:

- `reddit: ...` forces the Reddit engine
- `hermes: ...` forces the Hermes direct-reply path
- `general: ...` also forces the Hermes direct-reply path

## How to Verify Hermes-First Orchestration

Use this checklist after every new setup or major routing change.

### 1. Check startup health

Run:

```bash
uv run python slack_bot.py
```

Healthy startup looks like:

- Slack bot connects successfully
- default Reddit toolkit is printed
- shared Reddit account mode is printed if enabled
- no Hermes gateway conflict error appears

If you see a Hermes gateway conflict, stop the Hermes gateway for the same Slack app before continuing.

### 2. Check first-time access

In a Slack DM with the bot:

1. send `admin claim` if no admin exists yet
2. send `allowlist add <@your_user>` if needed

Healthy result:

- the bot confirms admin or allowlist changes
- you can send normal work messages after that

### 3. Test Hermes direct replies

Send one or two normal assistant tasks in a DM:

- `hello`
- `rewrite this in a warmer tone: thanks for the update`
- `general: turn this into a short meeting summary`

Healthy result:

- the bot replies directly
- the answer does not drift into Reddit analysis
- the message reads like normal assistant help, not a tool trace

### 4. Test Hermes-to-Reddit handoff

Send a Reddit task in a DM:

- `where should we post about niacinamide on Reddit this week?`
- `research what people are saying about tretinoin dryness right now`

Healthy result:

- progress starts with Hermes and then moves into research
- the final answer includes Reddit context, subreddit fit, or content guidance
- the reply stays clean and Slack-formatted

### 5. Test explicit engine forcing

Send:

- `hermes: rewrite this into a founder update`
- `reddit: analyze Reddit sentiment around sunscreen sticks this week`

Healthy result:

- `hermes:` stays in direct assistant mode
- `reddit:` forces the Reddit workflow even if the message could have been answered more casually

### 6. Test tool loading

Send:

- `tools`

Healthy result:

- you see concrete Reddit tools such as `REDDIT_SEARCH_ACROSS_SUBREDDITS`, `REDDIT_GET_SUBREDDIT_RULES`, or `REDDIT_RETRIEVE_POST_COMMENTS`
- you do not see only generic tools like `COMPOSIO_SEARCH_TOOLS`

### 7. Test channel behavior

In a public channel:

- mention the bot with a simple request

In a private channel:

- invite the bot first
- then mention it

Healthy result:

- the bot ignores channel chatter unless mentioned
- the bot responds once mentioned

### 8. Test shared Reddit account mode

If `COMPOSIO_SHARED_USER_ID` is set, ask two different Slack users to send Reddit research tasks.

Healthy result:

- both Slack users can use the bot
- the bot still uses one shared Composio Reddit identity for Reddit actions
- conversation memory remains per Slack user even though the Reddit account is shared

### 9. Watch for unhealthy signs

These usually mean routing or config is wrong:

- every message gets routed into Reddit research, even `hello`
- Hermes replies show raw JSON or CLI chrome
- Slack shows duplicate replies
- startup fails with a Hermes gateway conflict
- `tools` shows only generic Composio meta-tools
- the bot claims it posted or changed something on Reddit without confirmation and tool results

### 10. Quick restart workflow

If behavior looks wrong after changing `.env` or code:

```bash
pkill -f slack_bot.py
uv run python slack_bot.py
```

Then rerun the checklist above from step 1.

## Available Commands

### General Commands

- `help`
- `/help`
- `tools`
- `/tools`
- `reddit help`
- `workflow help`
- `workflows`
- `/reddit`
- `reddit capabilities`
- `capabilities`
- `/capabilities`

### Engine Routing Prefixes

- `reddit: research what people are saying about retinol this week`
- `reddit: export the top 25 Reddit posts about retinol this week into Excel with scores and insights`
- `hermes: turn this Reddit analysis into a founder update`
- `general: rewrite this in simpler language`

What `tools` shows now:

- the real Reddit tools currently available to the bot
- not just the generic Composio meta-tools

Healthy examples include:

- `REDDIT_SEARCH_ACROSS_SUBREDDITS`
- `REDDIT_GET_SUBREDDITS_SEARCH`
- `REDDIT_GET_SUBREDDIT_RULES`
- `REDDIT_RETRIEVE_REDDIT_POST`
- `REDDIT_RETRIEVE_POST_COMMENTS`
- `REDDIT_CREATE_REDDIT_POST`
- `REDDIT_POST_REDDIT_COMMENT`

### Access Commands

Use these only in a DM with the bot:

- `access help`
- `admin claim`
- `admin list`
- `admin add <@user>`
- `admin remove <@user>`
- `allowlist list`
- `allowlist add <@user>`
- `allowlist remove <@user>`

### Access Roles

The bot has three practical access levels:

- `No access`
  The user cannot use the bot normally. They will be told to ask an admin for access, or to use `admin claim` if this is the first setup.
- `Allowed user`
  The user can use the bot for normal work such as Reddit research, drafting, subreddit analysis, Hermes-assisted rewrites, and Excel exports, but cannot manage access for other users.
- `Access admin`
  The user can do everything an allowed user can do, and can also manage admins and the allowlist from a DM with the bot.

Important behavior:

- `admin claim` works only when no admin exists yet
- `admin add <@user>` also adds that user to the allowlist
- `admin remove <@user>` removes admin privileges, but does not automatically remove normal bot access
- `allowlist remove <@user>` removes only the dynamic allowlist entry
- if `.env` still contains `SLACK_ALLOWED_USERS`, those users remain allowed as a fallback

Where access is stored:

- dynamic admins and allowed users are stored in `.slack_access_control.json`
- static fallback users come from `SLACK_ALLOWED_USERS` in `.env`
- the bot merges both sources when deciding who can use it

## Best Prompt Examples

### Research

- `research what Reddit users are saying about retinol irritation right now`
- `summarize what people are discussing in r/SkincareAddiction about sunscreen sticks`
- `compare how Reddit users talk about SkinPal vs competitors`

### Where to Post

- `where should we post a hydration success story on Reddit?`
- `which subreddit fits a dermatologist-led skincare AMA?`
- `best subreddit for educational content about tretinoin dryness`

### What to Post

- `what should we post this week for our niacinamide launch?`
- `create 5 Reddit post ideas for barrier repair content`
- `make a Reddit content plan for acne education this month`

### Drafting

- `draft a Reddit post for r/SkincareAddiction about retinol purging`
- `draft a helpful comment replying to this concern about tret dryness`
- `write a Reddit post for r/acne that feels educational, not promotional`

### Thread Analysis

- `analyze this Reddit thread and tell me the sentiment and opportunity: https://reddit.com/...`
- `summarize this Reddit thread and tell me what users actually want: https://reddit.com/...`

### Excel Reports

- `make a weekly Reddit report for sunscreen discussions and export it to Excel`
- `export the top content opportunities for acne education into xlsx`
- `analyze r/SkincareAddiction and send the result as an Excel file`

## How the Bot Responds

The bot is configured to respond in Slack-native format:

- top-level message text fallback
- Slack `header` block when there is a short first-line title
- Slack `section` blocks with `mrkdwn`
- chunked long replies

For Reddit work, it tries to organize answers around sections like:

- `*Summary*`
- `*Current Context*`
- `*Recommended Subreddits*`
- `*Content Plan*`
- `*Draft Post*`
- `*Risks*`
- `*Next Step*`

## How to Change Settings

Most bot behavior can be changed through `.env`.

### Core Settings

- `OPENAI_API_KEY`: OpenAI access
- `COMPOSIO_API_KEY`: Composio access
- `SLACK_BOT_TOKEN`: Slack bot token
- `SLACK_APP_TOKEN`: Slack Socket Mode token
- `OPENAI_MODEL`: model used by the bot
- `COMPOSIO_TOOLKITS`: keep this as `reddit` unless you deliberately want more tools
- `COMPOSIO_TOOLKIT_VERSION_REDDIT`: pinned Reddit toolkit version for deterministic tool loading
- `HERMES_ENABLED`: enable or disable Hermes-first orchestration
- `HERMES_MODEL`: optional Hermes model override
- `HERMES_PROVIDER`: optional Hermes provider override
- `HERMES_TIMEOUT_SECONDS`: Hermes orchestration and direct-reply timeout
- `ALLOW_HERMES_GATEWAY_CONFLICT`: if `false`, the bot blocks startup when Hermes gateway is also running for the same app

### Access Settings

- `SLACK_ALLOWED_USERS`: static fallback allowlist from `.env`
- `.slack_access_control.json`: dynamic admin and allowlist state

### Shared Reddit Account Settings

- `COMPOSIO_SHARED_USER_ID`: shared Composio user for one Reddit account used by all Slack users
- `COMPOSIO_SHARED_CONNECTED_ACCOUNT_ID`: optional exact Reddit connected account under that shared user

### Brand and Strategy Settings

- `REDDIT_BRAND_NAME`: your brand or worker identity
- `REDDIT_BRAND_CONTEXT`: short description of your company and voice
- `REDDIT_CONTENT_GOALS`: what the bot should optimize for
- `REDDIT_PRIORITY_SUBREDDITS`: preferred subreddit list
- `REDDIT_TARGET_AUDIENCES`: target audience hints
- `REDDIT_PROHIBITED_CLAIMS`: claims or language the bot must avoid

After changing `.env`, restart the bot:

```bash
pkill -f slack_bot.py
uv run python slack_bot.py
```

## How to Give Access to Another User

If you are already an admin:

1. open a DM with the bot
2. send `allowlist add <@user>`

To make someone else an admin:

1. open a DM with the bot
2. send `admin add <@user>`

To view current access:

- `admin list`
- `allowlist list`

Quick role guide:

- use `allowlist add <@user>` for a teammate who should use the bot but should not manage permissions
- use `admin add <@user>` for a trusted operator who should also manage access for others

## Excel Export Behavior

When the user asks for Excel, the bot can:

- post a short Slack summary
- generate an `.xlsx` file locally in `exports/`
- upload that file back into the same Slack conversation

For best results, ask for exact columns.

Example:

```text
Analyze r/SkincareAddiction posts from this week.
Send the result as an Excel file.
Columns: subreddit, title, score, num_comments, topic, sentiment, recommendation.
```

## Important Operational Notes

- the bot can only execute the Reddit actions exposed by your Composio Reddit tools
- the bot now tries to resolve concrete Reddit tools directly before running the agent
- the bot is configured to ask for confirmation before creating, editing, deleting, submitting, or replying on Reddit
- the bot is designed to avoid spammy or misleading Reddit behavior
- if subreddit rules cannot be verified, recommendations should be treated more carefully

## Troubleshooting

### Bot starts but Reddit actions do not work

Check:

- `COMPOSIO_API_KEY` is valid
- Reddit is connected in Composio
- `COMPOSIO_TOOLKITS=reddit` is set
- shared account settings are correct if you are using shared mode
- restart the bot after changing config
- send `tools` and confirm you see Reddit tools like `REDDIT_SEARCH_ACROSS_SUBREDDITS`

If `tools` only shows entries such as:

- `COMPOSIO_MANAGE_CONNECTIONS`
- `COMPOSIO_MULTI_EXECUTE_TOOL`
- `COMPOSIO_SEARCH_TOOLS`

then you are usually running an older process or older code path. Restart the bot from the project root:

```bash
pkill -f slack_bot.py
uv run python slack_bot.py
```

### Bot works in DMs but not in channels

Check:

- `app_mention` event is enabled
- the bot was invited to the channel
- you mentioned the bot

### Bot works in DMs but not in private channels

Check:

- `message.groups` is enabled
- `groups:history` scope exists
- the bot was invited to the private channel
- you mentioned the bot

### Slack connection fails

Check:

- `SLACK_BOT_TOKEN` is a valid `xoxb-` token
- `SLACK_APP_TOKEN` is a valid `xapp-` token
- Socket Mode is enabled

### Raw lines like `browser_navigate` or `skills_list` appear in Slack

Check:

- Hermes Slack gateway is not running against the same Slack app
- no older bot process is still active

Fix:

```bash
pkill -f "hermes_cli.main gateway run"
pkill -f slack_bot.py
uv run python slack_bot.py
```

This repo is designed to use Hermes internally as the first-pass orchestrator through `slack_bot.py`, not as a second Slack gateway for the same app.

### Hermes replies conflict with Reddit bot replies

Cause:

- Hermes Slack gateway and `slack_bot.py` are both attached to the same Slack app

Fix:

- stop Hermes gateway for this app
- keep only `uv run python slack_bot.py` running
- if you want Hermes gateway too, use a separate Slack app for it

## Recommended Daily Usage Flow

1. ask the bot what Reddit users are discussing now
2. ask which subreddit is the best fit
3. ask what content should be created
4. ask for a draft post or comment
5. ask Hermes to rewrite or summarize the result if needed
6. ask for a weekly Excel report when needed

That is the cleanest way to use this project as a real Reddit AI worker inside Slack.
