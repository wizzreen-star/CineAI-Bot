# bot.py
import os
from threading import Thread
from flask import Flask, Response
from discord.ext import commands
import discord
from video_maker import VideoMaker

# -----------------------
# Config (set in Render)
# -----------------------
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")         # required
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")       # required for Gemini features (text/images/tts)
PORT = int(os.environ.get("PORT", 10000))

if not DISCORD_TOKEN:
    print("❌ ERROR: set DISCORD_TOKEN in environment variables.")
if not GEMINI_API_KEY:
    print("⚠️ Warning: GEMINI_API_KEY not set — the bot will use fallbacks for images/tts.")

# -----------------------
# Discord bot
# -----------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

video_maker = VideoMaker(gemini_api_key=GEMINI_API_KEY)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (id={bot.user.id}) — CineAI ready.")

@bot.command(name="hello")
async def hello(ctx):
    await ctx.send("👋 Hello! I’m CineAI — send `!video <prompt>` to generate a short AI video.")

@bot.command(name="video")
async def video_cmd(ctx, *, prompt: str):
    """
    Usage: !video <prompt>
    Example: !video a dog running on a beach at sunset
    """
    # notify user
    await ctx.send(f"🎬 Generating a video for: **{prompt}** — this may take 30s–5m depending on resources.")

    # create video using VideoMaker (runs heavy work in background threads)
    try:
        out_path = await video_maker.make_video_for_prompt(prompt, notify_func=lambda s: ctx.send(s))
    except Exception as e:
        await ctx.send(f"❌ Failed to generate video: {e}")
        return

    # send the final video (if not larger than discord limit)
    try:
        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        if size_mb < 24:
            await ctx.send(file=discord.File(out_path))
        else:
            await ctx.send(f"✅ Video created: `{out_path}` ({size_mb:.1f} MB). It's available on the server.")
    except Exception as e:
        await ctx.send(f"✅ Video created but failed to upload to Discord: {e}\nSaved at `{out_path}`")

# -----------------------
# Flask health endpoint for Render
# -----------------------
app = Flask("cineai")
@app.route("/")
def index():
    return Response("CineAI bot running", mimetype="text/plain")

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

def run_discord():
    if not DISCORD_TOKEN:
        print("❌ No DISCORD_TOKEN; exiting bot.")
        return
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    # start Flask so Render sees a web service
    Thread(target=run_flask, daemon=True).start()
    run_discord()
