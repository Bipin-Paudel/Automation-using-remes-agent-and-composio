# Slack Setup Guide

This file gives you the full Slack setup in one place.

If you want one dedicated document just for the custom Reddit Slack worker, also open `SLACK_REDDIT_AGENT_README.md`.

It covers 2 valid ways to build your Slack bot:

1. `Hermes Gateway` setup
2. `slack_bot.py` custom setup with direct Composio integration

If you want the simplest Slack setup, use **Hermes Gateway**.

If you want the best Reddit-specific bot with real Composio sessions per Slack user, use **`slack_bot.py`**.

Recommended for this repo:

- use **`slack_bot.py`** unless you specifically want Hermes Gateway to be the Slack-facing bot
- use **Hermes Gateway** only when you want the quickest generic Slack setup and do not need the custom Reddit worker behavior

## Sheet Ingest In Slack

The custom `slack_bot.py` route includes direct sheet-ingest support.

Supported links:

- Google Sheets edit links
- Google Sheets CSV export links
- direct `.xlsx` URLs

Typical Slack usage:

1. send a readable document link
2. say `read this`
3. optionally follow up with `give me all that data in a new excel file`

What the bot does:

- converts Google Sheets edit links into machine-readable CSV export URLs
- reads the full dataset when the file is publicly accessible
- summarizes row count, columns, missing values, and sample rows in Slack
- can generate a new Excel file from the parsed data

Important:

- Google Sheets must allow `Anyone with the link` access for direct reading
- the Google Drive install prompt from `Slackbot` is Slack’s own UI behavior, not this repo’s code
- the active runtime uses the Python sheet reader in `sheet_ingest/python_sheet_reader.py`

Recommended app name:

- `SkinPal Reddit Ops`

This name works well because it sounds professional, clearly matches your Reddit workflow, and still fits if your bot grows into a full Reddit operations employee.

## What You Need

- Slack workspace access
- OpenAI API key
- Composio API key
- Python 3.14+
- this repo opened locally

From the project root:

```bash
cd /Users/bipinpaudel/work/automation
uv sync
```

If you want Hermes on this machine too:

```bash
uv add hermes-agent composio
```

## Step 1: Create the Slack App

1. Open `https://api.slack.com/apps`
2. Click `Create New App`
3. Choose `From scratch`
4. Name it `SkinPal Reddit Ops`
5. Choose your Slack workspace
6. Click `Create App`

## Step 2: Add Bot Token Scopes

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

Optional:

- `groups:read`

Important:

- if you add or change scopes later, reinstall the app again

## Step 3: Enable Socket Mode

In Slack app settings:

1. Open `Socket Mode`
2. Turn `Enable Socket Mode` on
3. Click `Generate Token and Scopes`
4. Give the token a name like `hermes-socket`
5. Add scope `connections:write`
6. Generate the token
7. Copy the token that starts with `xapp-`

This token becomes:

```env
SLACK_APP_TOKEN=xapp-your-token
```

Important:

- this token must come from `Socket Mode`
- it is not your bot token
- it must start with `xapp-`

## Step 4: Enable Event Subscriptions

In Slack app settings:

1. Open `Event Subscriptions`
2. Turn `Enable Events` on
3. Under `Subscribe to bot events`, add:
   - `message.im`
   - `message.channels`
   - `message.groups`
   - `app_mention`
4. Save the changes

These matter because:

- `message.im` is for DMs
- `message.channels` is for public channels
- `message.groups` is for private channels
- `app_mention` is for mentions in channels

## Step 5: Enable App Home Messages

In Slack app settings:

1. Open `App Home`
2. Find `Show Tabs`
3. Turn `Messages Tab` on
4. If Slack shows a checkbox for allowing messages, enable it

Without this, DMs may not work correctly.

## Step 6: Install the App to the Workspace

In Slack app settings:

