import os
import google.generativeai as genai
import discord
from discord.ext import commands
from moviepy.editor import TextClip, CompositeVideoClip, ColorClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# === API KEYS ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY missing.")
else:
    print("✅ GEMINI_API_KEY loaded successfully.")

if not DISCORD_TOKEN:
    print("❌ DISCORD_TOKEN missing.")
else:
    print("✅ DISCORD_TOKEN loaded successfully.")

# === Configure Gemini ===
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# === Discord Bot ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# === YouTube Auth ===
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
def get_youtube_service():
    creds = None
    if os.path.exists("token.pkl"):
        with open("token.pkl", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=8080)
        with open("token.pkl", "wb") as token:
            pickle.dump(creds, token)
    return build("youtube", "v3", credentials=creds)

# === Video Generator ===
def create_ai_video(script, title):
    clip = ColorClip(size=(1280, 720), color=(0, 0, 0), duration=10)
    text = TextClip(script, fontsize=40, color='white', size=(1200, None), method='caption').set_duration(10)
    video = CompositeVideoClip([clip, text.set_position("center")])
    video.write_videofile("ai_video.mp4", fps=24)
    return "ai_video.mp4"

# === YouTube Upload ===
def upload_to_youtube(filename, title, description, tags):
    youtube = get_youtube_service()
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22"
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=MediaFileUpload(filename)
    )
    response = request.execute()
    return f"https://youtube.com/watch?v={response['id']}"

# === Commands ===
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def auto(ctx, *, prompt: str):
    await ctx.send(f"🎬 Creating YouTube video for: **{prompt}** ...")

    response = model.generate_content(
        f"Create a short YouTube video script, title, and description for: {prompt}. "
        f"Format as:\nTITLE: ...\nDESCRIPTION: ...\nSCRIPT: ...\nTAGS: ..."
    )

    text = response.text
    title = text.split("TITLE:")[1].split("DESCRIPTION:")[0].strip()
    description = text.split("DESCRIPTION:")[1].split("SCRIPT:")[0].strip()
    script = text.split("SCRIPT:")[1].split("TAGS:")[0].strip()
    tags = text.split("TAGS:")[1].split() if "TAGS:" in text else ["AI", "CineAI"]

    video_path = create_ai_video(script, title)
    youtube_link = upload_to_youtube(video_path, title, description, tags)

    await ctx.send(f"✅ Uploaded successfully! Watch here: {youtube_link}")

# === Flask keepalive (for Render) ===
from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "CineAI Bot is live!"

if __name__ == "__main__":
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=10000)).start()
    bot.run(DISCORD_TOKEN)
