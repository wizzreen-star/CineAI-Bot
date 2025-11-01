import os
import asyncio
import uuid
import textwrap
from io import BytesIO
from pathlib import Path

import discord
from discord.ext import commands
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp

# Optional: try to use Gemini if available
try:
    import google.generativeai as genai
    HAVE_GEMINI = True
except Exception:
    HAVE_GEMINI = False

# -------------------
# CONFIG
# -------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
VIDEO_DIR = Path("videos")
VIDEO_DIR.mkdir(exist_ok=True)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

if HAVE_GEMINI and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception:
        HAVE_GEMINI = False

# -------------------
# HELPERS
# -------------------
def generate_script_using_gemini(prompt: str) -> str:
    completion = genai.generate_text(
        model="chat-bison-002",
        prompt=prompt,
        max_output_tokens=500
    )
    if hasattr(completion, "text"):
        return completion.text
    if isinstance(completion, dict):
        return completion.get("content", "") or completion.get("output", "") or str(completion)
    return str(completion)

def fallback_script(prompt: str) -> str:
    return (
        f"🎬 Title: {prompt}\n\n"
        "Scene 1: Introduction - Introduce the topic quickly.\n"
        "Scene 2: Main Idea - Explain the concept in simple words.\n"
        "Scene 3: Example - Show or describe a quick example.\n"
        "Scene 4: Outro - Wrap up with a short final thought.\n"
    )

def split_text_into_segments(text: str, max_chars: int = 140):
    paragraphs = text.replace("\r", "").split("\n")
    segments = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
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
    return segments or [""]

def create_image_for_text(text: str, size=(1280, 720), bg=(15,15,15), fg=(240,240,240)):
    W, H = size
    img = Image.new("RGB", size, color=bg)
    draw = ImageDraw.Draw(img)
    font = None
    for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, 42)
                break
            except Exception:
                font = None
    if font is None:
        font = ImageFont.load_default()
    lines = textwrap.wrap(text, width=40)
    line_h = font.getsize("Ay")[1] + 10
    total_h = line_h * len(lines)
    y = (H - total_h) // 2
    for line in lines:
        w, _ = draw.textsize(line, font=font)
        x = (W - w) // 2
        draw.text((x, y), line, font=font, fill=fg)
        y += line_h
    return img

async def build_video_from_text(prompt: str, script_text: str, ctx) -> Path:
    uid = uuid.uuid4().hex[:8]
    audio_path = VIDEO_DIR / f"{uid}_voice.mp3"
    video_path = VIDEO_DIR / f"{uid}.mp4"

    await ctx.send("🎙️ Generating voice narration...")
    def make_tts():
        tts = gTTS(script_text, lang="en", slow=False)
        tts.save(str(audio_path))
    await asyncio.to_thread(make_tts)

    await ctx.send("🖼️ Creating video slides...")
    audio_clip = mp.AudioFileClip(str(audio_path))
    audio_duration = audio_clip.duration

    segments = split_text_into_segments(script_text)
    per_segment_dur = audio_duration / len(segments) if len(segments) else 3

    image_clips = []
    for seg in segments:
        img = create_image_for_text(seg)
        bio = BytesIO()
        img.save(bio, format="PNG")
        bio.seek(0)
        clip = mp.ImageClip(bio).set_duration(per_segment_dur).resize(width=1280)
        image_clips.append(clip)

    final_clip = mp.concatenate_videoclips(image_clips, method="compose")
    final_clip = final_clip.set_audio(audio_clip)
    final_clip = final_clip.set_fps(24)

    await ctx.send("🎞️ Rendering video... this can take up to 2–5 minutes ⏳")
    def write_video():
        final_clip.write_videofile(str(video_path), codec="libx264", audio_codec="aac", verbose=False, logger=None)
    await asyncio.to_thread(write_video)

    audio_clip.close()
    return video_path

# -------------------
# COMMANDS
# -------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (id={bot.user.id})")
    print("Bot is ready.")

@bot.command(name="hello")
async def hello(ctx):
    await ctx.send("👋 Hello! I’m CineAI — I can generate short AI videos from text prompts!")

@bot.command(name="video")
async def video_cmd(ctx, *, prompt: str):
    await ctx.send(f"🎬 Generating a video for: **{prompt}** — please wait...")

    try:
        if HAVE_GEMINI and GEMINI_API_KEY:
            script_text = await asyncio.to_thread(generate_script_using_gemini, prompt)
            if not script_text or len(script_text.strip()) < 20:
                script_text = fallback_script(prompt)
        else:
            script_text = fallback_script(prompt)
    except Exception:
        script_text = fallback_script(prompt)

    try:
        video_path = await build_video_from_text(prompt, script_text, ctx)
    except Exception as e:
        await ctx.send(f"❌ Failed to build video: {e}")
        return

    filesize_mb = video_path.stat().st_size / 1024 / 1024
    if filesize_mb < 24:
        await ctx.send(file=discord.File(str(video_path)))
    else:
        await ctx.send(f"✅ Video created ({filesize_mb:.1f} MB). Too large for Discord — check your Render `/videos` folder.")

# -------------------
# RUN Flask (for Render health)
# -------------------
from flask import Flask, Response
from threading import Thread

app = Flask("cineai")
@app.route("/")
def index():
    return Response("CineAI bot running", mimetype="text/plain")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def run_bot():
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not set in environment.")
        return
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    run_bot()
