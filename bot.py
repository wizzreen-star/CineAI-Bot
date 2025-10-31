import os
import discord
import requests
from discord.ext import commands

# Environment Variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# Discord Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🤖 Bot is online as {bot.user}")

@bot.command()
async def video(ctx, *, prompt: str):
    await ctx.send(f"🎬 Generating video for: `{prompt}` ... please wait ⏳")

    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": prompt}

    response = requests.post(
        "https://api-inference.huggingface.co/models/damo-vilab/text-to-video-ms-1.7b",
        headers=headers,
        json=payload,
    )

    if response.status_code == 200:
        video_path = "output.mp4"
        with open(video_path, "wb") as f:
            f.write(response.content)
        await ctx.send(file=discord.File(video_path))
    else:
        await ctx.send(f"❌ Error: {response.text}")

bot.run(DISCORD_TOKEN)
