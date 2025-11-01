import os
import tempfile
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
import google.generativeai as genai
import requests
from io import BytesIO
from gtts import gTTS


class VideoMaker:
    def __init__(self, gemini_api_key=None):
        self.gemini_api_key = gemini_api_key
        if genai and gemini_api_key:
            genai.configure(api_key=gemini_api_key)

        self.font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    # ✍️ Generate a short AI script
    def generate_script(self, topic: str):
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"Write a short video narration script (3-5 sentences) about: {topic}"
        response = model.generate_content(prompt)
        return response.text.strip()

    # 🖼️ Generate an image using Gemini
    def generate_image(self, prompt: str):
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            image_response = model.generate_content(f"Generate a realistic image of: {prompt}")
            image_url = image_response.candidates[0].content.parts[0].text

            if image_url.startswith("http"):
                img_data = requests.get(image_url).content
                return Image.open(BytesIO(img_data)).convert("RGB")
            else:
                raise ValueError("Invalid image URL")
        except Exception as e:
            print(f"⚠️ Image generation failed: {e}")
            # fallback to simple black image with text
            img = Image.new("RGB", (1280, 720), color=(0, 0, 0))
            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype(self.font_path, 48)
            draw.text((50, 300), prompt, font=font, fill=(255, 255, 255))
            return img

    # 🎙️ Generate narration using gTTS
    def generate_voice(self, text: str):
        tts = gTTS(text)
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(temp_audio.name)
        return temp_audio.name

    # 🎬 Make video
    def make_video(self, topic: str):
        script = self.generate_script(topic)
        sentences = script.split(".")
        image_clips = []

        for line in sentences:
            line = line.strip()
            if not line:
                continue

            img = self.generate_image(line)
            temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            img.save(temp_img.name)

            clip = ImageClip(temp_img.name).set_duration(4)
            image_clips.append(clip)

        final_video = concatenate_videoclips(image_clips, method="compose")

        # voiceover
        audio_path = self.generate_voice(script)
        audio_clip = AudioFileClip(audio_path)
        final_video = final_video.set_audio(audio_clip)

        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")

        return output_path        random.shuffle(keywords)
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
