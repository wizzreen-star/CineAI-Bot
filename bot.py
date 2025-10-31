import os
import discord
from discord.ext import commands
from flask import Flask
import google.generativeai as genai
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from moviepy.editor import TextClip, concatenate_videoclips, ColorClip

# ------------------ ENVIRONMENT ------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not GEMINI_API_KEY:
    raise Exception("❌ GEMINI_API_KEY not found!")
if not DISCORD_TOKEN:
    raise Exception("❌ DISCORD_TOKEN not found!")

genai.configure(api_key=GEMINI_API_KEY)

# ------------------ DISCORD ------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------ FLASK KEEPALIVE ------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ CineAI Bot is running!"

# ------------------ YOUTUBE UPLOAD ------------------
def upload_to_youtube(video_path, title, description):
    creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/youtube.upload"])
    youtube = build("youtube", "v3", credentials=creds)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": description},
            "status": {"privacyStatus": "public"}
        },
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )
    response = request.execute()
    return f"https://www.youtube.com/watch?v={response['id']}"

# ------------------ GEMINI VIDEO MAKER ------------------
def make_video_from_text(prompt):
    print(f"🎬 Generating idea for: {prompt}")
    model = genai.GenerativeModel("gemini-1.5-flash")
    idea = model.generate_content(f"Write a short creative video idea for: {prompt}")
    script = idea.text

    print("🎥 Creating simple text video...")
    clips = []
    lines = script.split(". ")
    for line in lines:
        txt = TextClip(line, fontsize=60, color='white', size=(1080, 1920), bg_color='black', duration=2)
        clips.append(txt)
    final = concatenate_videoclips(clips)
    final.write_videofile("output.mp4", fps=24)
    return "output.mp4", script

# ------------------ DISCORD COMMAND ------------------
@bot.command()
async def video(ctx, *, prompt: str):
    await ctx.reply(f"💡 Thinking of an idea for: **{prompt}** ...")
    try:
        video_path, script = make_video_from_text(prompt)
        await ctx.reply("🎬 Video generated! Uploading to YouTube...")
        youtube_url = upload_to_youtube(video_path, title=prompt, description=script)
        await ctx.reply(f"✅ Uploaded to YouTube!\n{youtube_url}")
    except Exception as e:
        await ctx.reply(f"❌ Error: {str(e)}")

# ------------------ START EVERYTHING ------------------
if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))).start()
    bot.run(DISCORD_TOKEN)
