import os
import tempfile
import uuid
import random
import textwrap
from pathlib import Path
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp

try:
    import google.generativeai as genai
    HAVE_GEMINI = True
except Exception:
    HAVE_GEMINI = False


class VideoMaker:
    def __init__(self, gemini_api_key=None):
        self.gemini_api_key = gemini_api_key
        if HAVE_GEMINI and gemini_api_key:
            try:
                genai.configure(api_key=gemini_api_key)
                self.model = genai.GenerativeModel("gemini-1.5-flash")
            except Exception as e:
                print("⚠️ Gemini init failed:", e)
                self.model = None
        else:
            self.model = None

        self.output_dir = Path("videos")
        self.output_dir.mkdir(exist_ok=True)

    # ---------------------------------------------------------
    # 🎬 Main Video Creation
    # ---------------------------------------------------------
    def make_video(self, prompt: str, notify_func=None, lang="en"):
        """Create a narrated slideshow video with AI script."""
        try:
            if notify_func:
                notify_func("✍️ Writing script...")

            script = self.generate_script(prompt)

            if notify_func:
                notify_func("🎙️ Generating narration...")

            audio_path = self.text_to_speech(script, lang)

            if notify_func:
                notify_func("🖼️ Generating visuals...")

            video_path = self.build_video(script, audio_path)

            if notify_func:
                notify_func("🎞️ Combining video...")

            return video_path
        except Exception as e:
            print("❌ make_video error:", e)
            raise

    # ---------------------------------------------------------
    # 🧠 AI Script Generation
    # ---------------------------------------------------------
    def generate_script(self, prompt: str) -> str:
        if self.model:
            try:
                response = self.model.generate_content(
                    f"Write a short, engaging 1-minute video narration about: {prompt}."
                )
                return response.text.strip()
            except Exception as e:
                print("⚠️ Gemini generation failed:", e)

        # fallback
        return (
            f"🎬 Title: {prompt}\n\n"
            "Scene 1: Introduction to the topic.\n"
            "Scene 2: Key insights or main idea.\n"
            "Scene 3: Real world example.\n"
            "Scene 4: Conclusion and takeaway.\n"
        )

    # ---------------------------------------------------------
    # 🗣️ Text → Speech
    # ---------------------------------------------------------
    def text_to_speech(self, text, lang="en") -> str:
        temp_path = self.output_dir / f"{uuid.uuid4().hex}.mp3"
        tts = gTTS(text, lang=lang)
        tts.save(str(temp_path))
        return temp_path

    # ---------------------------------------------------------
    # 🖼️ Create Visual Slides
    # ---------------------------------------------------------
    def build_video(self, script: str, audio_path: str) -> str:
        audio_clip = mp.AudioFileClip(str(audio_path))
        duration = audio_clip.duration

        # Split text into segments
        slides = self.split_text(script)
        per_slide = duration / max(len(slides), 1)
        clips = []

        for line in slides:
            img = self.create_image(line)
            img_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
            img.save(img_path)
            clip = mp.ImageClip(img_path).set_duration(per_slide)
            clips.append(clip)

        final_clip = mp.concatenate_videoclips(clips, method="compose")
        final_clip = final_clip.set_audio(audio_clip)
        final_clip = final_clip.set_fps(24)

        output_path = self.output_dir / f"{uuid.uuid4().hex}.mp4"
        final_clip.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            verbose=False,
            logger=None
        )

        audio_clip.close()
        return str(output_path)

    # ---------------------------------------------------------
    # 🧩 Helpers
    # ---------------------------------------------------------
    def split_text(self, text: str, width=70):
        lines = []
        for p in text.split("\n"):
            p = p.strip()
            if not p:
                continue
            lines.extend(textwrap.wrap(p, width=width))
        return lines

    def create_image(self, text: str, size=(1280, 720)):
        """Create a slide with real background and text overlay."""
        W, H = size
        # choose random color background
        bg_color = random.choice(
            [(20, 30, 60), (60, 20, 30), (30, 60, 20), (50, 50, 50)]
        )
        img = Image.new("RGB", size, color=bg_color)
        draw = ImageDraw.Draw(img)

        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = (
            ImageFont.truetype(font_path, 42)
            if os.path.exists(font_path)
            else ImageFont.load_default()
        )

        wrapped = textwrap.wrap(text, width=40)
        total_height = sum(draw.textbbox((0, 0), line, font=font)[3] for line in wrapped)
        y = (H - total_height) // 2

        for line in wrapped:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            draw.text(((W - w) / 2, y), line, font=font, fill=(255, 255, 255))
            y += bbox[3] - bbox[1] + 10

        return img
