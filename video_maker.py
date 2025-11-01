import os
import random
import tempfile
from moviepy.editor import *
from gtts import gTTS
import requests
from PIL import Image
from io import BytesIO

class VideoMaker:
    def __init__(self, gemini_api_key=None):
        self.gemini_api_key = gemini_api_key

    async def make_video(self, prompt, notify_func=None):
        """Generate a video with images, text, and narration."""
        if notify_func:
            await notify_func("✍️ Writing script...")

        # Create simple narration script
        script = f"This video is about {prompt}. Let's explore the topic in depth and discover how it impacts our world."

        if notify_func:
            await notify_func("🎙️ Generating voice narration...")

        # Generate voice using gTTS
        tts = gTTS(script)
        voice_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        tts.save(voice_path)

        if notify_func:
            await notify_func("🖼️ Creating video slides...")

        # Download some random images from Unsplash (based on keywords)
        keywords = prompt.split()
        random.shuffle(keywords)
        images = []

        for word in keywords[:3]:  # Limit to 3 images
            try:
                url = f"https://source.unsplash.com/1280x720/?{word}"
                img_data = requests.get(url, timeout=10).content
                img = Image.open(BytesIO(img_data)).convert("RGB")
                path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
                img.save(path)
                images.append(path)
            except Exception:
                continue

        # If no images downloaded, fallback to black background
        if not images:
            clip = ColorClip(size=(1280, 720), color=(0, 0, 0), duration=10)
            clip = clip.set_audio(AudioFileClip(voice_path))
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            clip.write_videofile(output_path, fps=24)
            return output_path

        # Create slideshow from images
        clips = []
        for img_path in images:
            img_clip = ImageClip(img_path).set_duration(5)
            txt_clip = TextClip(prompt, fontsize=48, color='white', size=(1200, None), method='caption')
            txt_clip = txt_clip.set_position('center').set_duration(5)
            clips.append(CompositeVideoClip([img_clip, txt_clip]))

        video = concatenate_videoclips(clips, method="compose")

        # Add audio
        audio = AudioFileClip(voice_path)
        final_video = video.set_audio(audio)

        # Export video
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        final_video.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')

        if notify_func:
            await notify_func("✅ Video generation complete!")

        return output_path