1. Go back to `OAuth & Permissions`
2. Click `Install to Workspace`
3. Approve the installation
4. Copy the token that starts with `xoxb-`

This token becomes:

```env
SLACK_BOT_TOKEN=xoxb-your-token
```

Important:

- this is the bot token
- this is different from `SLACK_APP_TOKEN`
- it must start with `xoxb-`

## Step 7: Find Your Slack Member ID

You need this for allowlisting.

To find it:

1. Open Slack
2. Click your profile
3. Open profile details
4. Copy your `Member ID`

Example:

```text
U01234567890
```

This becomes:

```env
SLACK_ALLOWED_USERS=U01234567890
```

If you want multiple allowed users, separate them with commas.

## Choose Your Slack Bot Type

Now choose one route.

### Route A: Hermes Gateway

Use this if you want:

- a quick Slack bot
- less custom coding
- a Hermes-managed Slack gateway

### Route B: `slack_bot.py`

Use this if you want:

- direct Composio integration in code
- per-user Composio sessions
- Reddit-only default tools
- a custom Slack bot like your `discord_bot.py`
- direct Google Sheet / CSV / Excel reading in Slack
- Excel file creation from previously read document links

## Route A: Hermes Gateway Setup

### Step A1: Create `~/.hermes/.env`

Create and open the file:

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

Important:

- no quotes
- no spaces around `=`
- this file is `~/.hermes/.env`
- not the project `.env`

Correct:

```env
SLACK_BOT_TOKEN=xoxb-...
```

Wrong:

```env
SLACK_BOT_TOKEN = xoxb-...
```

Lock it down:

```bash
chmod 600 ~/.hermes/.env
```

### Step A2: If Hermes Says `slack-bolt not installed`

Install it into the Hermes runtime:

```bash
~/.hermes/hermes-agent/venv/bin/python -m ensurepip --upgrade
~/.hermes/hermes-agent/venv/bin/python -m pip install slack-bolt
```

### Step A3: If You Only Want Slack, Disable Discord in Hermes

In `~/.hermes/.env`, comment out Discord lines if present:

```env
# DISCORD_BOT_TOKEN=...
# DISCORD_ALLOWED_USERS=...
# DISCORD_HOME_CHANNEL=...
```

### Step A4: Start Hermes

Run:

```bash
uv run hermes gateway
```

If another gateway is already running:

```bash
uv run hermes gateway restart
```

### Step A5: Optional Home Channel

If you want a Slack home channel for cron results and cross-platform delivery:

```env
SLACK_HOME_CHANNEL=your_channel_id
SLACK_HOME_CHANNEL_NAME=your-channel-name
```

If Hermes prompts you inside Slack, the correct command is:

```text
/hermes sethome
```

Important:

- `/sethome` alone is not the right Slack command here

### Step A6: Test Hermes

Test in this order:

1. DM the bot with `hello`
2. mention it in a public channel
3. mention it in a private channel after inviting it there

Examples:

```text
hello
```

```text
@Reddit Agent hello
```

Private channel rule:

- the bot must be invited
- you should mention it

## Route B: Custom `slack_bot.py` with Composio

Use this if you want the Slack bot to be directly connected to Composio in code.

This is the best route for a Reddit-specific Slack employee bot.

### What `slack_bot.py` Does

The custom Slack bot:

- connects directly to Slack with Socket Mode
- creates a Composio session per Slack user
- keeps a separate `SQLiteSession` per Slack user
- uses Reddit as the default toolkit
- can behave like a Reddit operations assistant for your brand
- responds directly in DMs
- responds in channels and private channels when mentioned
- formats replies using official Slack Block Kit patterns
- resolves direct Reddit tools before running the agent
- routes every Slack message through Hermes first as the shared orchestrator
- lets Hermes reply directly for normal chat, rewriting, planning, and synthesis
- hands work to the Reddit/Composio engine only when Hermes decides the task needs Reddit tools or live Reddit context
- supports a `tools` message to show available Reddit tools
- supports `reddit capabilities` to explain the loaded toolkit in plain language
- can turn Reddit analysis results into `.xlsx` Excel files and upload them back to Slack

