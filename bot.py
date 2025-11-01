# bot.py
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

# Optional: try to use google.generativeai (Gemini) if installed
try:
    import google.generativeai as genai
    HAVE_GEMINI = True
except Exception:
    HAVE_GEMINI = False

# -------------------
# Configuration
# -------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")         # set in Render/Env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")       # set in Render/Env
VIDEO_DIR = Path("videos")
VIDEO_DIR.mkdir(exist_ok=True)

# Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# If Gemini available, configure
if HAVE_GEMINI and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception:
        HAVE_GEMINI = False

# -------------------
# Helpers
# -------------------
def generate_script_using_gemini(prompt: str) -> str:
    """
    Try to get a script from Gemini. If Gemini library isn't available
    or the call fails, raise exception so fallback occurs.
    """
    # NOTE: API details vary by lib version — this is a best-effort attempt.
    # If it errors, caller will handle fallback.
    completion = genai.generate_text(model="chat-bison-002", # fallback model name attempt
                                     prompt=prompt,
                                     max_output_tokens=500)
    # The response format may vary. Try to extract text.
    if hasattr(completion, "text"):
        return completion.text
    if isinstance(completion, dict):
        # common fallback
        return completion.get("content", "") or completion.get("output", "") or str(completion)
    return str(completion)

def fallback_script(prompt: str) -> str:
    """Simple fallback script generation when Gemini inaccessible"""
    return (
        f"Title: {prompt}\n\n"
        "Scene 1: Short intro - A quick 3-5 second opening with the topic introduction.\n"
        "Scene 2: Main content - Explain the main idea with short sentences.\n"
        "Scene 3: Visual example - Describe a short visual that matches the voice.\n"
        "Scene 4: Closing - One-sentence call to action or closing line.\n"
    )

def split_text_into_segments(text: str, max_chars: int = 140):
    """Split text into suitably sized segments for slide images."""
    paragraphs = text.replace("\r", "").split("\n")
    segments = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # wrap into lines of reasonable length
        wrapped = textwrap.wrap(p, width=60)
        # join some wrapped lines into segments each containing up to max_chars chars
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
    # if too few segments, ensure at least one
    return segments or [""]

def create_image_for_text(text: str, size=(1280, 720), bg=(10, 10, 10), fg=(240,240,240)):
    """Create a PIL Image with centered text. Returns PIL Image."""
    W, H = size
    img = Image.new("RGB", size, color=bg)
    draw = ImageDraw.Draw(img)

    # try to use a TTF font if available, otherwise default
    font = None
    for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, 40)
                break
            except Exception:
                font = None
    if font is None:
        font = ImageFont.load_default()

    # wrap text to width
    lines = textwrap.wrap(text, width=40)
    # compute total height
    line_h = font.getsize("Ay")[1] + 10
    total_h = line_h * len(lines)
    y = (H - total_h) // 2
    for line in lines:
        w, h = draw.textsize(line, font=font)
        x = (W - w) // 2
        draw.text((x, y), line, font=font, fill=fg)
        y += line_h
    return img

async def build_video_from_text(prompt: str, script_text: str, voice_lang="en") -> Path:
    """
    Build a simple video: split script -> create slides -> generate TTS -> combine.
    Returns path to saved mp4.
    """
    # unique names
    uid = uuid.uuid4().hex[:8]
    audio_path = VIDEO_DIR / f"{uid}_voice.mp3"
    video_path = VIDEO_DIR / f"{uid}.mp4"

    # Create TTS audio (gTTS)
    # gTTS is blocking; run in thread
    def make_tts():
        tts = gTTS(script_text, lang=voice_lang, slow=False)
        tts.save(str(audio_path))
    await asyncio.to_thread(make_tts)

    # load audio duration
    audio_clip = mp.AudioFileClip(str(audio_path))
    audio_duration = audio_clip.duration

    # split script into segments and create image slides
    segments = split_text_into_segments(script_text)
    num_segments = max(1, len(segments))
    # allocate duration per segment proportional equal
    per_segment_dur = audio_duration / num_segments if audio_duration > 0 else 3

    image_clips = []
    for i, seg in enumerate(segments):
        img = create_image_for_text(seg)
        # convert PIL to ImageClip
        bio = BytesIO()
        img.save(bio, format="PNG")
        bio.seek(0)
        clip = mp.ImageClip(bio).set_duration(per_segment_dur)
        clip = clip.resize(width=1280)  # ensure size
        image_clips.append(clip)

    # concatenate clips
    final_clip = mp.concatenate_videoclips(image_clips, method="compose")
    final_clip = final_clip.set_audio(audio_clip)
    final_clip = final_clip.set_fps(24)

    # write file (blocking) in thread to avoid blocking event loop
    def write_video():
        final_clip.write_videofile(str(video_path), codec="libx264", audio_codec="aac", verbose=False, logger=None)

    await asyncio.to_thread(write_video)

    # cleanup audio clip
    audio_clip.close()
    # return the path
    return video_path

# -------------------
# Discord commands
# -------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (id={bot.user.id})")
    print("Bot is ready.")

@bot.command(name="hello")
async def hello(ctx):
    await ctx.send("👋 Hello! I’m CineAI — your movie assistant bot!")

@bot.command(name="video")
async def video_cmd(ctx, *, prompt: str):
    """
    Usage: !video <prompt>
    """
    await ctx.send(f"🎬 Generating video for: **{prompt}** — this may take some time. I will upload when done.")

    # generate script via Gemini if available
    try:
        if HAVE_GEMINI and GEMINI_API_KEY:
            # try Gemini first (may throw)
            script_text = await asyncio.to_thread(generate_script_using_gemini, prompt)
            # safety: short fallback if empty
            if not script_text or len(script_text.strip()) < 20:
                script_text = fallback_script(prompt)
        else:
            script_text = fallback_script(prompt)
    except Exception as e:
        script_text = fallback_script(prompt)

    # build video (heavy work)
    try:
        video_path = await build_video_from_text(prompt, script_text)
    except Exception as e:
        await ctx.send(f"❌ Failed to build video: {e}")
        return

    # send file to Discord (if file size < Discord limits). If large, tell user where it is saved.
    try:
        filesize_mb = video_path.stat().st_size / 1024 / 1024
        if filesize_mb < 24:  # safe small file limit
            await ctx.send(file=discord.File(str(video_path)))
        else:
            await ctx.send(f"✅ Video created and saved: `{video_path}` ({filesize_mb:.1f} MB). Download from your Render instance or ask me to upload somewhere.")
    except Exception as e:
        await ctx.send(f"✅ Video created and saved: `{video_path}` but failed to upload to Discord: {e}")

# -------------------
# Run Flask simple health endpoint + Discord bot concurrently
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
    # ensure token exists
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not set in environment.")
        return
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    # start Flask in background thread (so Render health check passes)
    t = Thread(target=run_flask, daemon=True)
    t.start()
    # run discord bot (blocks)
    run_bot()
