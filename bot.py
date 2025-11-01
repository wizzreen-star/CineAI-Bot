# ================================================================
# 🎬 CineAI Discord Bot — Real AI Video Maker (Gemini + gTTS + MoviePy)
# ================================================================

import os
import asyncio
from threading import Thread
from flask import Flask, Response
import discord
from discord.ext import commands
from video_maker import VideoMaker  # ✅ import fixed

# -------------------
# Configuration
# -------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# -------------------
# Discord Setup
# -------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize the video maker
video_maker = VideoMaker(gemini_api_key=GEMINI_API_KEY)

# -------------------
# Discord Commands
# -------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} — CineAI is ready to make real videos!")

@bot.command(name="hello")
async def hello(ctx):
    await ctx.send("👋 Hey! I’m CineAI — your AI movie maker bot! Use `!video <your topic>` to create a video.")

@bot.command(name="video")
async def make_video(ctx, *, prompt: str):
    """Generate a full AI video."""
    await ctx.send(f"🎬 Generating a video for: **{prompt}** — please wait...")

    try:
        # Create the video
        output_path = await asyncio.to_thread(video_maker.make_video, prompt)
        size_mb = os.path.getsize(output_path) / (1024 * 1024)

        if size_mb < 24:
            await ctx.send(file=discord.File(output_path))
        else:
            await ctx.send(f"✅ Video generated ({size_mb:.1f} MB) but too large to upload. Saved at: `{output_path}`")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")
        print("❌ Failed to generate video:", e)

# -------------------
# Flask for Render Health
# -------------------
app = Flask("cineai")

@app.route("/")
def index():
    return Response("✅ CineAI bot is running!", mimetype="text/plain")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def run_discord():
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not found in environment variables!")
        return
    bot.run(DISCORD_TOKEN)

# -------------------
# Start Both Services
# -------------------
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    run_discord()
