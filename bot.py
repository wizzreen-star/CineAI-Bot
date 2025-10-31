import discord
from discord.ext import commands
from gtts import gTTS
import moviepy.editor as mp
import os

# --- SETUP ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- BASIC COMMANDS ---
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def hello(ctx):
    await ctx.send("👋 Hello! I’m CineAI — your cinema assistant!")

@bot.command()
async def about(ctx):
    await ctx.send("🎬 I can create videos, generate voices, and more movie magic! Type `!video <text>` to create a text-to-video clip.")

# --- TEXT TO VIDEO COMMAND ---
@bot.command()
async def video(ctx, *, text: str):
    await ctx.send("🎥 Creating your video... please wait a few seconds!")

    # Generate voice
    tts = gTTS(text)
    tts.save("voice.mp3")

    # Create a black background video
    clip = mp.ColorClip(size=(720, 480), color=(0, 0, 0), duration=5)
    audio = mp.AudioFileClip("voice.mp3")
    clip = clip.set_audio(audio)

    # Add text overlay
    txt = mp.TextClip(text, fontsize=40, color='white')
    txt = txt.set_duration(5).set_position("center")
    final = mp.CompositeVideoClip([clip, txt])

    # Export video
    final.write_videofile("output.mp4", fps=24, codec="libx264", audio_codec="aac")

    await ctx.send(file=discord.File("output.mp4"))

    # Clean up
    os.remove("voice.mp3")
    os.remove("output.mp4")

# --- RUN THE BOT ---
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if TOKEN is None:
    print("❌ No bot token found! Please set DISCORD_BOT_TOKEN in your environment variables.")
else:
    bot.run(TOKEN)
