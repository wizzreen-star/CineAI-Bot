import os
import discord
from discord.ext import commands
import requests
import time

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

PIKA_API_KEY = os.getenv("PIKA_API_KEY")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def sora(ctx, *, prompt: str):
    """Generate an AI video using Pika Labs"""
    await ctx.send(f"🎬 Generating video for: **{prompt}** ... please wait 30–60 seconds")

    # Step 1: Request video generation
    headers = {
        "Authorization": f"Bearer {PIKA_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "pika-v1",  # Pika Labs model
        "prompt": prompt
    }

    response = requests.post("https://api.pika.art/generate", headers=headers, json=data)

    if response.status_code != 200:
        await ctx.send("❌ Error connecting to Pika API.")
        return

    job = response.json()
    job_id = job.get("id")

    await ctx.send("⏳ Video generation started... waiting for completion")

    # Step 2: Poll for result
    video_url = None
    for _ in range(40):  # Wait up to ~80 seconds
        status = requests.get(f"https://api.pika.art/status/{job_id}", headers=headers)
        result = status.json()

        if result.get("status") == "completed":
            video_url = result["output"]["video"]
            break
        elif result.get("status") == "failed":
            await ctx.send("⚠️ Video generation failed.")
            return

        time.sleep(2)

    if video_url:
        await ctx.send("✅ Done! Here's your AI-generated video:")
        await ctx.send(video_url)
    else:
        await ctx.send("⏰ Timed out waiting for video. Try again later!")

bot.run(os.getenv("DISCORD_TOKEN"))
