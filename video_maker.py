import os
import random
import tempfile
import requests
import textwrap
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
import moviepy.editor as mp

try:
    import google.generativeai as genai
    HAVE_GEMINI = True
except Exception:
    HAVE_GEMINI = False


class VideoMaker:
    def __init__(self, gemini_api_key=None):
        self.have_gemini = HAVE_GEMINI and gemini_api_key
        if self.have_gemini:
            try:
                genai.configure(api_key=gemini_api_key)
            except Exception as e:
                print("⚠️ Gemini setup failed:", e)
                self.have_gemini = False

        self.font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        self.video_dir = Path("videos")
        self.video_dir.mkdir(exist_ok=True)

    # -------------------------
    # 1️⃣ Generate script text
    # -------------------------
    def generate_script(self, prompt: str) -> str:
        if self.have_gemini:
            try:
                response = genai.GenerativeModel("gemini-pro").generate_content(
                    f"Write a short video narration (about 60 seconds) for this topic: {prompt}. "
                    "Make it sound natural and engaging."
                )
                if hasattr(response, "text"):
                    return response.text.strip()
            except Exception as e:
                print("⚠️ Gemini script failed:", e)

        return f"This is a short explainer video about {prompt}. Let's explore it step by step!"

    # -------------------------
    # 2️⃣ Download related image
    # -------------------------
    def fetch_image(self, prompt):
        try:
            url = f"https://source.unsplash.com/1280x720/?{prompt.replace(' ', ',')}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return Image.open(BytesIO(resp.content)).convert("RGB")
        except Exception as e:
            print("⚠️ Image fetch failed:", e)
        return None

    # -------------------------
    # 3️⃣ Build the video
    # -------------------------
    def make_video_for_prompt(self, prompt, notify_func=None):
        if notify_func:
            notify_func("✍️ Writing script...")

        script = self.generate_script(prompt)
        if notify_func:
            notify_func("🎙️ Generating voice...")

        # Generate TTS audio
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_audio:
            gTTS(script).save(tmp_audio.name)
            audio_path = tmp_audio.name

        # Generate slide images
        if notify_func:
            notify_func("🖼️ Creating visuals...")

        base_img = self.fetch_image(prompt)
        if base_img is None:
            base_img = Image.new("RGB", (1280, 720), color=(0, 0, 0))
            print("⚠️ No image found, using black background")

        font = ImageFont.truetype(self.font_path, 48) if os.path.exists(self.font_path) else ImageFont.load_default()
        draw = ImageDraw.Draw(base_img)
        wrapped = textwrap.fill(prompt.upper(), width=18)
        text_w, text_h = draw.textbbox((0, 0), wrapped, font=font)[2:]
        draw.text(((1280 - text_w) / 2, (720 - text_h) / 2), wrapped, fill=(255, 255, 255), font=font)

        # Save frame
        frame_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        base_img.save(frame_path)

        # Combine with audio into video
        if notify_func:
            notify_func("🎞️ Building video...")

        try:
            img_clip = mp.ImageClip(frame_path).set_duration(10)
            audio_clip = mp.AudioFileClip(audio_path)
            final = img_clip.set_audio(audio_clip).set_fps(24)

            output_path = self.video_dir / f"{prompt.replace(' ', '_')[:20]}_{random.randint(1000,9999)}.mp4"
            final.write_videofile(str(output_path), codec="libx264", audio_codec="aac", verbose=False, logger=None)
            return output_path
        except Exception as e:
            print("❌ Failed video build:", e)
            return None