### Code Structure

The Slack Reddit bot now uses a package layout instead of one large file.

- `slack_bot.py`: wrapper entrypoint
- `slack_reddit_agent/app.py`: Slack event handling and main runtime
- `slack_reddit_agent/reddit_tools.py`: concrete Reddit tool fetching
- `slack_reddit_agent/prompts.py`: workflow detection and agent setup
- `slack_reddit_agent/hermes_bridge.py`: local Hermes CLI bridge for non-Reddit assistant tasks
- `slack_reddit_agent/formatting.py`: Slack output rendering
- `slack_reddit_agent/progress.py`: temporary status messages
- `slack_reddit_agent/commands.py`: help, tools, and access commands
- `slack_reddit_agent/exports.py`: Excel report creation
- `slack_reddit_agent/sessions.py`: session and memory helpers
- `slack_reddit_agent/config.py`: `.env` settings and constants
- `slack_reddit_agent/runtime.py`: startup checks including Hermes gateway conflict detection

### Runtime Model

This bot is now designed as one Slack responder with a Hermes-first orchestration flow:

- `Hermes orchestrator`: first-pass routing, direct chat replies, rewriting, synthesis, cleanup, and broader strategy help
- `Composio Reddit engine`: invoked only when Hermes decides the task needs Reddit workflows such as search, post analysis, subreddit checks, drafting, or export preparation

Best practice:

- run only `uv run python slack_bot.py` for this Slack app
- do not run Hermes Slack gateway on the same Slack app at the same time
- if Hermes gateway is still running, the bot now treats it as a conflict by default

### Slack Message Format Used by `slack_bot.py`

`slack_bot.py` is set up to send Slack-native replies instead of generic Markdown dumps.

It uses:

- top-level `text` fallback for accessibility and notifications
- an optional Slack `header` block when the first line is a short title followed by a blank line
- Slack `section` blocks with `mrkdwn` for the main reply body
- automatic chunking for long replies

Best format to use in prompts and responses:

- short title on the first line when useful
- one blank line after the title
- short paragraphs
- `*bold*` for section names
- `_italic_` when needed
- `~strike~` for strike text
- backticks for inline code
- triple backticks for code blocks
- `-` for bullets
- `1.` for numbered lists
- `<https://example.com|label>` for labeled links

Avoid:

- `# Markdown headings`
- Markdown tables
- HTML
- nested bullets
- legacy attachment-style formatting for standard replies

Recommended response pattern:

```text
Reddit Summary

*Summary*
Short answer in plain Slack-friendly language.

*Key Points*
- Point one
- Point two

*Recommendation*
1. First action
2. Second action

*Next Step*
Ask for confirmation or suggest the next move.
```

If you follow that structure, the custom bot will render especially cleanly in Slack.

### Reddit Ops Focus

The custom bot is now meant to answer questions like:

- what is happening on Reddit around a topic right now
- where should we post this content
- which subreddit is the best fit and why
- what content should be created for that subreddit
- how should the final Reddit post or comment be written
- whether the result should also be exported into Excel

It also includes recent Slack conversation context in the internal agent prompt so it can understand the current discussion before answering.

### Step B1: Create the Project `.env`

For `slack_bot.py`, use the project root `.env`.

Start from the repo template so the variable names and defaults stay clean:

```bash
cp .env.example .env
```

Add:

