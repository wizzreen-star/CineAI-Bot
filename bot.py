import os
import discord
from discord.ext import commands
from video_maker import VideoMaker

TOKEN = os.getenv("DISCORD_TOKEN")  # or paste your token directly (not recommended)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Enable message content intent so the bot can read user messages
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

video_maker = VideoMaker(gemini_api_key=GEMINI_API_KEY)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} — CineAI is ready!")


# ---------------------------------------------------------
# 🎬 Command: !video <prompt>
# ---------------------------------------------------------
@bot.command(name="video")
async def make_video(ctx, *, prompt: str):
    """Create an AI-generated video."""
    await ctx.send(f"🎥 Generating video for: **{prompt}** … this may take 1–2 minutes")

    def notify(msg):
        try:
            import asyncio
            asyncio.run_coroutine_threadsafe(ctx.send(msg), bot.loop)
        except Exception as e:
            print("Notify error:", e)

    try:
        output_path = video_maker.make_video(prompt, notify_func=notify)
        await ctx.send("✅ Video created successfully!", file=discord.File(output_path))
    except Exception as e:
        await ctx.send(f"❌ Failed to generate video: {e}")
        print("Error:", e)


# ---------------------------------------------------------
# 🏓 Simple test command
# ---------------------------------------------------------
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("🏓 Pong!")


if __name__ == "__main__":
    print("🚀 Starting CineAI bot...")
    bot.run(TOKEN)
