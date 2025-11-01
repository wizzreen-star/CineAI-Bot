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
        """Generate a REAL AI video with image backgrounds + voice + text."""

        if notify_func:
            await notify_func("✍️ Writing script...")

        script = f"This video explores {prompt}. Let's dive into how it is shaping our world today."

        if notify_func:
            await notify_func("🎙️ Generating voice narration...")

        # Generate TTS narration
        tts = gTTS(script)
        voice_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        tts.save(voice_path)

        if notify_func:
            await notify_func("🖼️ Downloading background visuals...")

        # Download random topic-related images
        keywords = prompt.split()
        random.shuffle(keywords)
        images = []

        for word in keywords[:4]:
            try:
                url = f"https://source.unsplash.com/1280x720/?{word}"
                response = requests.get(url, timeout=10)
                img = Image.open(BytesIO(response.content)).convert("RGB")
                img_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
                img.save(img_path)
                images.append(img_path)
            except Exception as e:
                print("⚠️ Image download failed:", e)
                continue

        if not images:
            if notify_func:
                await notify_func("⚠️ No images found — using fallback visuals.")
            images = [None]

        if notify_func:
            await notify_func("🎬 Building cinematic video...")

        # Load voice
        audio_clip = AudioFileClip(voice_path)
        duration = audio_clip.duration
        per_image = duration / len(images)

        clips = []
        for i, img_path in enumerate(images):
            if img_path:
                img_clip = ImageClip(img_path).set_duration(per_image)
            else:
                img_clip = ColorClip(size=(1280, 720), color=(0, 0, 0)).set_duration(per_image)

            # Add subtle zoom-in effect
            img_clip = img_clip.fx(vfx.zoom_in, 1.05)

            # Overlay caption text
            text_clip = TextClip(
                txt=prompt,
                fontsize=48,
                color='white',
                stroke_color='black',
                stroke_width=2,
                font="DejaVu-Sans",
                size=(1200, None),
                method='caption'
            ).set_position(('center', 'bottom')).set_duration(per_image)

            final_frame = CompositeVideoClip([img_clip, text_clip])
            clips.append(final_frame)

        video = concatenate_videoclips(clips, method="compose")
        final_video = video.set_audio(audio_clip)

        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        final_video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            preset="medium"
        )

        if notify_func:
            await notify_func("✅ Video ready! Sending now...")

        return output_path
