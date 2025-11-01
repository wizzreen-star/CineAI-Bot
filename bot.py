# ================================================================
# 🎬 CineAI Discord Bot — Auto Video Maker (Text ➜ Speech ➜ Video)
# - fixes: BytesIO -> numpy, Pillow textbbox, progress messages,
#   robust Gemini handling, safer MoviePy usage, error reporting.
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
import numpy as np
from flask import Flask, Response

# Optional: try to use Google Gemini (google.generativeai)
try:
    import google.generativeai as genai
    HAVE_GEMINI = True
except Exception:
    genai = None
    HAVE_GEMINI = False

# -------------------
# Configuration
# -------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")        # required
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")      # optional
PORT = int(os.getenv("PORT", 10000))

VIDEO_DIR = Path("videos")
VIDEO_DIR.mkdir(exist_ok=True)

# -------------------
# Discord Setup
# -------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# configure Gemini if available
if HAVE_GEMINI and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print("⚠️ Gemini configure failed:", e)
        HAVE_GEMINI = False

# -------------------
# Script Generation (Gemini or fallback)
# -------------------
def generate_script_via_gemini(prompt: str) -> str:
    """
    Try multiple genai call styles to be robust across versions.
    Returns plain text script or raises.
    """
    if not HAVE_GEMINI:
        raise RuntimeError("Gemini not available")

    # 1) try high-level helper if present
    try:
        if hasattr(genai, "generate_text"):
            resp = genai.generate_text(model="chat-bison-002", prompt=prompt, max_output_tokens=500)
            # many wrappers return object with .text
            if hasattr(resp, "text") and resp.text:
                return resp.text
            # or dict-like
            if isinstance(resp, dict):
                return resp.get("text") or resp.get("content") or str(resp)
            return str(resp)
    except Exception:
        pass

    # 2) try GenerativeModel style if present
    try:
        if hasattr(genai, "GenerativeModel"):
            model = genai.GenerativeModel("chat-bison-002")
            resp = model.generate_content(prompt)
            if hasattr(resp, "text") and resp.text:
                return resp.text
            if isinstance(resp, dict):
                return resp.get("content") or resp.get("output") or str(resp)
            return str(resp)
    except Exception:
        pass

    raise RuntimeError("Gemini call failed")

def fallback_script(prompt: str) -> str:
    """Simple fallback script for video if Gemini isn't available."""
    return (
        f"Title: {prompt}\n\n"
        "Scene 1 — Quick intro (3-5s): Briefly introduce the idea.\n"
        "Scene 2 — Explain (20-30s): Explain the main points in short sentences.\n"
        "Scene 3 — Example (15-25s): Give a simple visual example.\n"
        "Scene 4 — Outro (3-5s): Call to action or short closing line.\n"
    )

def generate_script(prompt: str) -> str:
    """High-level wrapper used by the bot."""
    if HAVE_GEMINI and GEMINI_API_KEY:
        try:
            # give Gemini a helpful instruction
            instruction = (
                f"Write a concise, engaging 60-90 second video script about: {prompt}\n"
                "Use short sentences and simple language suitable for narration."
            )
            return generate_script_via_gemini(instruction)
        except Exception as e:
            print("⚠️ Gemini generation failed, using fallback. Error:", e)
            return fallback_script(prompt)
    else:
        return fallback_script(prompt)

# -------------------
# Text -> Images helpers
# -------------------
def split_text_into_segments(text: str, max_chars: int = 160):
    """Split text into slide-friendly segments."""
    paragraphs = [p.strip() for p in text.replace("\r", "").split("\n") if p.strip()]
    if not paragraphs:
        return ["(no text)"]
    segments = []
    for p in paragraphs:
        wrapped = textwrap.wrap(p, width=60)
        current = ""
        for line in wrapped:
            if len(current) + len(line) + 1 > max_chars:
                if current:
                    segments.append(current.strip())
                current = line
            else:
                current = (current + " " + line).strip()
        if current:
            segments.append(current)
    return segments or ["(no text)"]

def create_image_for_text(text: str, size=(1280, 720), bg=(12,12,12), fg=(240,240,240)):
    """Create a centered text image (PIL Image). Uses textbbox for measuring."""
    W, H = size
    img = Image.new("RGB", size, color=bg)
    draw = ImageDraw.Draw(img)

    # try a common TTF; fallback to default
    font = None
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, 40)
                break
            except Exception:
                font = None
    if font is None:
        font = ImageFont.load_default()

    # wrap into lines for display
    lines = textwrap.wrap(text, width=40)
    # measure total height using textbbox
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0,0), line, font=font)
        line_heights.append(bbox[3] - bbox[1])
    total_h = sum(line_heights) + (10 * (len(lines)-1))
    y = (H - total_h) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0,0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (W - w) // 2
        draw.text((x, y), line, font=font, fill=fg)
        y += h + 10

    return img

