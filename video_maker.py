# ==========================================================
# 🎬 video_maker.py — Realistic AI Video Generator (Gemini + MoviePy)
# ==========================================================

import os
import tempfile
import random
import requests
import textwrap
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class VideoMaker:
    def __init__(self, gemini_api_key=None):
        self.gemini_api_key = gemini_api_key
        if genai and gemini_api_key:
            genai.configure(api_key=gemini_api_key)

        self.font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    # ---------------------------------------------------------
    def generate_script(self, topic: str) -> str:
        """Generate video script using Gemini or fallback."""
        if genai and self.gemini_api_key:
            try:
                model = genai.GenerativeModel("gemini-pro")
                response = model.generate_content(
                    f"Write a cinematic short narration script (around 1 minute) about: {topic}."
                )
                if response.text:
                    return response.text.strip()
            except Exception as e:
                print("⚠️ Gemini generation failed, fallback:", e)

        # fallback script
        return (
            f"🎬 Title: {topic}\n\n"
            "Scene 1: A powerful opening.\n"
            "Scene 2: The main idea.\n"
            "Scene 3: Real-world impact.\n"
            "Scene 4: Conclusion and inspiration.\n"
        )

    # ---------------------------------------------------------
    def download_clip(self, keyword: str, duration: int = 5) -> mp.VideoClip:
        """Download stock clip or create colored fallback."""
        tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tmp_path = tmpfile.name

        # Try stock video API
        try:
            pexels_key = os.getenv("PEXELS_API_KEY")
            if pexels_key:
                url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=1"
                res = requests.get(url, headers={"Authorization": pexels_key})
                data = res.json()
                if "videos" in data and len(data["videos"]) > 0:
                    video_url = data["videos"][0]["video_files"][0]["link"]
                    v = requests.get(video_url)
                    with open(tmp_path, "wb") as f:
                        f.write(v.content)
                    return mp.VideoFileClip(tmp_path).subclip(0, min(duration, 5))
        except Exception as e:
            print("⚠️ Pexels download failed:", e)

        # fallback color slide
        img = Image.new("RGB", (1280, 720), color=random.choice([(0,0,0),(20,20,60),(50,0,80)]))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(self.font_path, 50)
        text = keyword.capitalize()
        bbox = draw.textbbox((0,0), text, font=font)
        w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
        draw.text(((1280-w)/2, (720-h)/2), text, font=font, fill="white")

        slide_path = tmp_path.replace(".mp4", ".png")
        img.save(slide_path)
        return mp.ImageClip(slide_path).set_duration(duration)

    # ---------------------------------------------------------
    async def make_video_for_prompt(self, topic: str, notify=None) -> str:
        """Make full narrated AI video."""
        def log(msg):
            if notify:
                notify(msg)
            else:
                print(msg)

        log("✍️ Writing script...")
        script = self.generate_script(topic)

        log("🎙️ Generating narration...")
        tts_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        tts = gTTS(script)
        tts.save(tts_path)
        narration = mp.AudioFileClip(tts_path)
        total_dur = narration.duration

        log("🎞️ Assembling video scenes...")
        keywords = [topic, "cinematic", "nature", "technology", "cityscape"]
        random.shuffle(keywords)
        clip_dur = max(4, int(total_dur / len(keywords)))

        clips = [self.download_clip(k, clip_dur) for k in keywords]
        final_clip = mp.concatenate_videoclips(clips, method="compose").set_audio(narration).set_fps(24)

        log("🖋️ Adding title overlay...")
        txt = mp.TextClip(topic, fontsize=70, color='white', font='DejaVu-Sans')
        txt = txt.set_position(('center', 'bottom')).set_duration(3)
        composed = mp.CompositeVideoClip([final_clip, txt])

        log("💾 Rendering video...")
        out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        composed.write_videofile(out_path, codec='libx264', audio_codec='aac', verbose=False, logger=None)

        narration.close()
        log("✅ Done! Returning video.")
        return out_path
