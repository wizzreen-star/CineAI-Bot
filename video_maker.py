# ==========================================================
# 🎥 video_maker.py — Real AI Video Builder (Gemini + MoviePy)
# ==========================================================

import os
import tempfile
import textwrap
import requests
import random
import moviepy.editor as mp
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont

try:
    import google.generativeai as genai
except Exception:
    genai = None


class VideoMaker:
    def __init__(self, gemini_api_key=None):
        self.gemini_api_key = gemini_api_key
        if gemai and gemini_api_key:
            genai.configure(api_key=gemini_api_key)

        self.font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    # ----------------------------------------------------
    def generate_script(self, prompt: str) -> str:
        """Generate script with Gemini or fallback."""
        if genai and self.gemini_api_key:
            try:
                model = genai.GenerativeModel("gemini-pro")
                response = model.generate_content(
                    f"Write a short, cinematic 1-minute video narration script about: {prompt}. Keep it natural and emotional."
                )
                if response.text:
                    return response.text.strip()
            except Exception as e:
                print("⚠️ Gemini failed, using fallback:", e)

        # Fallback script
        return (
            f"🎬 Title: {prompt}\n\n"
            "Scene 1: A captivating introduction.\n"
            "Scene 2: The main idea or story.\n"
            "Scene 3: A real-life example.\n"
            "Scene 4: Conclusion and impact.\n"
        )

    # ----------------------------------------------------
    def download_random_clip(self, keyword: str, duration: int = 5) -> mp.VideoFileClip:
        """Try downloading a real video or fallback to colored background."""
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        temp_path = temp.name

        try:
            # Try Pexels free video API (requires optional API key)
            PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
            if PEXELS_API_KEY:
                url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=1"
                res = requests.get(url, headers={"Authorization": PEXELS_API_KEY})
                data = res.json()
                if "videos" in data and data["videos"]:
                    video_url = data["videos"][0]["video_files"][0]["link"]
                    vid = requests.get(video_url)
                    with open(temp_path, "wb") as f:
                        f.write(vid.content)
                    return mp.VideoFileClip(temp_path).subclip(0, min(duration, 5))
        except Exception as e:
            print("⚠️ Pexels video download failed:", e)

        # fallback: create color slide
        color = random.choice([(0,0,0),(10,10,40),(30,0,50),(60,60,60)])
        img = Image.new("RGB", (1280,720), color=color)
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(self.font_path, 50)
        text = keyword.capitalize()
        w, h = draw.textsize(text, font=font)
        draw.text(((1280-w)/2,(720-h)/2), text, font=font, fill="white")
        slide_path = temp_path.replace(".mp4",".png")
        img.save(slide_path)
        return mp.ImageClip(slide_path).set_duration(duration)

    # ----------------------------------------------------
    async def make_video_for_prompt(self, prompt: str, notify_func=None) -> str:
        """Make full narrated video from text."""
        def log(msg):
            if notify_func:
                notify_func(msg)
            else:
                print(msg)

        log("✍️ Writing script...")
        script = self.generate_script(prompt)

        log("🎙️ Generating voice narration...")
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        tts = gTTS(script)
        tts.save(temp_audio)

        narration = mp.AudioFileClip(temp_audio)
        total_duration = narration.duration

        log("📹 Building real scenes...")
        keywords = [prompt] + ["cinematic", "beautiful landscape", "inspiring scene"]
        random.shuffle(keywords)
        clips = [self.download_random_clip(k, duration=int(total_duration/len(keywords))) for k in keywords]

        final_video = mp.concatenate_videoclips(clips, method="compose")
        final_video = final_video.set_audio(narration).set_fps(24)

        log("🖋️ Adding subtitles...")
        txt_clip = mp.TextClip(prompt, fontsize=60, color='white', size=(1280, None), method='caption', align='center')
        txt_clip = txt_clip.set_duration(3).set_position(('center', 0.8), relative=True)
        final_video = mp.CompositeVideoClip([final_video, txt_clip])

        temp_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        final_video.write_videofile(temp_video, codec="libx264", audio_codec="aac", verbose=False, logger=None)

        narration.close()
        log("✅ Done! Returning video file.")
        return temp_video
