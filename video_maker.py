# ================================================================
# 🎥 video_maker.py — Handles creating narrated videos from text
# ================================================================

import uuid
import textwrap
from pathlib import Path
from io import BytesIO
import asyncio
import numpy as np
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp

# Directory to store generated videos
VIDEO_DIR = Path("videos")
VIDEO_DIR.mkdir(exist_ok=True)


# -------------------
# Helper Functions
# -------------------
def split_text(text, max_chars=150):
    """Split long text into multiple short slides."""
    lines = text.split("\n")
    chunks = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        chunks.extend(textwrap.wrap(line, width=70))
    return chunks or ["(no content)"]


def create_image(text: str, size=(1280, 720)):
    """Generate an image with centered text."""
    W, H = size
    img = Image.new("RGB", (W, H), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
    except:
        font = ImageFont.load_default()

    lines = textwrap.wrap(text, width=40)
    total_height = sum(draw.textbbox((0, 0), line, font=font)[3] for line in lines) + 15 * len(lines)
    y = (H - total_height) // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((W - w) / 2, y), line, fill=(255, 255, 255), font=font)
        y += bbox[3] + 15

    return np.array(img)


# -------------------
# Main Video Builder
# -------------------
async def build_video(prompt: str, script: str, lang="en") -> Path:
    """Build a full narrated slideshow video."""
    uid = uuid.uuid4().hex[:8]
    audio_path = VIDEO_DIR / f"{uid}.mp3"
    video_path = VIDEO_DIR / f"{uid}.mp4"

    # 🎙️ Text-to-Speech
    await asyncio.to_thread(lambda: gTTS(script, lang=lang).save(str(audio_path)))
    audio_clip = mp.AudioFileClip(str(audio_path))
    duration = audio_clip.duration

    # 🖼️ Generate slides
    slides = split_text(script)
    per_slide = max(duration / len(slides), 2)
    clips = [mp.ImageClip(create_image(s)).set_duration(per_slide) for s in slides]

    # 🎬 Combine video + audio
    final = mp.concatenate_videoclips(clips, method="compose").set_audio(audio_clip)
    final = final.set_fps(24)

    # 💾 Save video
    await asyncio.to_thread(final.write_videofile, str(video_path), codec="libx264", audio_codec="aac", verbose=False, logger=None)
    audio_clip.close()

    return video_path
