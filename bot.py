import os
import discord
import requests
from discord.ext import commands

# --- Environment Variables ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def hello(ctx):
    await ctx.send("👋 Hello! I’m CineAI — your AI movie assistant bot!")

@bot.command()
async def idea(ctx, *, topic: str):
    """Use Gemini to generate a creative video idea"""
    await ctx.send(f"🧠 Thinking of a movie idea for: **{topic}** ... please wait ⏳")

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {"parts": [{"text": f"Create a cinematic short film idea about {topic}."}]}
            ]
        }

        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        idea_text = result["candidates"][0]["content"]["parts"][0]["text"]

        await ctx.send(f"🎬 **Idea:** {idea_text}")

    except Exception as e:
        await ctx.send(f"❌ Failed to generate idea: {e}")

@bot.command()
async def video(ctx, *, prompt: str):
    """Generate AI video using Hugging Face"""
    await ctx.send(f"🎬 Generating video for: **{prompt}** ... please wait ⏳")

    url = "https://api-inference.huggingface.co/models/ali-vilab/text-to-video-ms-1.7b"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {"inputs": prompt}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=600)
        if response.status_code == 200:
            video_bytes = response.content
            filename = "ai_video.mp4"
            with open(filename, "wb") as f:
                f.write(video_bytes)
            await ctx.send(file=discord.File(filename))
        else:
            await ctx.send(f"⚠️ API error ({response.status_code}): {response.text[:200]}")
    except Exception as e:
        await ctx.send(f"❌ Failed to generate video: {e}")

# --- Run Bot ---
if not DISCORD_TOKEN:
    print("❌ ERROR: DISCORD_TOKEN not found.")
else:
    bot.run(DISCORD_TOKEN)
