import discord
from discord.ext import commands
from gtts import gTTS
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
import os
import requests
import base64
from io import BytesIO

from dotenv import load_dotenv
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Use a free Hugging Face model for image generation
HF_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2"
HF_API_KEY = os.getenv("HF_API_KEY")  # optional for free-tier usage

headers = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}

def generate_image(prompt):
    """Generate one AI image from text prompt"""
    data = {"inputs": prompt}
    response = requests.post(HF_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        image_data = response.content
        return ImageClip(BytesIO(image_data)).set_duration(2)
    else:
        raise Exception(f"Image generation failed: {response.text}")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def video(ctx, *, prompt: str):
    """Create a short AI video with images + audio narration"""
    await ctx.send(f"🎬 Generating AI video for: **{prompt}** (please wait 1–2 min)...")

    try:
        # 1. Create speech
        tts = gTTS(prompt)
        tts.save("speech.mp3")

        # 2. Generate multiple images
        clips = []
        for i in range(5):
            img_prompt = f"{prompt}, cinematic lighting, 4k art, frame {i+1}"
            clip = generate_image(img_prompt)
            clips.append(clip)

        # 3. Combine video
        video = concatenate_videoclips(clips, method="compose")
        video = video.set_audio(AudioFileClip("speech.mp3"))
        output_path = "ai_video.mp4"
        video.write_videofile(output_path, fps=24, codec="libx264")

        # 4. Send back to Discord
        await ctx.send(file=discord.File(output_path))

    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

    finally:
        for f in ["speech.mp3", "ai_video.mp4"]:
            if os.path.exists(f):
                os.remove(f)

bot.run(DISCORD_TOKEN)
