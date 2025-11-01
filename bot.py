import os
import discord
from discord.ext import commands
from video_maker import VideoMaker

TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

intents = discord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
video_maker = VideoMaker(gemini_api_key=GEMINI_API_KEY)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")


@bot.command(name="video")
async def make_video(ctx, *, prompt: str):
    """Generate an AI video from a text prompt."""
    await ctx.send(f"🎬 Generating a video for: **{prompt}** — please wait...")

    try:
        # Generate video in background thread
        from asyncio import to_thread
        output_path = await to_thread(video_maker.make_video, prompt)

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        if size_mb < 24:
            await ctx.send(file=discord.File(output_path))
        else:
            await ctx.send(f"✅ Video generated ({size_mb:.1f} MB) but too large to upload. Saved at: `{output_path}`")

    except Exception as e:
        await ctx.send(f"❌ Error: {e}")
        print("❌ Failed to generate video:", e)


bot.run(TOKEN)
