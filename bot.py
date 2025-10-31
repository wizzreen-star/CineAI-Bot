import os
import threading
import discord
from discord.ext import commands
from flask import Flask
import google.generativeai as genai
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
import requests
import moviepy.editor as mp

# === ENVIRONMENT VARIABLES ===
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN:
    print("❌ DISCORD_TOKEN not found in environment variables!")
if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY not found in environment variables!")
else:
    print("✅ GEMINI_API_KEY loaded successfully.")

# === GEMINI AI SETUP ===
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# === DISCORD BOT SETUP ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# === FLASK SETUP (Render Port Binding) ===
app = Flask(__name__)

@app.route('/')
def home():
    return "🎬 CineAI Bot is live and running with Gemini + Discord + YouTube!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# === DISCORD EVENTS ===
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def hello(ctx):
    await ctx.send("👋 Hello! I’m CineAI — your AI-powered video creator bot!")

@bot.command()
async def idea(ctx, *, prompt: str):
    """Generate an idea using Gemini AI"""
    await ctx.send(f"💡 Thinking of an idea for: **{prompt}** ...")

    try:
        response = model.generate_content(f"Create a short video concept for: {prompt}")
        idea_text = response.text.strip()
        await ctx.send(f"🎬 Here's your idea:\n\n{idea_text}")
    except Exception as e:
        await ctx.send(f"⚠️ Gemini error: {e}")

@bot.command()
async def video(ctx, *, prompt: str):
    """Generate a simple AI-based video using Gemini"""
    await ctx.send(f"🎞️ Creating a short AI video for: **{prompt}**...")

    # Ask Gemini for a short script
    response = model.generate_content(f"Write a short video script about: {prompt}")
    script = response.text.strip()

    # Generate a dummy video with text (MoviePy)
    clip = mp.TextClip(script, fontsize=40, color='white', bg_color='black', size=(720, 480))
    clip = clip.set_duration(5)
    clip.write_videofile("output.mp4", fps=24)

    await ctx.send("✅ Video generated successfully!")
    await ctx.send(file=discord.File("output.mp4"))

# === YOUTUBE UPLOAD ===
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def youtube_upload(video_file, title, description):
    """Upload a video to YouTube"""
    flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", YOUTUBE_SCOPES)
    credentials = flow.run_local_server(port=8080)

    youtube = build("youtube", "v3", credentials=credentials)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["AI", "CineAI", "Gemini", "Automation"]
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=MediaFileUpload(video_file)
    )
    response = request.execute()
    print(f"✅ Uploaded video: https://www.youtube.com/watch?v={response['id']}")
    return response['id']

@bot.command()
async def upload(ctx, *, title: str):
    """Upload the last generated video to YouTube"""
    await ctx.send(f"📤 Uploading video: **{title}** ...")
    try:
        video_id = youtube_upload("output.mp4", title, "Auto-uploaded by CineAI Bot using Gemini AI")
        await ctx.send(f"✅ Uploaded successfully!\n📺 https://www.youtube.com/watch?v={video_id}")
    except Exception as e:
        await ctx.send(f"❌ Upload failed: {e}")

# === START FLASK IN BACKGROUND THREAD ===
threading.Thread(target=run_flask).start()

# === RUN DISCORD BOT ===
bot.run(DISCORD_TOKEN)# ===============================
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("❌ DISCORD_TOKEN missing — bot not started.")
