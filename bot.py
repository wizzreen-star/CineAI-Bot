import discord
from discord.ext import commands
from gtts import gTTS
from moviepy.editor import TextClip, concatenate_videoclips, AudioFileClip
import os
import asyncio

# Load environment variables (if using Render)
from dotenv import load_dotenv
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def video(ctx, *, prompt: str):
    """Generate a simple AI video from text"""
    await ctx.send(f"🎬 Generating video for: **{prompt}** ...")

    try:
        # --- Step 1: Create audio from text ---
        tts = gTTS(prompt)
        audio_path = "speech.mp3"
        tts.save(audio_path)

        # --- Step 2: Create text-based frames ---
        clips = []
        words = prompt.split()
        step = max(1, len(words) // 5)
        for i in range(0, len(words), step):
            text = " ".join(words[:i+step])
            clip = TextClip(text, fontsize=50, color='white', bg_color='black', size=(1280, 720), duration=1)
            clips.append(clip)

        # --- Step 3: Combine all clips ---
        video = concatenate_videoclips(clips)
        video = video.set_audio(AudioFileClip(audio_path))

        output_path = "output.mp4"
        video.write_videofile(output_path, fps=24)

        await ctx.send(file=discord.File(output_path))

    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

    finally:
        # Clean up temporary files
        for f in ["speech.mp3", "output.mp4"]:
            if os.path.exists(f):
                os.remove(f)

bot.run(DISCORD_TOKEN)
