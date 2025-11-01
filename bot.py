# ================================================================
# 🎬 CineAI Discord Bot — Auto Video Maker (Text ➜ Speech ➜ Video)
# ================================================================

import os
import asyncio
import uuid
import textwrap
from pathlib import Path
from threading import Thread

import discord
from discord.ext import commands
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp
from flask import Flask, Response

# Optional: Use Gemini for script generation
try:
    import google.generativeai as genai
    HAVE_GEMINI = True
except Exception:
    HAVE_GEMINI = False

# -------------------
# Config
# -------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN:
    raise ValueError("❌ Missing DISCORD_TOKEN in environment!")

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
# Script Generator
# -------------------
def generate_script(prompt: str) -> str:
    """Generate video narration text."""
    if HAVE_GEMINI and GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-pro")
            response = model.generate_content(
                f"Write a short engaging 1-minute video script about: {prompt}. Keep it natural, human-like, and conversational."
            )
            if hasattr(response, "text") and response.text:
                return response.text.strip()
        except Exception as e:
            print("⚠️ Gemini failed, using fallback:", e)

    # fallback script
    return (
        f"🎬 Title: {prompt}\n\n"
        "Scene 1: Quick introduction.\n"
        "Scene 2: Key idea explained simply.\n"
        "Scene 3: An example or comparison.\n"
        "Scene 4: Final thoughts and summary.\n"
    )


# -------------------
# Text → Image
# -------------------
def split_text_into_segments(text: str):
    """Split text for slides."""
    lines = text.split("\n")
    chunks = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        for chunk in textwrap.wrap(line, width=70):
            chunks.append(chunk)
    return chunks or ["(empty)"]

def create_image(text: str, size=(1280, 720)) -> Path:
    """Create an image with centered text and return its path."""
    W, H = size
    img = Image.new("RGB", size, color=(15, 15, 15))
    draw = ImageDraw.Draw(img)

    # Load font safely
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 42) if os.path.exists(font_path) else ImageFont.load_default()

    lines = textwrap.wrap(text, width=40)
    line_heights = [font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines]
    total_h = sum(line_heights) + 10 * len(lines)
    y = (H - total_h) // 2

    for line, h in zip(lines, line_heights):
        w = font.getlength(line)
        draw.text(((W - w) / 2, y), line, font=font, fill=(240, 240, 240))
        y += h + 10

    # Save to a temporary PNG
    temp_path = VIDEO_DIR / f"{uuid.uuid4().hex[:6]}.png"
    img.save(temp_path)
    return temp_path


# -------------------
# Video Builder
# -------------------
async def build_video(prompt: str, script: str, lang="en") -> Path:
    """Generate narrated video."""
    uid = uuid.uuid4().hex[:8]
    audio_path = VIDEO_DIR / f"{uid}.mp3"
    video_path = VIDEO_DIR / f"{uid}.mp4"

    # Step 1: Text → Speech
    def make_tts():
        tts = gTTS(script, lang=lang)
        tts.save(str(audio_path))
    await asyncio.to_thread(make_tts)

    # Step 2: Load audio
    audio_clip = mp.AudioFileClip(str(audio_path))
    duration = audio_clip.duration

    # Step 3: Create slides
    slides = split_text_into_segments(script)
    per_slide = duration / max(len(slides), 1)
    clips = []

    for s in slides:
        img_path = create_image(s)
        clip = mp.ImageClip(str(img_path)).set_duration(per_slide)
        clips.append(clip)

    # Step 4: Combine
    final_clip = mp.concatenate_videoclips(clips, method="compose")
    final_clip = final_clip.set_audio(audio_clip).set_fps(24)

    # Step 5: Save
    def write_file():
        final_clip.write_videofile(str(video_path), codec="libx264", audio_codec="aac", verbose=False, logger=None)
    await asyncio.to_thread(write_file)

    # Cleanup
    audio_clip.close()
    for clip in clips:
        try:
            os.remove(clip.filename)
        except Exception:
            pass

    return video_path


# -------------------
# Discord Commands
# -------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} — ready to make videos!")

@bot.command(name="hello")
async def hello(ctx):
    await ctx.send("👋 Hey! I’m CineAI — I can turn your ideas into short videos!")

@bot.command(name="video")
async def make_video(ctx, *, prompt: str):
    await ctx.send(f"🎬 Generating a video for: **{prompt}** — please wait...")
    await ctx.send("✍️ Writing script...")

    try:
        script = await asyncio.to_thread(generate_script, prompt)
        await ctx.send("🎙️ Generating voice narration...")
        video_path = await build_video(prompt, script)
        await ctx.send("📤 Uploading your video...")

        size_mb = video_path.stat().st_size / (1024 * 1024)
        if size_mb < 24:
            await ctx.send(file=discord.File(str(video_path)))
        else:
            await ctx.send(f"✅ Video created ({size_mb:.1f} MB). Saved at `{video_path}`.")
    except Exception as e:
        await ctx.send(f"❌ Failed to build video: {e}")


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
    bot.run(DISCORD_TOKEN)

# -------------------
# Start
# -------------------
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    run_discord()
