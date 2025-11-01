import os
import tempfile
import textwrap
import requests
from moviepy.editor import (
    ImageClip,
    concatenate_videoclips,
    AudioFileClip,
)
from gtts import gTTS
from PIL import Image
from io import BytesIO

# 🔑 Optional: use your Gemini / OpenAI / HuggingFace key if available
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ==============================
# Helper: Generate image with fallback
# ==============================
def generate_image(prompt):
    """
    Generate an image using OpenAI or fallback to Unsplash.
    """
    try:
        if GEMINI_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("imagen-3.0")
            img = model.generate_images(prompt)[0]
            img.save("temp_img.jpg")
            return "temp_img.jpg"
        else:
            # Fallback: Unsplash image
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


# ==============================
# Helper: Generate voiceover
# ==============================
def generate_voiceover(text, lang="en"):
    """
    Convert text to speech using gTTS
    """
    tts = gTTS(text=text, lang=lang)
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(temp_audio.name)
    return temp_audio.name


# ==============================
# Main function: make video
# ==============================
def make_video(title, script_text):
    """
    Create a narrated slideshow video with AI images + voiceover
    """
    print(f"🎬 Building video for: {title}")

    # Split script into short scenes
    sentences = textwrap.wrap(script_text, width=150)
    clips = []
    audio_paths = []

    for i, sentence in enumerate(sentences, 1):
        print(f"🖼️ Scene {i}: {sentence[:60]}...")
        img_path = generate_image(f"{title}, cinematic, realistic, high quality")
        audio_path = generate_voiceover(sentence)
        audio_paths.append(audio_path)

        # Create video clip with image
        img_clip = ImageClip(img_path).set_duration(6)
        audio_clip = AudioFileClip(audio_path)
        img_clip = img_clip.set_audio(audio_clip)
        clips.append(img_clip)

    # Combine all scenes
    final_video = concatenate_videoclips(clips, method="compose")

    # Save video file
    temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    final_video.write_videofile(
        temp_path.name,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        verbose=False,
        logger=None
    )

    # Cleanup
    for p in audio_paths:
        try:
            os.remove(p)
        except:
            pass

    print(f"✅ Video created: {temp_path.name}")
    return temp_path.name
