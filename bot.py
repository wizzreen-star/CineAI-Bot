import os
import threading
import discord
from discord.ext import commands
from flask import Flask
from dotenv import load_dotenv
import google.generativeai as genai
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import moviepy.editor as mp

# =========================
# Load environment variables
# =========================
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
YOUTUBE_CLIENT_SECRET_FILE = os.getenv("YOUTUBE_CLIENT_SECRET_FILE")  # optional path

if not DISCORD_TOKEN:
    raise ValueError("❌ DISCORD_TOKEN is missing in environment variables")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY is missing in environment variables")

print("✅ Environment variables loaded successfully.")

# =========================
# Flask App Setup (for Render)
# =========================
app = Flask(__name__)

@app.route('/')
def home():
    return "🎬 CineAI Bot is live and running with Gemini + Discord + YouTube!"

# =========================
# Discord Bot Setup
# =========================
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# Gemini AI Setup
# =========================
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# =========================
# YouTube Upload Function
# =========================
def upload_to_youtube(title, description, video_path, category="22", privacy="public"):
    """Uploads a video to YouTube using OAuth credentials (requires setup)."""
    try:
        youtube = build("youtube", "v3")
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title, "description": description, "categoryId": category},
                "status": {"privacyStatus": privacy},
            },
            media_body=MediaFileUpload(video_path)
        )
        response = request.execute()
        print(f"✅ Uploaded to YouTube: https://youtu.be/{response['id']}")
        return response
    except Exception as e:
        print(f"❌ YouTube upload failed: {e}")
        return None

# =========================
# Video Generation Function
# =========================
def create_video_from_text(prompt):
    """Uses Gemini to generate script & MoviePy to make a video."""
    print(f"🎨 Generating video idea for: {prompt}")
    try:
        response = model.generate_content(f"Create a short fun video script for: {prompt}")
        script = response.text
        print(f"📝 Script generated:\n{script}")

        # Create video from text (simple black background)
        clip = mp.TextClip(script, fontsize=40, color='white', bg_color='black', size=(1280, 720))
        clip = clip.set_duration(10)
        output_path = f"{prompt.replace(' ', '_')}.mp4"
        clip.write_videofile(output_path, fps=24)

        print(f"🎬 Video created: {output_path}")
        return output_path, script
    except Exception as e:
        print(f"❌ Video creation failed: {e}")
        return None, None

# =========================
# Discord Commands
# =========================
@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")

@bot.command(name="makevideo")
async def makevideo(ctx, *, prompt: str):
    """Command: !makevideo cat playing piano"""
    await ctx.send(f"💡 Thinking of an idea for: **{prompt}** ...")
    video_path, script = create_video_from_text(prompt)

    if video_path:
        await ctx.send("✅ Video created successfully! Uploading to YouTube...")
        upload_to_youtube(f"{prompt.title()} - AI Short", script, video_path)
        await ctx.send("📹 Video uploaded to YouTube!")
    else:
        await ctx.send("❌ Failed to create the video. Check server logs.")

# =========================
# Run Flask + Discord Together
# =========================
def start_flask():
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Starting Flask server on port {port} ...")
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    threading.Thread(target=start_flask, daemon=True).start()
    bot.run(DISCORD_TOKEN)
