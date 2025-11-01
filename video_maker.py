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
        """Generate cinematic video with voice, text, and real backgrounds."""

        if notify_func:
            await notify_func("✍️ Writing script...")

        # Create a simple narration script (replace with Gemini if available)
        script = f"This video explores {prompt}. Let's discover what makes it so fascinating."

        if notify_func:
            await notify_func("🎙️ Generating voice narration...")

        # Generate TTS audio
        tts = gTTS(script)
        voice_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        tts.save(voice_path)

        if notify_func:
            await notify_func("🖼️ Downloading visuals...")

        # Download up to 4 related images from Unsplash
        keywords = [w for w in prompt.split() if len(w) > 1]
        if not keywords:
            keywords = ["nature", "technology", "people"]
        random.shuffle(keywords)

        images = []
        for word in keywords[:4]:
            try:
                url = f"https://source.unsplash.com/1280x720/?{word}"
                resp = requests.get(url, timeout=12)
                resp.raise_for_status()
                img = Image.open(BytesIO(resp.content)).convert("RGB")

                # Robust resampling: compatible with Pillow 9.x and 10+
                try:
                    # Pillow >= 10: Image.Resampling.LANCZOS
                    resample_filter = Image.Resampling.LANCZOS
                except Exception:
                    # Pillow < 10: Image.LANCZOS exists, else fallback to default
                    resample_filter = getattr(Image, "LANCZOS", Image.NEAREST)

                img = img.resize((1280, 720), resample_filter)
                img_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
                img.save(img_path, format="JPEG", quality=85)
                images.append(img_path)
            except Exception as e:
                print("⚠️ Image fetch failed for", word, ":", e)
                continue

        if not images:
            # fallback to a solid color clip if no images downloaded
            if notify_func:
                await notify_func("⚠️ No images found — using fallback background.")
            images = [None]

        if notify_func:
            await notify_func("🎬 Building video...")

        # Load audio
        audio_clip = AudioFileClip(voice_path)
        duration = audio_clip.duration if audio_clip.duration else max(6, len(script)/10)
        per_image = duration / len(images)

        clips = []
        for img_path in images:
            if img_path:
                base = ImageClip(img_path).set_duration(per_image)
            else:
                base = ColorClip(size=(1280, 720), color=(20, 20, 20)).set_duration(per_image)

            # Manual smooth zoom: resize factor grows slightly over clip duration
            # we use lambda t -> scale (1.0 to 1.06 over the clip)
            def zoom(get_frame, t):
                frame = get_frame(t)
                return frame
            # Use resize with a time-dependent factor
            zoom_clip = base.resize(lambda t: 1 + 0.06 * (t / per_image))  # 6% zoom across the duration

            # Text overlay (caption) - ensures readability with stroke
            text_clip = TextClip(
                txt=prompt,
                fontsize=44,
                color='white',
                font='DejaVu-Sans',
                stroke_color='black',
                stroke_width=2,
                method='caption',
                size=(1100, None),
            ).set_duration(per_image).set_position(('center', 'bottom'))

            # Composite image + text
            frame = CompositeVideoClip([zoom_clip, text_clip], size=(1280, 720)).set_duration(per_image)
            clips.append(frame)

        # Concatenate clips and attach audio
        final_video = concatenate_videoclips(clips, method="compose")
        final_video = final_video.set_audio(audio_clip).set_fps(24)

        # Export
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            threads=4,
            preset="medium",
            verbose=False,
            logger=None
        )

        if notify_func:
            await notify_func("✅ Video ready!")

        # cleanup temp audio? (keep for debugging)
        try:
            audio_clip.close()
        except Exception:
            pass

        return output_path
