import os
import tempfile
import random
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
import google.generativeai as genai
from gtts import gTTS


class VideoMaker:
    def __init__(self, gemini_api_key=None):
        self.gemini_api_key = gemini_api_key
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.model = None

    def generate_script(self, prompt: str) -> str:
        if self.model:
            try:
                response = self.model.generate_content(f"Write a short engaging script about: {prompt}.")
                return response.text.strip()
            except Exception as e:
                print("❌ Gemini failed:", e)
                return f"This is a sample video about {prompt}. AI generation failed."
        else:
            return f"This is a simple video about {prompt}. Gemini not configured."

    def make_audio(self, text: str) -> str:
        """Generate voice narration."""
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts = gTTS(text)
        tts.save(temp_audio.name)
        return temp_audio.name

    def make_video(self, prompt: str) -> str:
        """Generate a real AI-style video (text + background + voice)."""
        script = self.generate_script(prompt)
        audio_path = self.make_audio(script)

        # Generate simple visual slides
        keywords = script.split(".")[:5]
        clips = []
        for sentence in keywords:
            bg_color = random.choice([(20, 20, 20), (40, 60, 120), (0, 0, 0)])
            img = Image.new("RGB", (1280, 720), color=bg_color)
            draw = ImageDraw.Draw(img)

            # Font setup
            try:
                font = ImageFont.truetype("arial.ttf", 48)
            except:
                font = ImageFont.load_default()

            text = sentence.strip()
            if not text:
                continue

            # Wrap text roughly in the center
            draw.text((100, 300), text, fill="white", font=font)

            temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            img.save(temp_img.name)
            clips.append(ImageClip(temp_img.name).set_duration(3))

        if not clips:
            raise ValueError("No slides generated.")

        final_clip = concatenate_videoclips(clips, method="compose")

        # Add narration
        audio_clip = AudioFileClip(audio_path)
        final_clip = final_clip.set_audio(audio_clip)

        output_path = os.path.join(tempfile.gettempdir(), "ai_video.mp4")
        final_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", verbose=False, logger=None)
        return output_path
