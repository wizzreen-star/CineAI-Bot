import os
import textwrap
import uuid
import random
from io import BytesIO
from pathlib import Path
import asyncio

from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp

try:
    import google.generativeai as genai
    HAVE_GEMINI = True
except Exception:
    HAVE_GEMINI = False

# Suppress Gemini gRPC spam
os.environ["GRPC_VERBOSITY"] = "NONE"
os.environ["GLOG_minloglevel"] = "2"

class VideoMaker:
    def __init__(self, gemini_api_key=None):
        self.video_dir = Path("videos")
        self.video_dir.mkdir(exist_ok=True)
        self.gemini_api_key = gemini_api_key
        if HAVE_GEMINI and gemini_api_key:
            genai.configure(api_key=gemini_api_key)
        else:
            print("⚠️ Gemini not configured — using fallback scripts.")

    async def make_video(self, prompt: str, notify=None):
        """Generate and return a video path."""
        if notify:
            await notify("✍️ Writing script...")

        script = await asyncio.to_thread(self.generate_script, prompt)
        if notify:
            await notify("🎙️ Generating voice narration...")

        audio_path = await asyncio.to_thread(self.make_tts, script)
        if notify:
            await notify("🖼️ Creating video slides...")

        video_path = await asyncio.to_thread(self.make_slideshow, script, audio_path)
        return video_path

    def generate_script(self, prompt: str) -> str:
        if HAVE_GEMINI and self.gemini_api_key:
            try:
                model = genai.GenerativeModel("gemini-pro")
                response = model.generate_content(
                    f"Write a short video narration (about 5 sentences, under 40 seconds) about: {prompt}."
                )
                return response.text.strip() if response and response.text else prompt
            except Exception as e:
                print("⚠️ Gemini failed:", e)
        # fallback
        return f"This is a short video about {prompt}. Let's explore it quickly and simply!"

    def make_tts(self, text: str, lang="en"):
        tts = gTTS(text, lang=lang)
        out_path = self.video_dir / f"{uuid.uuid4().hex[:8]}.mp3"
        tts.save(out_path)
        return out_path

    def create_image(self, text: str, size=(1280, 720)):
        W, H = size
        img = Image.new("RGB", size, color=(random.randint(0,60), random.randint(0,60), random.randint(0,60)))
        draw = ImageDraw.Draw(img)
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_path, 50) if os.path.exists(font_path) else ImageFont.load_default()

        lines = textwrap.wrap(text, width=35)
        total_h = sum(font.getbbox(line)[3] for line in lines) + 20 * len(lines)
        y = (H - total_h) // 2
        for line in lines:
            w = font.getlength(line)
            draw.text(((W - w) / 2, y), line, font=font, fill=(255, 255, 255))
            y += font.getbbox(line)[3] + 20
        return img

    def make_slideshow(self, script: str, audio_path: Path):
        audio_clip = mp.AudioFileClip(str(audio_path))
        duration = audio_clip.duration

        slides = textwrap.wrap(script, width=80)
        per_slide = duration / max(len(slides), 1)
        clips = []

        for s in slides:
            img = self.create_image(s)
            frame_path = self.video_dir / f"frame_{uuid.uuid4().hex[:4]}.png"
            img.save(frame_path)
            clip = mp.ImageClip(str(frame_path)).set_duration(per_slide)
            clips.append(clip)

        final = mp.concatenate_videoclips(clips, method="compose")
        final = final.set_audio(audio_clip).set_fps(24)

        out_path = self.video_dir / f"{uuid.uuid4().hex[:8]}.mp4"
        final.write_videofile(str(out_path), codec="libx264", audio_codec="aac", verbose=False, logger=None)
        audio_clip.close()
        return out_path