```env
OPENAI_API_KEY=your_openai_key
COMPOSIO_API_KEY=your_composio_key
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_APP_TOKEN=xapp-your-slack-app-token
# Optional bootstrap allowlist. If blank, claim the first admin in Slack DM after startup.
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
REDDIT_BRAND_NAME=SkinPal
REDDIT_BRAND_CONTEXT=We are a skincare brand focused on trustworthy education and useful Reddit-native content.
REDDIT_CONTENT_GOALS=audience research, subreddit discovery, content strategy, post creation, comment drafting, reporting
REDDIT_PRIORITY_SUBREDDITS=r/SkincareAddiction,r/AsianBeauty,r/acne
REDDIT_TARGET_AUDIENCES=people with acne-prone skin, sensitive skin shoppers, retinol users
REDDIT_PROHIBITED_CLAIMS=no guaranteed cure claims,no misleading medical claims
# Optional when you want to force one exact connected Reddit account:
# COMPOSIO_SHARED_CONNECTED_ACCOUNT_ID=ca_xxxxx
```

Important:

- no quotes
- no spaces around `=`
- `SLACK_BOT_TOKEN` must be `xoxb-...`
- `SLACK_APP_TOKEN` must be `xapp-...`
- start from `.env.example` instead of typing the whole file manually
- `COMPOSIO_TOOLKITS=reddit` keeps the bot Reddit-focused by default
- `COMPOSIO_TOOLKIT_VERSION_REDDIT=20260316_00` pins the Reddit toolkit version used by the bot
- `HERMES_ENABLED=true` allows the bot to route general or explicitly prefixed tasks to Hermes
- `ALLOW_HERMES_GATEWAY_CONFLICT=false` is the recommended production setting and avoids mixed Slack replies
- `SLACK_ALLOWED_USERS` is now optional if you want to manage access directly from Slack
- `COMPOSIO_SHARED_USER_ID` lets every Slack user operate through one shared Reddit connection
- `COMPOSIO_SHARED_CONNECTED_ACCOUNT_ID` is optional and only needed if that shared Composio user has more than one Reddit account connected
- the optional `REDDIT_*` settings make the bot much more specific to your brand, audience, and posting rules
- `SLACK_HOME_CHANNEL` and `SLACK_HOME_CHANNEL_NAME` are for the Hermes Gateway route, not the custom `slack_bot.py` route

### Step B2: Understand the Composio + Hermes Part

`slack_bot.py` now combines direct Composio Reddit execution with Hermes-first orchestration.

For Reddit workflows, it does these things:

1. reads `COMPOSIO_API_KEY`
2. creates a Composio session for each Slack user
3. limits the default toolkit to `reddit`
4. resolves concrete Reddit tools directly from Composio
5. passes those Reddit tools into the OpenAI agent
6. keeps Slack conversation memory per user

For broader assistant workflows, it can also call Hermes locally. That is useful for:

- rewriting
- summarizing
- strategy synthesis
- cleanup of Reddit findings into business-ready output
- natural chat support that is not a direct Reddit action

The important difference is that the bot is no longer relying only on the 6 generic Composio meta-tools from `session.tools()`. It now fetches real Reddit tools like subreddit search, subreddit rules, post retrieval, comment retrieval, and posting tools before running the agent.

### Step B2.1: Best Ways To Ask The Bot

Good prompt patterns:

- `research what Reddit users are saying about retinol irritation right now`
- `where should we post a sunscreen myth-busting post?`
- `what should we post this week for acne education?`
- `draft a Reddit post for r/SkincareAddiction about niacinamide purging myths`
- `analyze this Reddit thread and tell me the sentiment, pain points, and opportunity: https://reddit.com/...`
- `make a weekly Reddit report and export it to Excel`
- `reddit: export the top 25 Reddit posts about retinol this week into Excel with scores and insights`

Explicit routing prefixes:

- `reddit: ...` forces the Reddit engine
- `hermes: ...` forces the Hermes direct-reply path
- `general: ...` also forces the Hermes direct-reply path

Examples:

- `hermes: turn this Reddit analysis into a founder update`
- `general: rewrite this in simpler language`

You can also send:

- `reddit help`

That shows the bot's main Reddit workflows directly inside Slack.

### Step B3: Connect Reddit in Composio

