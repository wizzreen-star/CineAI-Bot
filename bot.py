# ================================================================
# 🎬 CineAI Discord Bot — Auto Video Maker (Text ➜ Speech ➜ Video)
# ================================================================

import os
import asyncio
import uuid
import textwrap
from io import BytesIO
from pathlib import Path
from threading import Thread

import discord
from discord.ext import commands
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp
from flask import Flask, Response

# Optional: Use Gemini for smart script generation
try:
    import google.generativeai as genai
    HAVE_GEMINI = True
except Exception:
    HAVE_GEMINI = False

# -------------------
# Configuration
# -------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")        # ⚙️ Required
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")      # Optional
VIDEO_DIR = Path("videos")
VIDEO_DIR.mkdir(exist_ok=True)

# -------------------
# Discord Setup
# -------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

if HAVE_GEMINI and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print("⚠️ Gemini setup failed:", e)
        HAVE_GEMINI = False


# -------------------
# Script Generation
# -------------------
def generate_script(prompt: str) -> str:
    """Generate a video script using Gemini or fallback."""
    if HAVE_GEMINI and GEMINI_API_KEY:
        try:
            response = genai.GenerativeModel("gemini-pro").generate_content(
                f"Write a short video script (60-90 seconds) about: {prompt}."
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            print("⚠️ Gemini failed, using fallback:", e)

    # Fallback if Gemini not available or errors
    return (
        f"🎬 Title: {prompt}\n\n"
        "Scene 1: Quick intro explaining the topic.\n"
        "Scene 2: Main idea in simple words.\n"
        "Scene 3: A visual or fun example.\n"
        "Scene 4: Final line or call to action.\n"
    )


# -------------------
# Text → Image Helper
# -------------------
def split_text_into_segments(text: str, max_chars=160):
    """Split text into small pieces for each slide."""
    lines = text.split("\n")
    chunks = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        for chunk in textwrap.wrap(line, width=70):
            chunks.append(chunk)
    return chunks or ["(empty)"]

def create_image(text: str, size=(1280, 720)):
    """Make a slide image with centered text."""
    W, H = size
    img = Image.new("RGB", size, color=(10, 10, 10))
    draw = ImageDraw.Draw(img)

    # Try loading a decent font
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 42) if os.path.exists(font_path) else ImageFont.load_default()

    lines = textwrap.wrap(text, width=40)
    total_h = sum(font.getbbox(line)[3] for line in lines) + 10 * len(lines)
    y = (H - total_h) // 2

    for line in lines:
        w = font.getlength(line)
        draw.text(((W - w) / 2, y), line, font=font, fill=(240, 240, 240))
        y += font.getbbox(line)[3] + 10

    return img


# -------------------
# Build Video
# -------------------
async def build_video(prompt: str, script: str, lang="en") -> Path:
    """Create a simple narrated slideshow video."""
    uid = uuid.uuid4().hex[:8]
    audio_path = VIDEO_DIR / f"{uid}.mp3"
    video_path = VIDEO_DIR / f"{uid}.mp4"

    # Generate voice with gTTS
    def make_tts():
        tts = gTTS(script, lang=lang)
        tts.save(str(audio_path))
    await asyncio.to_thread(make_tts)

    audio_clip = mp.AudioFileClip(str(audio_path))
    duration = audio_clip.duration

    # Make slides
    slides = split_text_into_segments(script)
    per_slide = duration / max(len(slides), 1)
    clips = []

    for s in slides:
        img = create_image(s)
        bio = BytesIO()
        img.save(bio, format="PNG")
        bio.seek(0)
        clip = mp.ImageClip(bio).set_duration(per_slide)
        clips.append(clip)

    final_clip = mp.concatenate_videoclips(clips, method="compose")
    final_clip = final_clip.set_audio(audio_clip)
    final_clip = final_clip.set_fps(24)

    # Save video
    def write_file():
        final_clip.write_videofile(str(video_path), codec="libx264", audio_codec="aac", verbose=False, logger=None)
    await asyncio.to_thread(write_file)

    audio_clip.close()
    return video_path


# -------------------
# Discord Commands
# -------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} — ready to make videos!")

@bot.command(name="hello")
async def hello(ctx):
    await ctx.send("👋 Hey! I’m CineAI — I can make short videos from your ideas!")

@bot.command(name="video")
async def make_video(ctx, *, prompt: str):
    """Make a short AI-generated video from your idea."""
    await ctx.send(f"🎬 Generating a video for: **{prompt}** — please wait...")

    # 1. Get script (Gemini or fallback)
    script = await asyncio.to_thread(generate_script, prompt)

    # 2. Build the video
    try:
        video_path = await build_video(prompt, script)
    except Exception as e:
        await ctx.send(f"❌ Failed to build video: {e}")
        return

    # 3. Upload or show path
    try:
        size_mb = video_path.stat().st_size / (1024 * 1024)
        if size_mb < 24:
            await ctx.send(file=discord.File(str(video_path)))
        else:
            await ctx.send(f"✅ Video created ({size_mb:.1f} MB). Too large to upload, but saved at `{video_path}`.")
    except Exception as e:
        await ctx.send(f"✅ Video ready but upload failed: {e}")


# -------------------
# Flask (for Render)
# -------------------
app = Flask("cineai")

@app.route("/")
def index():
    return Response("✅ CineAI bot running!", mimetype="text/plain")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def run_discord():
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not set in environment.")
        return
    bot.run(DISCORD_TOKEN)

# -------------------
# Start Everything
# -------------------
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    run_discord()
