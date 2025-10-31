import os
import discord
from discord.ext import commands
from flask import Flask
import google.generativeai as genai
from moviepy.editor import TextClip, concatenate_videoclips
import requests
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# =====================================================
# ✅ Load environment variables
# =====================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY not found in environment variables!")
else:
    print("✅ GEMINI_API_KEY loaded successfully.")

if not DISCORD_TOKEN:
    print("❌ DISCORD_TOKEN not found in environment variables!")
else:
    print("✅ DISCORD_TOKEN loaded successfully.")

# =====================================================
# ✅ Flask setup (for Render port binding)
# =====================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "CineAI Bot is running successfully!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

# =====================================================
# ✅ Discord Bot Setup
# =====================================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

genai.configure(api_key=GEMINI_API_KEY)

# =====================================================
# ✅ Helper Functions
# =====================================================

def create_video_from_text(text, output_path="output.mp4"):
    """Create a simple text-based video using MoviePy."""
    clip = TextClip(text, fontsize=48, color='white', size=(1280, 720), bg_color='black', duration=5)
    clip.write_videofile(output_path, fps=24)
    return output_path


def upload_to_youtube(title, description, file_path):
    """Upload a video to YouTube (requires OAuth token setup)."""
    try:
        creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/youtube.upload"])
        youtube = build("youtube", "v3", credentials=creds)

        request_body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["AI", "CineAI", "Gemini"],
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "public"
            }
        }

        media = MediaFileUpload(file_path, resumable=True)
        upload_request = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media
        )
        response = upload_request.execute()
        return f"https://youtu.be/{response['id']}"
    except Exception as e:
        return f"❌ Upload failed: {e}"


# =====================================================
# ✅ Discord Commands
# =====================================================

@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")


@bot.command()
async def video(ctx, *, prompt: str):
    """Generate video idea, create video, upload to YouTube."""
    await ctx.send(f"💡 Thinking of an idea for: **{prompt}** ...")

    # Generate text using Gemini
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(f"Create a short YouTube video script about: {prompt}")
    idea_text = response.text

    await ctx.send("🎬 Creating video...")

    # Create video
    video_path = create_video_from_text(idea_text)
    await ctx.send("📤 Uploading to YouTube...")

    # Upload video
    youtube_url = upload_to_youtube(prompt, idea_text, video_path)
    await ctx.send(f"✅ Uploaded! Watch it here: {youtube_url}")


# =====================================================
# ✅ Run Discord Bot
# =====================================================
bot.run(DISCORD_TOKEN)