Before Reddit actions work, Composio needs access to Reddit.

Do this:

1. open your Composio dashboard
2. connect the Reddit account you want to use
3. make sure the connection is available for your Composio user/session
4. then start the Slack bot

If the bot starts but Reddit actions do not work, this is usually the missing step.

### Step B3.1: Use One Shared Reddit Account For Everyone

Yes, you can do this.

This is the cleanest setup if:

- you want all Slack users to work through one company Reddit account
- you do not want every Slack user to connect Reddit separately
- you are okay with all Reddit actions being performed as the same Reddit identity

How it works:

- the Slack bot still keeps separate Slack conversation memory per user
- but Composio authentication uses one shared Composio user ID
- that shared Composio user ID owns the Reddit connection
- so every allowed Slack user uses the same connected Reddit account

Set it up like this:

1. in `.env`, add:

```env
COMPOSIO_SHARED_USER_ID=skinpal_reddit_shared
```

2. open your Composio dashboard
3. connect Reddit using that shared Composio user identity
4. if only one Reddit account is connected there, you can stop here
5. if multiple Reddit accounts are connected to that same shared Composio user, copy the exact connected account ID and add:

```env
COMPOSIO_SHARED_CONNECTED_ACCOUNT_ID=ca_xxxxx
```

6. restart the bot

Very important:

- `COMPOSIO_SHARED_CONNECTED_ACCOUNT_ID` must be a Composio connected account ID, not a Slack member ID
- if you accidentally put something like `U012345...` there, the bot will fail because that is a Slack user ID format
- if your shared Composio user has only one connected Reddit account, leave `COMPOSIO_SHARED_CONNECTED_ACCOUNT_ID` unset

Quick connection helper from this repo:

```bash
uv run python connect_shared_reddit.py
```

This prints a Composio connect link for the shared Reddit user, waits for you to finish Reddit login in the browser, and then prints the connected account ID.

Result:

- every allowed Slack user can use Reddit features immediately
- no additional Reddit login is needed per Slack user
- posts, comments, edits, and reads all happen through the same shared Reddit account

Important tradeoffs:

- all Reddit actions come from one Reddit account
- rate limits and reputation are shared
- you should be careful with posting and moderation actions
- for safety, keep confirmation before create/edit/delete actions enabled

### Step B4: Run `slack_bot.py`

From the project root:

```bash
uv sync
uv run python slack_bot.py
```

Expected startup output looks like:

```text
Slack bot connected as reddit_agent
Reddit toolkit default: reddit
Slack bot is ready to receive DMs and @mentions
```

### Step B4.1: Quick Smoke Test

Run these checks in order after startup:

1. open a DM with the bot
2. if you left `SLACK_ALLOWED_USERS` blank, send `admin claim`
3. send `help`
4. send `tools`
5. send `reddit capabilities`
6. mention the bot once in a public channel

Healthy signs:

- the bot answers in DM
- `tools` shows Reddit tools for your session
- `reddit capabilities` returns a readable capability summary
- channel mentions work only when the bot is actually mentioned

### Step B5: Use the Bot

In DMs:

- plain text works
- example: `find good subreddits for skincare product feedback`

In public channels:

- mention required
- example: `@Reddit Agent draft a Reddit post for SkinPal`

In private channels:

- bot must be invited
- mention required

Special message:

- send `tools`
- the bot will list available Reddit tools for your session
- send `reddit capabilities`
- the bot will summarize its Reddit research, posting, and moderation powers
- start a message with `reddit:` to force the Reddit engine
- start a message with `hermes:` or `general:` to force the Hermes direct-reply path

### Step B5.1: Ask for Reddit Analysis

Use direct natural-language prompts like:

- `Analyze r/SkincareAddiction and tell me the top content themes this week`
- `Review recent Reddit discussions about tretinoin and tell me the biggest user complaints`
- `Compare how Reddit users talk about SkinPal vs competitors and summarize sentiment`
- `Find repeating questions in skincare subreddits that could become content ideas`

