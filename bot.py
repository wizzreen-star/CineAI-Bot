import os
import asyncio
from threading import Thread
from flask import Flask, Response
import discord
from discord.ext import commands
from video_maker import VideoMaker

# -------------------
# Environment setup
# -------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN:
    raise ValueError("❌ Missing DISCORD_TOKEN in environment variables")

# -------------------
# Flask for Render healthcheck
# -------------------
app = Flask("CineAI")

@app.route("/")
def index():
    return Response("✅ CineAI Bot is running!", mimetype="text/plain")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# -------------------
# Discord Bot Setup
# -------------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
video_maker = VideoMaker(gemini_api_key=GEMINI_API_KEY)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} — CineAI is ready!")

@bot.command(name="video")
async def video(ctx, *, prompt: str):
    async def notify(msg):
        await ctx.send(msg)

    await ctx.send(f"🎬 Generating a video for: **{prompt}** — please wait...")

    try:
        video_path = await video_maker.make_video(prompt, notify)
        await ctx.send(file=discord.File(video_path))
    except Exception as e:
        await ctx.send(f"❌ Failed to generate video: {e}")

# -------------------
# Start Flask + Bot
# -------------------
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    bot.run(DISCORD_TOKEN)