# -------------------
# Build video (TTS + slides + MoviePy)
# -------------------
async def build_video_from_text(prompt: str, script_text: str, progress_callback=None) -> Path:
    """
    Build a narrated slideshow video and return Path to mp4.
    progress_callback(optional): callable(str) -> used to send progress messages.
    """
    def send_progress(msg: str):
        try:
            if progress_callback:
                progress_callback(msg)
            else:
                print(msg)
        except Exception:
            pass

    uid = uuid.uuid4().hex[:10]
    video_path = VIDEO_DIR / f"{uid}.mp4"
    audio_path = VIDEO_DIR / f"{uid}.mp3"

    send_progress("🎙️ Generating voice (gTTS)...")
    def make_tts():
        tts = gTTS(script_text, lang="en", slow=False)
        tts.save(str(audio_path))
    await asyncio.to_thread(make_tts)

    # load audio
    send_progress("🔊 Loading audio...")
    audio_clip = mp.AudioFileClip(str(audio_path))
    audio_duration = audio_clip.duration if audio_clip.duration else max(4.0, len(script_text) / 12.0)

    # create slides
    send_progress("🖼️ Creating slide images...")
    segments = split_text_into_segments(script_text)
    if not segments:
        segments = ["(no content)"]
    per_segment = audio_duration / len(segments)

    image_clips = []
    for seg in segments:
        pil_img = create_image_for_text(seg)
        np_img = np.array(pil_img)  # convert to numpy (H,W,3)
        clip = mp.ImageClip(np_img).set_duration(per_segment)
        # ensure consistent size
        clip = clip.resize(width=1280)
        image_clips.append(clip)

    send_progress("🎞️ Concatenating and attaching audio...")
    final_clip = mp.concatenate_videoclips(image_clips, method="compose")
    final_clip = final_clip.set_audio(audio_clip)
    final_clip = final_clip.set_fps(24)

    # render
    send_progress("🧩 Rendering video (this may take some time)...")
    def write_file():
        # disable verbose logger to keep logs smaller
        final_clip.write_videofile(str(video_path), codec="libx264", audio_codec="aac", threads=2, verbose=False, logger=None)
    await asyncio.to_thread(write_file)

    # cleanup
    try:
        audio_clip.close()
    except Exception:
        pass

    send_progress(f"✅ Video saved to: {video_path}")
    return video_path

# -------------------
# Discord commands
# -------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (id={bot.user.id}) — ready to make videos!")

@bot.command(name="hello")
async def hello(ctx):
    await ctx.send("👋 Hey! I’m CineAI — I can make short videos from your ideas! Use `!video <topic>`")

@bot.command(name="video")
async def make_video(ctx, *, prompt: str):
    """
    Usage: !video <prompt>
    """
    if not prompt or not prompt.strip():
        await ctx.send("⚠️ Please provide a prompt. Example: `!video a cat playing piano`")
        return

    await ctx.send(f"🎬 Generating a video for: **{prompt}** — please wait...")

    # progress sender for build_video
    async def progress_send(msg: str):
        try:
            await ctx.send(msg)
        except Exception:
            # fallback to print
            print("Progress:", msg)

    # generate script (gemini or fallback) outside event loop
    await ctx.send("✍️ Writing script...")
    try:
        script_text = await asyncio.to_thread(generate_script, prompt)
    except Exception as e:
        script_text = fallback_script(prompt)
        print("⚠️ Script generation error:", e)

    # show snippet
    snippet = (script_text[:500] + '...') if len(script_text) > 500 else script_text
    await ctx.send(f"📝 Script preview:\n```\n{snippet}\n```")

    # build video with progress callback
    try:
        # progress_callback that schedules sending messages in asyncio loop
        def progress_callback(msg: str):
            # schedule coroutine to send message without blocking
            asyncio.run_coroutine_threadsafe(progress_send(msg), bot.loop)
        video_path = await build_video_from_text(prompt, script_text, progress_callback=progress_callback)
    except Exception as e:
        await ctx.send(f"❌ Failed to build video: {e}")
        print("Build error:", e)
        return

    # upload or notify
    try:
        size_mb = video_path.stat().st_size / (1024*1024)
        if size_mb < 24:
            await ctx.send(file=discord.File(str(video_path)))
        else:
            await ctx.send(f"✅ Video created ({size_mb:.1f} MB). Too large to attach to Discord — download from the server path: `{video_path}`")
    except Exception as e:
        await ctx.send(f"✅ Video created at `{video_path}` but upload failed: {e}")

# -------------------
# Flask health (for Render)
# -------------------
app = Flask("cineai")
@app.route("/")
def index():
    return Response("✅ CineAI bot running", mimetype="text/plain")

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

def run_discord():
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not set in environment.")
        return
    bot.run(DISCORD_TOKEN)

# -------------------
# Start
# -------------------
if __name__ == "__main__":
    # start flask in background thread
    Thread(target=run_flask, daemon=True).start()
    # run bot (blocks)
    run_discord()