The bot is already configured to stay Reddit-focused by default because `COMPOSIO_TOOLKITS=reddit`.

### Step B5.1A: Manage Allowed Users Directly From Slack

You no longer need to keep editing `.env` for every allowed user.

The bot now supports a dynamic local allowlist managed from Slack DMs.

First-time setup:

1. start the bot
2. open a DM with the bot
3. send `admin claim`
4. you become the first Slack access admin
5. then add users with `allowlist add <@user>`

Important:

- until the first admin is claimed, normal bot usage stays locked
- access commands still work in DM so you can bootstrap safely

Useful DM commands:

- `access help`
- `admin claim`
- `admin list`
- `admin add <@user>`
- `admin remove <@user>`
- `allowlist list`
- `allowlist add <@user>`
- `allowlist remove <@user>`

How it works:

- dynamic access is stored in `.slack_access_control.json`
- if `SLACK_ALLOWED_USERS` is still present in `.env`, those users remain allowed too
- access commands only work in DM so your permission changes stay private

Access roles:

- `No access`
  The user cannot use the bot normally and will be told to ask an admin for access, or use `admin claim` if this is the first setup.
- `Allowed user`
  The user can use the bot for Reddit research, drafting, thread analysis, Hermes-assisted rewrites, and Excel exports, but cannot manage access.
- `Access admin`
  The user can use the bot normally and can also manage admins and the allowlist from DM.

Important details:

- `admin claim` works only when no admin exists yet
- `admin add <@user>` also adds that user to the allowlist
- `admin remove <@user>` removes admin permission only
- `allowlist remove <@user>` removes only the dynamic allowlist entry
- users still listed in `SLACK_ALLOWED_USERS` in `.env` remain allowed as fallback users

### Step B5.2: Ask for Excel Files

If you want results in Excel, ask clearly for an Excel file.

Good prompt examples:

- `Analyze r/SkincareAddiction and export the top 25 posts to Excel`
- `Find Reddit posts about retinol from this week and send an Excel report with title, score, comments, subreddit, and insight`
- `Compare 3 skincare subreddits and create an Excel file with trends, pain points, and posting ideas`

What happens now:

1. the bot runs the Reddit task
2. it posts the short analysis in Slack
3. it creates an `.xlsx` file in the local `exports/` folder
4. it uploads that Excel file back into the same Slack conversation

### Step B5.3: Best Prompt Format for Reliable Excel Output

For best results, tell the bot exactly which columns you want.

Use prompts like:

```text
Analyze r/SkincareAddiction posts from this week.
Send the result as an Excel file.
Columns: subreddit, title, score, num_comments, author, topic, sentiment, recommendation.
```

```text
Research Reddit discussions about acne patches.
Create an Excel report with columns: title, subreddit, score, num_comments, pain_point, buying_signal, suggested_marketing_angle.
```

This works better than a vague prompt like `make a sheet`.

### Step B6: Stop and Restart

Stop:

- press `Ctrl + C`

Restart:

```bash
uv run python slack_bot.py
```

If you think another copy is running:

```bash
pkill -f slack_bot.py
uv run python slack_bot.py
```

## Common Problems

### Problem 1: `Unhandled request ... app_mention`

This happens when the Slack bot does not handle `app_mention`.

In this repo, the current `slack_bot.py` already fixes that.

If you still see it:

- make sure you are running the latest `slack_bot.py`
- restart the bot

### Problem 2: Bot works in DMs but not in public channels

Check:

- the app was reinstalled after any scope or event changes
- `app_mention` is enabled
- `message.channels` is enabled
- `channels:history` scope exists
- bot was invited to the channel
- you mentioned the bot

### Problem 3: Bot works in DMs but not in private channels

Check:

- the app was reinstalled after any scope or event changes
- `message.groups` is enabled
- `groups:history` exists
- bot was invited to the private channel
- you mentioned the bot

