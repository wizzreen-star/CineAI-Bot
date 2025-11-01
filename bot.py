import os
import asyncio
from threading import Thread
from flask import Flask, Response
import discord
from discord.ext import commands
from video_maker import VideoMaker

# ----------------------------
# Config
# ----------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

video_maker = VideoMaker(gemini_api_key=GEMINI_API_KEY)

# ----------------------------
# Discord Setup
# ----------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} — CineAI is ready!")

@bot.command()
async def make(ctx, *, prompt: str):
    await ctx.send(f"🎬 Generating a video for: **{prompt}** — please wait...")

    def notify(msg):
        asyncio.run_coroutine_threadsafe(ctx.send(msg), bot.loop)

    try:
        video_path = video_maker.make_video_for_prompt(prompt, notify_func=notify)
        if video_path and os.path.exists(video_path):
            await ctx.send("✅ Done! Here's your video:", file=discord.File(video_path))
        else:
            await ctx.send("❌ Failed to generate video.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

# ----------------------------
# Flask Server (for Render)
# ----------------------------
app = Flask("cineai")

@app.route("/")
def index():
    return Response("✅ CineAI Bot running!", mimetype="text/plain")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def run_discord():
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN missing.")
        return
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    run_discord()
