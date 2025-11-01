import os
import tempfile
import textwrap
import requests
from moviepy.editor import (
    ImageClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeVideoClip
)
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# Optional AI Image generator key (Gemini or other)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def generate_image(prompt):
    """
    Generate a relevant image for the scene using Gemini (if key available)
    or fallback to Unsplash.
    """
    try:
        if GEMINI_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("imagen-3.0")
            img = model.generate_images(prompt)[0]
            img.save("scene.jpg")
            return "scene.jpg"
        else:
            # Fallback: Unsplash (no API needed)
            response = requests.get(
                f"https://source.unsplash.com/1280x720/?{prompt.replace(' ', ',')}"
            )
            img = Image.open(BytesIO(response.content))
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            img.save(temp.name)
            return temp.name
    except Exception as e:
        print("⚠️ Image generation failed:", e)
        img = Image.new("RGB", (1280, 720), color=(0, 0, 0))
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        img.save(temp.name)
        return temp.name


def generate_voice(text):
    """
    Convert text to speech using gTTS
    """
    tts = gTTS(text=text, lang="en")
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(temp_audio.name)
    return temp_audio.name


def create_scene(image_path, text, voice_path):
    """
    Create a single scene with image, overlaid text, and synced voice.
    """
    audio_clip = AudioFileClip(voice_path)
    duration = audio_clip.duration

    # Load the image
    clip = ImageClip(image_path).set_duration(duration)

    # Add text overlay on top of image
    txt_clip = (
        ImageClip(make_text_image(text))
        .set_duration(duration)
        .set_position(("center", "bottom"))
        .set_opacity(0.9)
    )

    # Combine image, text, and audio
    final = CompositeVideoClip([clip, txt_clip])
    final = final.set_audio(audio_clip)
    return final


def make_text_image(text):
    """
    Render text into a transparent image for overlay
    """
    img = Image.new("RGBA", (1280, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("arial.ttf", 40)

    wrapped = textwrap.fill(text, width=40)
    w, h = draw.textbbox((0, 0), wrapped, font=font)[2:]

    x = (1280 - w) // 2
    y = (200 - h) // 2
    draw.text((x, y), wrapped, font=font, fill="white")
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp.name)
    return temp.name


def make_video(title, script_text):
    """
    Create a full AI video with narration and scene images
    """
    print(f"🎬 Making video for: {title}")
    sentences = textwrap.wrap(script_text, width=150)
    scenes = []

    for i, sentence in enumerate(sentences, 1):
        print(f"🖼️ Scene {i}: {sentence[:60]}...")
        img_path = generate_image(f"{title}, cinematic, realistic, 8k")
        voice_path = generate_voice(sentence)
        scene = create_scene(img_path, sentence, voice_path)
        scenes.append(scene)

    final_video = concatenate_videoclips(scenes, method="compose")

    temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    final_video.write_videofile(
        temp_path.name,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        verbose=False,
        logger=None
    )

    print(f"✅ Video saved at: {temp_path.name}")
    return temp_path.name
