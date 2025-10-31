import os
import discord
import requests
from discord.ext import commands

# --- Environment Variables ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")  # from Render
PIKA_API_KEY = os.getenv("PIKA_API_KEY")    # from Pika Labs or Hugging Face

# --- Bot setup ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- On Ready Event ---
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# --- !hello command ---
@bot.command()
async def hello(ctx):
    await ctx.send("👋 Hello! I’m CineAI — your movie assistant bot!")

# --- !video command ---
@bot.command()
async def video(ctx, *, prompt: str):
    await ctx.send(f"🎬 Generating video for: `{prompt}` … please wait ⏳")

    # Example free AI video generation using Hugging Face Inference API
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/stabilityai/stable-video-diffusion-img2vid",
            headers={"Authorization": f"Bearer {PIKA_API_KEY}"},
            json={"inputs": prompt},
            timeout=300,
        )

        if response.status_code == 200:
            # Save video to file
            with open("output.mp4", "wb") as f:
                f.write(response.content)
            await ctx.send("✅ Done! Here's your video:", file=discord.File("output.mp4"))
        else:
            await ctx.send(f"⚠️ Error: {response.status_code}\n{response.text}")

    except Exception as e:
        await ctx.send(f"❌ Failed to generate video: {e}")

# --- Run bot ---
if DISCORD_TOKEN is None:
    print("❌ ERROR: DISCORD_TOKEN not found in environment variables.")
else:
    bot.run(DISCORD_TOKEN)
