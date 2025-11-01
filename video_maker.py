# ================================================================
# 🎨 VideoMaker Class — Creates AI Videos with Gemini, gTTS & MoviePy
# ================================================================

import os
import uuid
import textwrap
from pathlib import Path
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageSequenceClip, AudioFileClip
import tempfile
import random

try:
    import google.generativeai as genai
except ImportError:
    genai = None

class VideoMaker:
    def __init__(self, gemini_api_key=None):
        self.video_dir = Path("videos")
        self.video_dir.mkdir(exist_ok=True)

        self.have_gemini = bool(gemini_api_key and genai)
        if self.have_gemini:
            try:
                genai.configure(api_key=gemini_api_key)
            except Exception as e:
                print("⚠️ Gemini setup failed:", e)
                self.have_gemini = False

    # -------------------
    # Generate Script
    # -------------------
    def generate_script(self, prompt: str) -> str:
        if self.have_gemini:
            try:
                model = genai.GenerativeModel("gemini-pro")
                response = model.generate_content(f"Write a detailed video narration script about: {prompt}. Include visuals, examples, and friendly tone.")
                if response.text:
                    return response.text.strip()
            except Exception as e:
                print("⚠️ Gemini failed:", e)

        return (
            f"🎬 Title: {prompt}\n\n"
            "Scene 1: Introduce the topic with excitement.\n"
            "Scene 2: Explain the main concept clearly.\n"
            "Scene 3: Give examples with a story.\n"
            "Scene 4: End with an inspiring message.\n"
        )

    # -------------------
    # Generate Images
    # -------------------
    def create_image(self, text: str, size=(1280, 720)):
        img = Image.new("RGB", size, color=(random.randint(0, 40), random.randint(0, 40), random.randint(0, 40)))
        draw = ImageDraw.Draw(img)

        # Font
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_path, 42) if os.path.exists(font_path) else ImageFont.load_default()

        # Wrap text
        lines = textwrap.wrap(text, width=40)
        y = (size[1] - len(lines) * 50) // 2
        for line in lines:
            w = font.getlength(line)
            draw.text(((size[0] - w) / 2, y), line, font=font, fill=(255, 255, 255))
            y += 60

        return img

    # -------------------
    # Main Video Builder
    # -------------------
    def make_video(self, prompt: str):
        print(f"🎬 Creating video for: {prompt}")
        script = self.generate_script(prompt)

        uid = uuid.uuid4().hex[:8]
        audio_path = self.video_dir / f"{uid}.mp3"
        video_path = self.video_dir / f"{uid}.mp4"

        # Generate voiceover
        print("🎙️ Generating voice...")
        tts = gTTS(script, lang="en")
        tts.save(str(audio_path))

        audio = AudioFileClip(str(audio_path))
        duration = audio.duration

        # Split script
        sentences = [s.strip() for s in script.split(".") if s.strip()]
        per_slide = duration / max(1, len(sentences))
        frames = []

        # Generate images
        for text in sentences:
            img = self.create_image(text)
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            img.save(temp.name)
            frames.append(temp.name)

        # Build video
        print("🎞️ Combining video...")
        clip = ImageSequenceClip(frames, durations=[per_slide] * len(frames))
        clip = clip.set_audio(audio)
        clip.write_videofile(str(video_path), fps=24, codec="libx264", audio_codec="aac", verbose=False, logger=None)

        print(f"✅ Video saved to: {video_path}")
        return str(video_path)
