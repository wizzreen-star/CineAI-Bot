import os
import discord
from discord.ext import commands
import google.generativeai as genai
from flask import Flask
import threading
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ===============================
# 🔧 Load Environment Variables
# ===============================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")  # (optional future use)

if GEMINI_API_KEY:
    print("✅ GEMINI_API_KEY loaded successfully.")
else:
    print("❌ GEMINI_API_KEY not found in environment variables!")

if DISCORD_TOKEN:
    print("✅ DISCORD_TOKEN loaded successfully.")
else:
    print("❌ DISCORD_TOKEN not found in environment variables!")

# ===============================
# 🤖 Setup Discord Bot
# ===============================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===============================
# 💬 Gemini Text Generator
# ===============================
genai.configure(api_key=GEMINI_API_KEY)

@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")

@bot.command()
async def idea(ctx, *, prompt: str):
    """Generate a video idea using Gemini"""
    await ctx.send(f"💡 Thinking of an idea for: **{prompt}** ...")

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        idea_text = response.text.strip()

        await ctx.send(f"🎬 **CineAI Idea:**\n{idea_text}")

        # Optionally save for auto YouTube upload
        with open("video_idea.txt", "w") as f:
            f.write(idea_text)

    except Exception as e:
        await ctx.send(f"⚠️ Gemini Error: {e}")

# ===============================
# 📤 Auto Upload to YouTube (optional)
# ===============================
def upload_to_youtube(title, description, file_path):
    try:
        # This needs OAuth setup; for now placeholder logic
        youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": ["CineAI", "AI Video", "Gemini Bot"],
                    "categoryId": "22"
                },
                "status": {"privacyStatus": "public"},
            },
            media_body=MediaFileUpload(file_path)
        )
        response = request.execute()
        print(f"✅ Uploaded video: {response['id']}")
    except Exception as e:
        print(f"❌ YouTube upload failed: {e}")

# ===============================
# 🌐 Flask Server (for Render)
# ===============================
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 CineAI Bot is running perfectly on Render!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Run Flask in background
threading.Thread(target=run_flask).start()

# ===============================
# ▶️ Start Discord Bot
# ===============================
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("❌ DISCORD_TOKEN missing — bot not started.")
