import os
import tempfile
import random
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
from moviepy.editor import *
import google.generativeai as genai

# -----------------------------
# CONFIG
# -----------------------------
class VideoMaker:
    def __init__(self, gemini_api_key=None):
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.model = None

    # ----------------------------------
    # Generate script using Gemini
    # ----------------------------------
    def generate_script(self, topic: str):
        if not self.model:
            return f"Video about {topic}. AI video demo."

        prompt = f"Write a short 6-line video narration about {topic}, suitable for AI narration."
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            if not text:
                raise ValueError("Empty response from Gemini")
            return text
        except Exception as e:
            print(f"⚠️ Script generation failed: {e}")
            return f"AI could not generate script for {topic}. Please try again."

    # ----------------------------------
    # Create simple background image (placeholder)
    # ----------------------------------
    def create_image(self, text, output_path):
        # Use LANCZOS instead of ANTIALIAS
        if hasattr(Image, "Resampling"):
            resample_filter = Image.Resampling.LANCZOS
        elif hasattr(Image, "LANCZOS"):
            resample_filter = Image.LANCZOS
        else:
            resample_filter = Image.BICUBIC

        # Background
        img = Image.new("RGB", (1280, 720), color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            font = ImageFont.load_default()

        # Text placement
        lines = text.split("\n")
        y_text = 300
        for line in lines:
            w, h = draw.textsize(line, font=font)
            draw.text(((1280 - w) / 2, y_text), line, font=font, fill="white")
            y_text += h + 10

        img.save(output_path)

    # ----------------------------------
    # Main function: generate video
    # ----------------------------------
    def make_video_for_prompt(self, prompt, notify_func=None):
        try:
            if notify_func:
                notify_func("✍️ Writing script...")
            script = self.generate_script(prompt)

            if notify_func:
                notify_func("🎙️ Generating voice...")
            tts = gTTS(script)
            audio_path = tempfile.mktemp(suffix=".mp3")
            tts.save(audio_path)

            # Split script lines into images
            if notify_func:
                notify_func("🖼️ Creating images...")

            temp_dir = tempfile.mkdtemp()
            slides = []
            for i, line in enumerate(script.split("\n")):
                if not line.strip():
                    continue
                img_path = os.path.join(temp_dir, f"slide_{i}.jpg")
                self.create_image(line, img_path)
                clip = ImageClip(img_path, duration=4)
                slides.append(clip)

            if not slides:
                raise ValueError("⚠️ No slides generated.")

            final_clip = concatenate_videoclips(slides, method="compose")
            audio_clip = AudioFileClip(audio_path)
            final_clip = final_clip.set_audio(audio_clip)

            # Export final video
            output_path = tempfile.mktemp(suffix=".mp4")
            final_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")

            if notify_func:
                notify_func("✅ Video generated successfully!")
            return output_path

        except Exception as e:
            print(f"❌ Error while generating video: {e}")
            if notify_func:
                notify_func(f"❌ Failed to generate video: {e}")
            return None
