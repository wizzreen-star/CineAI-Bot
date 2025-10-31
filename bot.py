import os, json, discord
from discord.ext import commands
import google.generativeai as genai
from moviepy.editor import TextClip, CompositeVideoClip, ColorClip
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Gemini setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# YouTube setup
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_youtube_service():
    creds_json = json.loads(os.getenv("YOUTUBE_SERVICE_ACCOUNT"))
    creds = service_account.Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    return build("youtube", "v3", credentials=creds)

# Create simple text video
def create_video(text, filename="/tmp/video.mp4"):
    clip = TextClip(text, fontsize=60, color="white", size=(1280,720), method="caption").set_duration(10)
    bg = ColorClip(size=(1280,720), color=(0,0,0)).set_duration(10)
    final = CompositeVideoClip([bg, clip.set_position("center")])
    final.write_videofile(filename, fps=24, codec="libx264", audio=False)
    return filename

# Discord command
@bot.command()
async def upload(ctx, *, prompt: str):
    await ctx.send(f"🎬 Creating a YouTube video for: **{prompt}** ...")

    try:
        # Gemini idea
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Write a 1-sentence viral video script about: {prompt}")
        script = response.text.strip()

        await ctx.send(f"💡 Gemini idea:\n> {script}")

        # Make video
        video_path = create_video(script)

        # Upload to YouTube
        youtube = get_youtube_service()
        request_body = {
            "snippet": {
                "categoryId": "22",
                "title": prompt.title(),
                "description": script,
                "tags": ["AI", "Gemini", "AutoUpload"]
            },
            "status": {"privacyStatus": "unlisted"}
        }

        media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
        upload = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
        response = upload.execute()

        youtube_link = f"https://youtu.be/{response['id']}"
        await ctx.send(f"✅ Uploaded!\n{youtube_link}")

    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))
from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
