import os
import json
import discord
from discord.ext import commands
import google.generativeai as genai
from moviepy.editor import TextClip, CompositeVideoClip, ColorClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

# --- Discord setup ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Gemini setup ---
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# --- YouTube Auth ---
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_youtube_service():
    creds_json = os.getenv("YOUTUBE_CLIENT_SECRET_JSON")
    creds_file = "/tmp/client_secret.json"
    with open(creds_file, "w") as f:
        f.write(creds_json)
    flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
    creds = flow.run_local_server(port=8080)
    return build("youtube", "v3", credentials=creds)

# --- Create simple video ---
def create_video(text, filename="/tmp/video.mp4"):
    clip = TextClip(
        text, fontsize=60, color="white", size=(1280, 720), method="caption"
    ).set_duration(10)

    bg = ColorClip(size=(1280, 720), color=(0, 0, 0)).set_duration(10)
    final = CompositeVideoClip([bg, clip.set_position("center")])
    final.write_videofile(filename, fps=24, codec="libx264", audio=False)
    return filename

# --- Discord command ---
@bot.command()
async def upload(ctx, *, prompt: str):
    await ctx.send(f"🎬 Creating a YouTube video for: **{prompt}** ...")

    try:
        # 1️⃣ Gemini generates short video idea
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Write a short viral video script (1 sentence) about: {prompt}")
        script = response.text.strip()

        await ctx.send(f"💡 Gemini idea:\n> {script}")

        # 2️⃣ Create short text-based video
        await ctx.send("🎥 Generating video...")
        video_path = create_video(script)

        # 3️⃣ Upload to YouTube
        await ctx.send("📤 Uploading to YouTube...")
        youtube = get_youtube_service()
        request_body = {
            "snippet": {
                "categoryId": "22",
                "title": prompt.title(),
                "description": script,
                "tags": ["AI", "Gemini", "Auto Upload"]
            },
            "status": {"privacyStatus": "unlisted"}
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/*")
        upload_request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
        response = upload_request.execute()

        video_id = response.get("id")
        youtube_link = f"https://youtu.be/{video_id}"
        await ctx.send(f"✅ Uploaded to YouTube!\n{youtube_link}")

    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))
