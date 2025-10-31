import os
import discord
import requests
from discord.ext import commands

# --- Environment Variables ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")  # from Render
HF_API_KEY = os.getenv("HF_API_KEY")        # your Hugging Face token (hf_...)

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def hello(ctx):
    await ctx.send("👋 Hello! I’m CineAI — your movie assistant bot!")

@bot.command()
async def video(ctx, *, prompt: str):
    """Generate an AI video from a text prompt"""
    await ctx.send(f"🎬 Generating video for: **{prompt}** ... please wait ⏳")

    url = "https://api-inference.huggingface.co/models/ali-vilab/text-to-video-ms-1.7b"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {"inputs": prompt}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=600)

        if response.status_code == 200:
            filename = "ai_video.mp4"
            with open(filename, "wb") as f:
                f.write(response.content)
            await ctx.send(file=discord.File(filename))
        else:
            await ctx.send(f"⚠️ API error ({response.status_code}): {response.text[:200]}")

    except Exception as e:
        await ctx.send(f"❌ Failed to generate video: {e}")

# --- Run Bot ---
if not DISCORD_TOKEN:
    print("❌ ERROR: DISCORD_TOKEN not found in environment variables.")
else:
    bot.run(DISCORD_TOKEN)

from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "CineAI Bot is running!"

def run():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run).start()
