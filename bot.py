# ================================================================
# 🎬 CineAI Discord Bot — Auto Video Maker (Gemini + gTTS + MoviePy)
# ================================================================

import os
import asyncio
from threading import Thread
from flask import Flask, Response
import discord
from discord.ext import commands
from video_maker import VideoMaker

# -------------------
# Load API keys
# -------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# -------------------
# Flask for Render keep-alive
# -------------------
app = Flask(__name__)

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

video_maker = VideoMaker(gemini_api_key=GEMINI_API_KEY)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} — ready to create videos!")

@bot.command(name="hello")
async def hello(ctx):
    await ctx.send("👋 Hey! I’m CineAI — I can make real AI videos from your ideas!")

@bot.command(name="video")
async def video(ctx, *, prompt: str):
    """Create an AI-generated video based on your text prompt."""
    await ctx.send(f"🎬 Generating a **real AI video** for: **{prompt}** — please wait...")

    try:
        # make_video() is the correct function name
        output_path = await asyncio.to_thread(video_maker.make_video, prompt)

        if not os.path.exists(output_path):
            await ctx.send("❌ Error: video file not found.")
            return

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        if size_mb < 24:
            await ctx.send(file=discord.File(output_path))
        else:
            await ctx.send(f"✅ Video created ({size_mb:.1f} MB). Too large to upload but saved at: `{output_path}`")

    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

# -------------------
# Start both Flask + Discord
# -------------------
def run_discord():
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not found in environment!")
        return
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    run_discord()
