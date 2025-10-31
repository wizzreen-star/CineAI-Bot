import os
import json
import discord
from discord.ext import commands
from flask import Flask
import threading
from moviepy.editor import TextClip, concatenate_videoclips
import google.generativeai as genai
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

# ---- Load environment variables ----
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")

# ---- Setup ----
genai.configure(api_key=GEMINI_API_KEY)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
app = Flask(__name__)

@app.route('/')
def home():
    return "🎬 CineAI Bot with YouTube Upload is Live!"

# ---- YouTube Upload Helper ----
def upload_to_youtube(video_path, title, description, tags):
    creds_file = "/tmp/client_secret.json"
    with open(creds_file, "w") as f:
        f.write(YOUTUBE_CLIENT_SECRET)

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
    creds = flow.run_console()

    youtube = build("youtube", "v3", credentials=creds)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "private"
            }
        },
        media_body=video_path
    )
    response = request.execute()
    return response

# ---- Discord Command ----
@bot.command()
async def video(ctx, *, prompt):
    await ctx.send(f"🎥 Generating video for: **{prompt}** ... please wait ⏳")

    try:
        # 1️⃣ Ask Gemini for script
        model = genai.GenerativeModel("gemini-1.5-flash")
        script = model.generate_content(f"Write a short 30s video script about: {prompt}").text
        await ctx.send(f"📝 Script:\n{script}")

        # 2️⃣ Create video
        clips = [TextClip(line, fontsize=40, color='white', size=(720,1280), bg_color='black', duration=2)
                 for line in script.split("\n") if line.strip()]
        final = concatenate_videoclips(clips)
        video_path = "output.mp4"
        final.write_videofile(video_path, fps=24)
        await ctx.send("🎬 Video created!")

        # 3️⃣ Ask Gemini for YouTube metadata
        meta = model.generate_content(
            f"Write a catchy YouTube title, short description, and 10 hashtags for this video about: {prompt}"
        ).text
        await ctx.send(f"🧾 YouTube Info:\n{meta}")

        # Extract details
        lines = meta.split("\n")
        title = lines[0].replace("Title:", "").strip()
        description = "\n".join(lines[1:]).strip()
        tags = [tag.replace("#", "") for tag in description.split() if "#" in tag]

        # 4️⃣ Upload to YouTube
        upload_to_youtube(video_path, title, description, tags)
        await ctx.send("✅ Video uploaded to YouTube!")

    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

# ---- Run Flask + Bot ----
def run_flask():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask).start()
bot.run(DISCORD_TOKEN)
