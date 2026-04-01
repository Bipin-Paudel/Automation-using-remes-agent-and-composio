import os
import asyncio
import atexit
from typing import Any, Awaitable, Callable
import discord
from discord.ext import commands
from dotenv import load_dotenv
from composio import Composio
from agents import Agent, Runner, SQLiteSession
from composio_openai_agents import OpenAIAgentsProvider

# Load environment variables
load_dotenv()

# Initialize Composio
composio = Composio(provider=OpenAIAgentsProvider())

# Create Discord bot with command prefix
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Store sessions per user
user_sessions = {}
memory_sessions = {}

LOCK_FILE = ".discord_bot.lock"


def _tool_name(tool: Any) -> str:
    """Return tool name for both object-style and dict-style tool payloads."""
    if isinstance(tool, dict):
        return str(tool.get("name") or "").strip()
    return str(getattr(tool, "name", "") or "").strip()


def _tool_description(tool: Any) -> str:
    """Return tool description for both object-style and dict-style tool payloads."""
    if isinstance(tool, dict):
        return str(tool.get("description") or "")
    return str(getattr(tool, "description", "") or "")


def _normalized_tool_names(tools: list[Any]) -> list[str]:
    """Collect tool names and filter out missing/empty entries."""
    return [name for name in (_tool_name(tool) for tool in tools) if name]


def get_or_create_session(user_id: str):
    """Get or create a Composio session for a user"""
    if user_id not in user_sessions:
        user_sessions[user_id] = composio.create(user_id=user_id)
    return user_sessions[user_id]


def get_or_create_memory(user_id: str) -> SQLiteSession:
    """Get or create per-user conversation memory for the agent runner."""
    if user_id not in memory_sessions:
        memory_sessions[user_id] = SQLiteSession(f"discord_{user_id}")
    return memory_sessions[user_id]


async def run_user_task(user_id: str, task: str) -> str:
    """Run a user task through the Composio agent and return final text."""
    session = get_or_create_session(user_id)
    memory = get_or_create_memory(user_id)
    tools = session.tools()

    agent = Agent(
        name="Discord Assistant",
        instructions=(
            "You are a helpful Discord assistant powered by Composio. "
            "You can use available tools to help users with tasks. "
            "Keep responses concise and friendly for Discord."
        ),
        model="gpt-5.2",
        tools=tools,
    )

    result = await asyncio.to_thread(
        Runner.run_sync,
        starting_agent=agent,
        input=task,
        session=memory,
    )
    return str(result.final_output or "No response generated")


async def send_chunked_response(
    send_embed: Callable[..., Awaitable[discord.Message]], response_text: str
) -> None:
    """Send long responses in Discord-safe chunks as embeds."""
    if len(response_text) > 1900:
        chunks = [
            response_text[i : i + 1900] for i in range(0, len(response_text), 1900)
        ]
        for i, chunk in enumerate(chunks):
            if i == 0:
                embed = discord.Embed(
                    title="✅ Task Completed",
                    description=chunk,
                    color=discord.Color.green(),
                )
                embed.set_footer(text=f"Response 1 of {len(chunks)}")
                await send_embed(embed=embed)
            else:
                embed = discord.Embed(description=chunk, color=discord.Color.green())
                embed.set_footer(text=f"Response {i + 1} of {len(chunks)}")
                await send_embed(embed=embed)
        return

    embed = discord.Embed(
        title="✅ Task Completed",
        description=response_text,
        color=discord.Color.green(),
    )
    await send_embed(embed=embed)


async def safe_defer(interaction: discord.Interaction) -> bool:
    """Acknowledge slash commands safely to avoid Unknown interaction crashes."""
    if interaction.response.is_done():
        return True
    try:
        await interaction.response.defer(thinking=True)
        return True
    except discord.NotFound:
        # Interaction expired before we could acknowledge it.
        return False
    except Exception:
        return False


@bot.event
async def on_ready():
    """Called when bot successfully connects to Discord"""
    print(f"✅ Bot logged in as {bot.user}")
    print("✅ Bot is ready to use!")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")


@bot.tree.command(name="help", description="Show available commands")
async def help_command(interaction: discord.Interaction):
    """Show help message"""
    embed = discord.Embed(
        title="🤖 Available Commands",
        description="Here are the commands you can use with Composio:",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="/ask <task>",
        value="Ask the AI assistant to help with a task using Composio tools",
        inline=False,
    )
    embed.add_field(
        name="/tools", value="List all available Composio tools", inline=False
    )
    embed.add_field(name="/help", value="Show this help message", inline=False)
    embed.set_footer(text="Powered by Composio & OpenAI")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="tools", description="List available Composio tools")
