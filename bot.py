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
import logging

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
logging.basicConfig(level=logging.INFO)
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
# Script Generation
# -------------------
def generate_script(prompt: str) -> str:
    """Generate a video script using Gemini or fallback."""
    if HAVE_GEMINI and GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-pro")
            response = model.generate_content(
                f"Write a short, engaging video script (60–90 seconds) about: {prompt}. Keep it creative but concise."
            )
            if hasattr(response, "text") and response.text:
                return response.text.strip()
        except Exception as e:
            print("⚠️ Gemini failed, using fallback:", e)

    # Fallback if Gemini not available
    return (
        f"🎬 Title: {prompt}\n\n"
        "Scene 1: Quick intro explaining the topic.\n"
        "Scene 2: Main idea in simple words.\n"
        "Scene 3: A visual or fun example.\n"
        "Scene 4: Final line or call to action.\n"
    )


# -------------------
# Text ➜ Image
# -------------------
def split_text_into_segments(text: str, max_chars=160):
    """Split text into readable pieces for slides."""
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
    """Generate an image with centered text."""
    W, H = size
    img = Image.new("RGB", size, color=(15, 15, 15))
    draw = ImageDraw.Draw(img)

    # Load font
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(font_path):
        font = ImageFont.truetype(font_path, 42)
    else:
        font = ImageFont.load_default()

    lines = textwrap.wrap(text, width=40)
    line_heights = [font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines]
    total_h = sum(line_heights) + 10 * len(lines)
    y = (H - total_h) // 2

    for line, h in zip(lines, line_heights):
        w = font.getlength(line)
        draw.text(((W - w) / 2, y), line, font=font, fill=(240, 240, 240))
        y += h + 10

    return img


# -------------------
# Video Builder
# -------------------
async def build_video(prompt: str, script: str, lang="en") -> Path:
    """Combine slides + voiceover into final MP4."""
    uid = uuid.uuid4().hex[:8]
    audio_path = VIDEO_DIR / f"{uid}.mp3"
    video_path = VIDEO_DIR / f"{uid}.mp4"

    # 1️⃣ Generate speech
    def make_tts():
        tts = gTTS(script, lang=lang)
        tts.save(str(audio_path))
    await asyncio.to_thread(make_tts)

    # 2️⃣ Load audio
    audio_clip = mp.AudioFileClip(str(audio_path))
    duration = audio_clip.duration

    # 3️⃣ Create slides
    slides = split_text_into_segments(script)
    per_slide = duration / max(len(slides), 1)
    clips = []

    for s in slides:
        img = create_image(s)
        temp_img = VIDEO_DIR / f"{uuid.uuid4().hex[:6]}.png"
        img.save(temp_img)
        clip = mp.ImageClip(str(temp_img)).set_duration(per_slide)
        clips.append(clip)

    # 4️⃣ Combine everything
    final_clip = mp.concatenate_videoclips(clips, method="compose")
    final_clip = final_clip.set_audio(audio_clip)
    final_clip = final_clip.set_fps(24)

    # 5️⃣ Save video
    def write_file():
        final_clip.write_videofile(str(video_path), codec="libx264", audio_codec="aac", verbose=False, logger=None)
    await asyncio.to_thread(write_file)

    # cleanup
    audio_clip.close()
    for c in clips:
        try:
            os.remove(c.filename)
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
    await ctx.send("👋 Hey! I’m CineAI — I can turn your ideas into videos!")

@bot.command(name="video")
async def make_video(ctx, *, prompt: str):
    """Create a short AI-generated video from text."""
    try:
        await ctx.send(f"🎬 Generating a video for: **{prompt}** — please wait...")
        await ctx.send("✍️ Writing script...")

        # 1️⃣ Generate script
        script = await asyncio.to_thread(generate_script, prompt)

        # 2️⃣ Build video (with timeout)
        await ctx.send("🎙️ Generating voice narration...")
        try:
            video_path = await asyncio.wait_for(build_video(prompt, script), timeout=300)
        except asyncio.TimeoutError:
            await ctx.send("⚠️ Took too long — video build cancelled.")
            return

        # 3️⃣ Upload result
        await ctx.send("📤 Uploading your video...")
        size_mb = video_path.stat().st_size / (1024 * 1024)
        if size_mb < 24:
            await ctx.send(file=discord.File(str(video_path)))
        else:
            await ctx.send(f"✅ Video created ({size_mb:.1f} MB). Too large for Discord but saved at `{video_path}`.")
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
# Start Everything
# -------------------
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    run_discord()# ================================================================
# 🎬 CineAI Discord Bot — Auto Video Maker (Text ➜ Speech ➜ Video)
# ================================================================

