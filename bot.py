import os
import discord
from discord.ext import commands
from flask import Flask, Response
from threading import Thread
import asyncio
from video_maker import VideoMaker  # ✅ must exist in your repo (video_maker.py)

# ===============================
# 🔧 ENVIRONMENT VARIABLES
# ===============================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN or not GEMINI_API_KEY:
    raise ValueError("❌ Missing DISCORD_TOKEN or GEMINI_API_KEY in environment variables!")

# ===============================
# 🌐 FLASK HEALTH CHECK (REQUIRED BY RENDER)
# ===============================
app = Flask("cineai")

@app.route("/")
def index():
    return Response("✅ CineAI bot is running", mimetype="text/plain")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False)

# ===============================
# 🤖 DISCORD BOT SETUP
# ===============================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

video_maker = VideoMaker(GEMINI_API_KEY)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} — CineAI is ready!")

# ===============================
# 🎬 VIDEO COMMAND
# ===============================
@bot.command()
async def video(ctx, *, prompt: str):
    await ctx.send(f"🎬 Generating a video for: **{prompt}** — please wait...")

    try:
        def notify(msg):
            asyncio.run_coroutine_threadsafe(ctx.send(msg), bot.loop)

        video_path = video_maker.make_video(prompt, notify_func=notify)

        if not video_path or not os.path.exists(video_path):
            await ctx.send("❌ Failed to create video.")
            return

        await ctx.send(file=discord.File(video_path))
        os.remove(video_path)

    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

# ===============================
# 🚀 START BOTH FLASK + DISCORD
# ===============================
def run_discord():
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    # Start Flask first — so Render detects the open port
    Thread(target=run_flask, daemon=True).start()

    # Short delay so Render sees open port before bot runs
    import time
    time.sleep(1.0)

    # Run the Discord bot (blocking)
    run_discord()
