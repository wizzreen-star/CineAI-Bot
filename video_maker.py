import os
import random
import tempfile
from io import BytesIO
import requests
from moviepy.editor import *
from gtts import gTTS
from PIL import Image

class VideoMaker:
    def __init__(self, gemini_api_key=None):
        self.gemini_api_key = gemini_api_key

    async def make_video(self, prompt, notify_func=None):
        """Generate cinematic video with voice, text, and real backgrounds."""

        if notify_func:
            await notify_func("✍️ Writing script...")

        # Simple AI-style narration
        script = f"This video explores {prompt}. Let's discover what makes it so fascinating."

        if notify_func:
            await notify_func("🎙️ Generating voice narration...")

        # Generate TTS audio
        tts = gTTS(script)
        voice_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        tts.save(voice_path)

        if notify_func:
            await notify_func("🖼️ Downloading real visuals...")

        # Download 4 images from Unsplash
        keywords = prompt.split()
        random.shuffle(keywords)
        images = []

        for word in keywords[:4]:
            try:
                url = f"https://source.unsplash.com/1280x720/?{word}"
                response = requests.get(url, timeout=10)
                img = Image.open(BytesIO(response.content)).convert("RGB")
                
                # ✅ Fixed ANTIALIAS deprecation
                if hasattr(Image, 'Resampling'):
                    img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                else:
                    img = img.resize((1280, 720), Image.ANTIALIAS)
                
                img_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
                img.save(img_path)
                images.append(img_path)
            except Exception as e:
                print("⚠️ Image fetch failed:", e)
                continue

        if not images:
            if notify_func:
                await notify_func("⚠️ No visuals found — using fallback background.")
            images = [None]

        if notify_func:
            await notify_func("🎬 Building cinematic video...")

        audio_clip = AudioFileClip(voice_path)
        duration = audio_clip.duration
        per_image = duration / len(images)

        clips = []
        for img_path in images:
            if img_path:
                clip = ImageClip(img_path).set_duration(per_image)
            else:
                clip = ColorClip(size=(1280, 720), color=(0, 0, 0)).set_duration(per_image)

            # ✅ Manual zoom effect (replaces moviepy.vfx.zoom_in)
            zoom_clip = clip.fl(lambda gf, t: gf(t), apply_to=['mask'])
            zoom_clip = zoom_clip.resize(lambda t: 1 + 0.03 * t)  # zoom 3% per sec

            # Add overlay text
            text = TextClip(
                txt=prompt,
                fontsize=48,
                color='white',
                font="DejaVu-Sans",
                stroke_color='black',
                stroke_width=2,
                size=(1200, None),
                method='caption'
            ).set_position(('center', 'bottom')).set_duration(per_image)

            final_frame = CompositeVideoClip([zoom_clip, text])
            clips.append(final_frame)

        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio_clip)

        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        final_video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            preset="medium",
            verbose=False,
            logger=None
        )

        if notify_func:
            await notify_func("✅ Video ready! Sending now...")

        return output_path
