#!/bin/bash

# Discord Bot Installation & Setup Script

echo "🚀 Discord Bot with Composio - Setup Script"
echo "==========================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    exit 1
fi

# Check for required API keys
if ! grep -q "COMPOSIO_API_KEY" .env; then
    echo "❌ COMPOSIO_API_KEY not found in .env"
    exit 1
fi

if ! grep -q "OPENAI_API_KEY" .env; then
    echo "❌ OPENAI_API_KEY not found in .env"
    exit 1
fi

echo "✅ Found API keys in .env"
echo ""

# Check if DISCORD_BOT_TOKEN is set
if ! grep -q "DISCORD_BOT_TOKEN" .env; then
    echo "⚠️  DISCORD_BOT_TOKEN not found in .env"
    echo "Please add it manually:"
    echo ""
    echo "   1. Get a Discord bot token from: https://discord.com/developers/applications"
    echo "   2. Add this line to .env:"
    echo "      DISCORD_BOT_TOKEN=your_bot_token_here"
    echo ""
    exit 1
fi

if grep -q "your_discord_bot_token_here" .env; then
    echo "⚠️  DISCORD_BOT_TOKEN is not set (still has placeholder)"
    exit 1
fi

echo "✅ DISCORD_BOT_TOKEN found in .env"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
if command -v uv &> /dev/null; then
    uv sync
else
    pip install discord.py aiohttp
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎉 To start your Discord bot, run:"
echo "   python discord_bot.py"
echo ""