async def list_tools(interaction: discord.Interaction):
    """List available Composio tools"""
    if not await safe_defer(interaction):
        return

    try:
        session = get_or_create_session(str(interaction.user.id))
        tools = session.tools()

        tool_names = _normalized_tool_names(tools or [])

        if not tool_names:
            await interaction.followup.send("❌ No tools available")
            return

        # Create embed for tools
        embed = discord.Embed(
            title="🛠️ Available Composio Tools",
            description=f"Total: {len(tool_names)} tools",
            color=discord.Color.green(),
        )

        # Split tools into chunks for discord message limit
        for i in range(0, len(tool_names), 10):
            chunk = tool_names[i : i + 10]
            embed.add_field(
                name=f"Tools {i + 1}-{min(i + 10, len(tool_names))}",
                value="\n".join(f"• {tool}" for tool in chunk),
                inline=False,
            )

        embed.set_footer(text="Use /ask to leverage these tools")
        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)[:100]}")


@bot.tree.command(name="ask", description="Ask the AI assistant to help with a task")
@discord.app_commands.describe(task="What would you like me to help with?")
async def ask_command(interaction: discord.Interaction, task: str):
    """Ask the AI assistant to complete a task using Composio tools"""
    if not await safe_defer(interaction):
        if interaction.channel:
            await interaction.channel.send(
                f"{interaction.user.mention} your command expired before I could respond. Please run `/ask` again."
            )
        return

    try:
        user_id = str(interaction.user.id)

        # Show that we're processing
        embed = discord.Embed(
            title="⏳ Processing your request...",
            description=f"Task: {task[:100]}...",
            color=discord.Color.yellow(),
        )
        await interaction.followup.send(embed=embed)

        response_text = await run_user_task(user_id, task)
        await send_chunked_response(interaction.followup.send, response_text)

    except Exception as e:
        error_msg = str(e)[:1900]
        embed = discord.Embed(
            title="❌ Error", description=error_msg, color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)


@bot.event
async def on_message(message: discord.Message):
    """Allow direct chat with the bot in DMs or when mentioned in servers."""
    if message.author.bot:
        return

    task = ""
    is_dm = isinstance(message.channel, discord.DMChannel)

    if is_dm:
        task = message.content.strip()
    else:
        if bot.user and bot.user.mentioned_in(message):
            mention_1 = message.content.replace(f"<@{bot.user.id}>", "")
            mention_2 = mention_1.replace(f"<@!{bot.user.id}>", "")
            task = mention_2.strip()

    if task:
        try:
            processing_embed = discord.Embed(
                title="⏳ Processing your request...",
                description=f"Task: {task[:100]}...",
                color=discord.Color.yellow(),
            )
            await message.channel.send(embed=processing_embed)

            response_text = await run_user_task(str(message.author.id), task)
            await send_chunked_response(message.channel.send, response_text)
        except Exception as e:
            error_msg = str(e)[:1900]
            error_embed = discord.Embed(
                title="❌ Error", description=error_msg, color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)

    await bot.process_commands(message)


def _is_process_running(pid: int) -> bool:
    """Check whether a process ID exists without killing it."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_single_instance_lock() -> bool:
    """Ensure only one bot process is active to prevent duplicate responses."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r", encoding="utf-8") as f:
                existing_pid = int(f.read().strip())
            if _is_process_running(existing_pid):
                return False
        except Exception:
            # Corrupt lock file: overwrite it below.
            pass

    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))

    def _cleanup_lock() -> None:
        try:
            if os.path.exists(LOCK_FILE):
                with open(LOCK_FILE, "r", encoding="utf-8") as f:
                    pid_in_file = f.read().strip()
                if pid_in_file == str(os.getpid()):
                    os.remove(LOCK_FILE)
        except Exception:
            pass

    atexit.register(_cleanup_lock)
    return True


# Run the bot
if __name__ == "__main__":
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    if not discord_token:
        print("❌ Error: DISCORD_BOT_TOKEN not found in .env file")
        print("Please add your Discord bot token to .env")
        exit(1)

    if not acquire_single_instance_lock():
        print("❌ Another discord_bot.py instance is already running.")
        print("Stop the previous process first to avoid duplicate responses.")
        exit(1)

    bot.run(discord_token)
