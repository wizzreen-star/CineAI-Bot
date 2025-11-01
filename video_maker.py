import os
import io
import textwrap
import numpy as np
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip

def make_video(script_text: str, topic: str) -> str:
    """
    Generate a narrated video using TTS + slideshow.
    Returns path to the created video file.
    """

    # === Step 1: Split text into slides ===
    lines = [line.strip() for line in script_text.split(".") if line.strip()]
    if not lines:
        lines = ["(No content provided)"]

    slides = []

    for line in lines:
        # === Create a blank image ===
        img = Image.new("RGB", (1280, 720), color=(15, 15, 15))
        draw = ImageDraw.Draw(img)

        # === Load font ===
        try:
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            font = ImageFont.truetype(font_path, 50)
        except Exception:
            font = ImageFont.load_default()

        # === Wrap and center text ===
        wrapped = textwrap.fill(line, width=25)
        text_w, text_h = draw.multiline_textbbox((0, 0), wrapped, font=font)[2:]
        x = (1280 - text_w) // 2
        y = (720 - text_h) // 2
        draw.multiline_text((x, y), wrapped, font=font, fill=(240, 240, 240), align="center")

        # === Convert image to numpy array for moviepy ===
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        frame = np.array(Image.open(buf))
        slides.append(frame)

    # === Step 2: Create video from slides ===
    clips = []
    for i, frame in enumerate(slides):
        clip = ImageClip(frame).set_duration(3)
        if i > 0:
            clip = clip.crossfadein(0.5)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")

    # === Step 3: Add narration ===
    audio_path = "narration.mp3"
    tts = gTTS(script_text)
    tts.save(audio_path)
    narration = AudioFileClip(audio_path)

    # Optional: Add background music (if file exists)
    bg_music_path = "background.mp3"
    if os.path.exists(bg_music_path):
        bg_music = AudioFileClip(bg_music_path).volumex(0.15)
        final_audio = CompositeAudioClip([narration, bg_music.set_duration(narration.duration)])
    else:
        final_audio = narration

    video = video.set_audio(final_audio)

    # === Step 4: Export final video ===
    temp_path = f"{topic.replace(' ', '_')}.mp4"
    video.write_videofile(temp_path, fps=24, codec="libx264", audio_codec="aac")

    # Cleanup
    narration.close()
    if os.path.exists(audio_path):
        os.remove(audio_path)

    # === Step 5: Return path ===
    return temp_path
