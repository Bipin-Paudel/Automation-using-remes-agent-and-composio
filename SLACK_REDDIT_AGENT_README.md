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

The bot uses:

- Slack for chat
- Composio for Reddit tool access
- OpenAI for reasoning and drafting
- a shared or per-user Reddit connection depending on your setup

## Main Files

- `slack_bot.py`: the Slack Reddit worker
- `connect_shared_reddit.py`: helper to connect a shared Reddit account in Composio
- `.env`: local project settings and secrets
- `.slack_access_control.json`: dynamic allowlist and admin state
- `exports/`: generated Excel files
- `README.md`: main project overview
- `SLACK_SETUP.md`: broader Slack setup instructions

## Setup Overview

You need four things ready:

1. Slack app and tokens
2. OpenAI API key
3. Composio API key
4. Reddit connected in Composio

## Step 1: Install Dependencies

From the project root:

```bash
cd /Users/bipinpaudel/work/automation
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
OPENAI_MODEL=gpt-5.2

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

## Recommended Daily Usage Flow

1. ask the bot what Reddit users are discussing now
2. ask which subreddit is the best fit
3. ask what content should be created
4. ask for a draft post or comment
5. ask for a weekly Excel report when needed

That is the cleanest way to use this project as a real Reddit AI worker inside Slack.