### Problem 4: `apps.connections.open` shows `invalid_auth`

This means `SLACK_APP_TOKEN` is wrong or expired.

Fix:

1. open `Socket Mode`
2. generate a new app-level token
3. add `connections:write`
4. copy the new `xapp-` token
5. replace `SLACK_APP_TOKEN`
6. restart the bot

### Problem 5: Hermes says `slack-bolt not installed`

Fix:

```bash
~/.hermes/hermes-agent/venv/bin/python -m ensurepip --upgrade
~/.hermes/hermes-agent/venv/bin/python -m pip install slack-bolt
```

### Problem 6: Reddit tools are missing or only generic meta-tools appear

Check:

- `COMPOSIO_API_KEY` is correct
- `COMPOSIO_TOOLKITS=reddit` is set
- Reddit is connected in Composio
- restart the bot
- send `tools` in Slack to inspect tool access

Healthy output should include Reddit tools such as:

- `REDDIT_SEARCH_ACROSS_SUBREDDITS`
- `REDDIT_GET_SUBREDDIT_RULES`
- `REDDIT_RETRIEVE_REDDIT_POST`
- `REDDIT_POST_REDDIT_COMMENT`

If you only see `COMPOSIO_MANAGE_CONNECTIONS`, `COMPOSIO_MULTI_EXECUTE_TOOL`, and similar entries, you are likely running an older bot process.

### Problem 7: Duplicate replies

Cause:

- more than one Slack responder is running for the same app

Common causes:

- more than one `slack_bot.py` process is running
- Hermes Slack gateway is also running against the same Slack app

Fix for custom `slack_bot.py`:

```bash
pkill -f "hermes_cli.main gateway run"
pkill -f slack_bot.py
uv run python slack_bot.py
```

If you intentionally want Hermes gateway too, use a different Slack app for it.

### Problem 8: Raw lines like `browser_navigate` or `skills_list` appear in Slack

Cause:

- Hermes gateway or another Slack responder is still replying directly
- an older bot process is still running

Fix:

```bash
pkill -f "hermes_cli.main gateway run"
pkill -f slack_bot.py
uv run python slack_bot.py
```

### Problem 9: Bot starts but says you are not allowed yet

Cause:

- `SLACK_ALLOWED_USERS` is blank and no Slack admin has claimed access yet
- or you are not in the current allowlist

Fix:

1. open a DM with the bot
2. if this is the first setup, send `admin claim`
3. if an admin already exists, ask them to DM the bot with `allowlist add <@your_name>`
4. send `allowlist list` in DM to verify who is allowed

## Final Checklist

Before calling your Slack bot fully ready, confirm all of these:

1. Slack app created from scratch
2. Bot token scopes added
3. Socket Mode enabled
4. `SLACK_BOT_TOKEN` is valid
5. `SLACK_APP_TOKEN` is valid
6. Event Subscriptions enabled
7. `message.im`, `message.channels`, `message.groups`, and `app_mention` added
8. Messages Tab enabled
9. App installed to workspace
10. allowlisted user IDs are correct
11. Reddit account is connected in Composio if using `slack_bot.py`
12. Slack bot starts without warnings
13. DM test works
14. Public channel mention test works
15. Private channel mention test works
16. `tools` shows real Reddit tools, not only generic Composio meta-tools
17. `hermes: rewrite this in simpler language` works without duplicate replies

## Which Route Should You Use?

Use `Hermes Gateway` if:

- you want the fastest setup
- you want Hermes-managed messaging
- you do not need custom per-user Composio logic in code

Use `slack_bot.py` if:

- you want direct Composio integration in Python
- you want Hermes available as the internal first-pass orchestrator without running a second Slack responder
- you want a Reddit-specific Slack bot
- you want behavior closer to your `discord_bot.py`
- you want more control over how the Slack bot works