import os
import asyncio
import uuid
import textwrap
from io import BytesIO
from pathlib import Path
from threading import Thread
import logging

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
logging.basicConfig(level=logging.INFO)
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
# Script Generation
# -------------------
def generate_script(prompt: str) -> str:
    """Generate a video script using Gemini or fallback."""
    if HAVE_GEMINI and GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-pro")
            response = model.generate_content(
                f"Write a short, engaging video script (60–90 seconds) about: {prompt}. Keep it creative but concise."
            )
            if hasattr(response, "text") and response.text:
                return response.text.strip()
        except Exception as e:
            print("⚠️ Gemini failed, using fallback:", e)

    # Fallback if Gemini not available
    return (
        f"🎬 Title: {prompt}\n\n"
        "Scene 1: Quick intro explaining the topic.\n"
        "Scene 2: Main idea in simple words.\n"
        "Scene 3: A visual or fun example.\n"
        "Scene 4: Final line or call to action.\n"
    )


# -------------------
# Text ➜ Image
# -------------------
def split_text_into_segments(text: str, max_chars=160):
    """Split text into readable pieces for slides."""
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
    """Generate an image with centered text."""
    W, H = size
    img = Image.new("RGB", size, color=(15, 15, 15))
    draw = ImageDraw.Draw(img)

    # Load font
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(font_path):
        font = ImageFont.truetype(font_path, 42)
    else:
        font = ImageFont.load_default()

    lines = textwrap.wrap(text, width=40)
    line_heights = [font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines]
    total_h = sum(line_heights) + 10 * len(lines)
    y = (H - total_h) // 2

    for line, h in zip(lines, line_heights):
        w = font.getlength(line)
        draw.text(((W - w) / 2, y), line, font=font, fill=(240, 240, 240))
        y += h + 10

    return img


# -------------------
# Video Builder
# -------------------
async def build_video(prompt: str, script: str, lang="en") -> Path:
    """Combine slides + voiceover into final MP4."""
    uid = uuid.uuid4().hex[:8]
    audio_path = VIDEO_DIR / f"{uid}.mp3"
    video_path = VIDEO_DIR / f"{uid}.mp4"

    # 1️⃣ Generate speech
    def make_tts():
        tts = gTTS(script, lang=lang)
        tts.save(str(audio_path))
    await asyncio.to_thread(make_tts)

    # 2️⃣ Load audio
    audio_clip = mp.AudioFileClip(str(audio_path))
    duration = audio_clip.duration

    # 3️⃣ Create slides
    slides = split_text_into_segments(script)
    per_slide = duration / max(len(slides), 1)
    clips = []

    for s in slides:
        img = create_image(s)
        temp_img = VIDEO_DIR / f"{uuid.uuid4().hex[:6]}.png"
        img.save(temp_img)
        clip = mp.ImageClip(str(temp_img)).set_duration(per_slide)
        clips.append(clip)

    # 4️⃣ Combine everything
    final_clip = mp.concatenate_videoclips(clips, method="compose")
    final_clip = final_clip.set_audio(audio_clip)
    final_clip = final_clip.set_fps(24)

    # 5️⃣ Save video
    def write_file():
        final_clip.write_videofile(str(video_path), codec="libx264", audio_codec="aac", verbose=False, logger=None)
    await asyncio.to_thread(write_file)

    # cleanup
    audio_clip.close()
    for c in clips:
        try:
            os.remove(c.filename)
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
    await ctx.send("👋 Hey! I’m CineAI — I can turn your ideas into videos!")

@bot.command(name="video")
async def make_video(ctx, *, prompt: str):
    """Create a short AI-generated video from text."""
    try:
        await ctx.send(f"🎬 Generating a video for: **{prompt}** — please wait...")
        await ctx.send("✍️ Writing script...")

        # 1️⃣ Generate script
        script = await asyncio.to_thread(generate_script, prompt)

        # 2️⃣ Build video (with timeout)
        await ctx.send("🎙️ Generating voice narration...")
        try:
            video_path = await asyncio.wait_for(build_video(prompt, script), timeout=300)
        except asyncio.TimeoutError:
            await ctx.send("⚠️ Took too long — video build cancelled.")
            return

        # 3️⃣ Upload result
        await ctx.send("📤 Uploading your video...")
        size_mb = video_path.stat().st_size / (1024 * 1024)
        if size_mb < 24:
            await ctx.send(file=discord.File(str(video_path)))
        else:
            await ctx.send(f"✅ Video created ({size_mb:.1f} MB). Too large for Discord but saved at `{video_path}`.")
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
# Start Everything
# -------------------
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    run_discord()                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()

    # Wrap text
    lines = textwrap.wrap(text, width=40)
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_heights.append(bbox[3] - bbox[1])
    total_height = sum(line_heights) + 10 * (len(lines) - 1)
    y = (H - total_height) // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (W - w) // 2
        draw.text((x, y), line, font=font, fill=fg)
        y += h + 10

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
        img = create_image_for_text(s)
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

    # 1. Get script
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
        raise ValueError("❌ Missing DISCORD_TOKEN in environment!")
    bot.run(DISCORD_TOKEN)


# -------------------
# Start Everything
# -------------------
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    run_discord()
