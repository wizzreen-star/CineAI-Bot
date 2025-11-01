# ================================================================
# 🎬 CineAI Discord Bot — Auto Video Maker (Gemini + Real Video)
# ================================================================

import os
import asyncio
from threading import Thread
from flask import Flask, Response
import discord
from discord.ext import commands

# Import your VideoMaker class
from video_maker import VideoMaker

# -------------------
# Configuration
# -------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# -------------------
# Flask (for Render uptime)
# -------------------
app = Flask("cineai")

@app.route("/")
def index():
    return Response("✅ CineAI bot running!", mimetype="text/plain")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# -------------------
# Discord Bot Setup
# -------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize video maker
video_maker = VideoMaker(gemini_api_key=GEMINI_API_KEY)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} — ready to create real videos!")

@bot.command(name="hello")
async def hello(ctx):
    await ctx.send("👋 Hey! I’m CineAI — I make real AI videos using Gemini!")

@bot.command(name="video")
async def make_video(ctx, *, prompt: str):
    """Generate a real AI video using Gemini."""
    await ctx.send(f"🎬 Generating a video for: **{prompt}** — please wait...")

    try:
        video_path = await video_maker.make_video_for_prompt(
            prompt,
            notify_func=lambda s: asyncio.create_task(ctx.send(s))
        )

        # Try sending the video file
        if os.path.exists(video_path):
            size_mb = os.path.getsize(video_path) / (1024 * 1024)
            if size_mb < 24:
                await ctx.send(file=discord.File(video_path))
            else:
                await ctx.send(f"✅ Video created ({size_mb:.1f} MB) — too large for Discord, saved at `{video_path}`.")
        else:
            await ctx.send("❌ Failed: no video file was generated.")

    except Exception as e:
        await ctx.send(f"❌ Error: {e}")
        print("Video generation error:", e)

# -------------------
# Start Flask + Discord
# -------------------
def run_discord():
    if not DISCORD_TOKEN:
        print("❌ Missing DISCORD_TOKEN in environment!")
        return
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    run_discord()
