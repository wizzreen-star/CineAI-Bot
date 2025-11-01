# ================================================================
# 🎬 CineAI Discord Bot — Auto Video Maker
# ================================================================

import os
import asyncio
from threading import Thread
from flask import Flask, Response
import discord
from discord.ext import commands

from video_maker import make_video  # 👈 import from your video_maker.py

# -------------------
# Configuration
# -------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # optional

# -------------------
# Discord Setup
# -------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------
# Events
# -------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} — ready to make videos!")

# -------------------
# Commands
# -------------------
@bot.command(name="video")
async def create_video(ctx, *, prompt: str):
    """Generate an AI video from a topic"""
    await ctx.send(f"🎬 Generating a video for: **{prompt}** — please wait...")

    try:
        # use make_video() from video_maker.py
        video_path = await asyncio.to_thread(make_video, prompt, prompt)
        await ctx.send(file=discord.File(video_path))
    except Exception as e:
        await ctx.send(f"❌ Failed to make video: {e}")

# -------------------
# Flask (for Render)
# -------------------
app = Flask("cineai")

@app.route("/")
def index():
    return Response("✅ CineAI bot running!", mimetype="text/plain")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def run_discord():
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not set in environment.")
        return
    bot.run(DISCORD_TOKEN)

# -------------------
# Start both
# -------------------
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    run_discord()
