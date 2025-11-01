# video_maker.py
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
        """Generate cinematic AI-style video with visuals + TTS narration."""
        if notify_func:
            await notify_func("✍️ Writing script...")

        # Create narration text
        script = f"This video explores {prompt}. Let's learn something amazing about it."

        if notify_func:
            await notify_func("🎙️ Generating voice narration...")

        # Text-to-speech
        tts = gTTS(script)
        voice_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        tts.save(voice_path)

        if notify_func:
            await notify_func("🖼️ Fetching visuals...")

        # Get images from Unsplash
        keywords = [w for w in prompt.split() if len(w) > 2]
        random.shuffle(keywords)
        if not keywords:
            keywords = ["nature", "abstract", "sky"]

        images = []
        for word in keywords[:4]:
            try:
                url = f"https://source.unsplash.com/1280x720/?{word}"
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                img = Image.open(BytesIO(resp.content)).convert("RGB")

                # ✅ UNIVERSAL RESIZE FIX (works for Pillow 8–11)
                if hasattr(Image, "Resampling"):
                    resample_filter = Image.Resampling.LANCZOS
                elif hasattr(Image, "LANCZOS"):
                    resample_filter = Image.LANCZOS
                else:
                    resample_filter = Image.BICUBIC

                img = img.resize((1280, 720), resample=resample_filter)
                path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
                img.save(path, format="JPEG", quality=90)
                images.append(path)
            except Exception as e:
                print(f"⚠️ Image download failed for '{word}':", e)

        if not images:
            if notify_func:
                await notify_func("⚠️ No images found, using black background.")
            images = [None]

        if notify_func:
            await notify_func("🎬 Building your video...")

        audio_clip = AudioFileClip(voice_path)
        duration = audio_clip.duration
        per_image = duration / len(images)

        clips = []
        for img in images:
            if img:
                base = ImageClip(img).set_duration(per_image)
            else:
                base = ColorClip(size=(1280, 720), color=(0, 0, 0)).set_duration(per_image)

            # Smooth zoom effect
            zoomed = base.resize(lambda t: 1 + 0.05 * (t / per_image))

            text_clip = TextClip(
                txt=prompt,
                fontsize=50,
                color="white",
                font="DejaVu-Sans",
                stroke_color="black",
                stroke_width=2,
                method="caption",
                size=(1100, None)
            ).set_position(("center", "bottom")).set_duration(per_image)

            clips.append(CompositeVideoClip([zoomed, text_clip], size=(1280, 720)))

        final = concatenate_videoclips(clips, method="compose").set_audio(audio_clip).set_fps(24)
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        final.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            threads=4,
            verbose=False,
            logger=None
        )

        if notify_func:
            await notify_func("✅ Video generated successfully!")

        try:
            audio_clip.close()
        except:
            pass

        return output_path
