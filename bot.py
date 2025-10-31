import os
import discord
from discord.ext import commands

# --- Load environment variable ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")  # The key name only, not the token itself!

# --- Bot setup ---
intents = discord.Intents.default()
intents.message_content = True  # Needed for reading messages
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")


@bot.command()
async def hello(ctx):
    await ctx.send("👋 Hello! I’m CineAI — your movie assistant bot!")


@bot.command()
async def about(ctx):
    await ctx.send("🎬 I can create AI-powered videos and more! Stay tuned for updates!")


# --- Run bot ---
if not DISCORD_TOKEN:
    print("❌ ERROR: DISCORD_TOKEN not found in environment variables.")
else:
    bot.run(DISCORD_TOKEN)
