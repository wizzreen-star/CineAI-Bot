import os
import io
import uuid
import asyncio
import discord
import moviepy.editor as mp
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from dotenv import load_dotenv
from flask import Flask
import threading
import google.generativeai as genai
from pathlib import Path

# === Load environment variables ===
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not DISCORD_TOKEN or not GOOGLE_API_KEY:
    raise ValueError("❌ Missing DISCORD_TOKEN or GOOGLE_API_KEY in .env file!")

# === Configure Gemini ===
genai.configure(api_key=GOOGLE_API_KEY)

# === Directories ===
VIDEO_DIR = Path("videos")
VIDEO_DIR.mkdir(exist_ok=True)

# === Discord bot setup ===
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = discord.Client(intents=intents)

# === Flask keep-alive ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ CineAI Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask, daemon=True).start()

# === Helper: Split text ===
def split_text_into_segments(text, max_len=200):
    words = text.split()
    segs, current = [], []
    for w in words:
        current.append(w)
        if len(" ".join(current)) > max_len:
            segs.append(" ".join(current))
            current = []
    if current:
        segs.append(" ".join(current))
    return segs

# === Helper: Create image ===
def create_image_for_text(text):
    img = Image.new("RGB", (1280, 720), color=(25, 25, 25))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 42)
    except:
        font = ImageFont.load_default()
    wrapped = "\n".join(text[i:i+40] for i in range(0, len(text), 40))
    draw.text((60, 280), wrapped, font=font, fill=(255, 255, 255))
    return img

# === Generate script using Gemini ===
async def generate_script(prompt: str) -> str:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(f"Write a short 60-second video script about: {prompt}")
    return response.text.strip()

# === Build the video ===
async def build_video_from_text(prompt: str, script_text: str, ctx) -> Path:
    uid = uuid.uuid4().hex[:8]
    audio_path = VIDEO_DIR / f"{uid}_voice.mp3"
    video_path = VIDEO_DIR / f"{uid}.mp4"

    await ctx.send("🎙️ Generating voice narration...")

    def make_tts():
        tts = gTTS(script_text, lang="en", slow=False)
        tts.save(str(audio_path))
    await asyncio.to_thread(make_tts)

    audio_clip = mp.AudioFileClip(str(audio_path))
    audio_duration = audio_clip.duration

    await ctx.send("🖼️ Creating image slides...")

    segments = split_text_into_segments(script_text)
    per_segment_dur = audio_duration / len(segments) if len(segments) else 3

    image_clips = []
    for seg in segments:
        img = create_image_for_text(seg)
        np_img = np.array(img)  # ✅ FIXED: Convert PIL → numpy
        clip = mp.ImageClip(np_img).set_duration(per_segment_dur).resize(width=1280)
        image_clips.append(clip)

    await ctx.send("🎞️ Rendering video... this can take a few minutes ⏳")

    final_clip = mp.concatenate_videoclips(image_clips, method="compose")
    final_clip = final_clip.set_audio(audio_clip)
    final_clip = final_clip.set_fps(24)

    def write_video():
        final_clip.write_videofile(str(video_path), codec="libx264", audio_codec="aac", verbose=False, logger=None)
    await asyncio.to_thread(write_video)

    audio_clip.close()
    return video_path

# === Command: !video ===
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith("!video"):
        prompt = message.content.replace("!video", "").strip()
        if not prompt:
            await message.channel.send("⚠️ Please provide a topic. Example: `!video the future of AI`")
            return

        await message.channel.send(f"🎬 Generating a video for: **{prompt}** — please wait...")

        try:
            script = await generate_script(prompt)
            video_path = await build_video_from_text(prompt, script, message.channel)
            await message.channel.send(f"✅ Here's your video for **{prompt}**:", file=discord.File(video_path))
        except Exception as e:
            await message.channel.send(f"❌ Failed to build video: {e}")

# === Run bot ===
bot.run(DISCORD_TOKEN)
