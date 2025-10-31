import os
import threading
import discord
from discord.ext import commands
from flask import Flask
import google.generativeai as genai

# ==============================
# 🔧 Load environment variables
# ==============================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN:
    print("❌ DISCORD_TOKEN not found in environment variables!")
if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY not found in environment variables!")
else:
    print("✅ GEMINI_API_KEY loaded successfully.")

# ==============================
# 🌐 Flask Web Server (for Render)
# ==============================
app = Flask(__name__)

@app.route("/")
def home():
    return "🎬 CineAI Bot is running successfully on Render!"

# ==============================
# 🤖 Discord Bot Setup
# ==============================
intents = discord.Intents.default()
intents.message_content = True  # ✅ Required for message reading

bot = commands.Bot(command_prefix="!", intents=intents)

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# ==============================
# 🎮 Commands
# ==============================

@bot.command()
async def ping(ctx):
    """Simple test command"""
    await ctx.send("🏓 Pong! I’m alive and ready!")

@bot.command()
async def idea(ctx, *, topic: str):
    """Generate a YouTube video idea using Gemini"""
    await ctx.send(f"💡 Thinking of an idea for: **{topic}** ...")

    try:
        response = model.generate_content(f"Give me a creative YouTube video idea about {topic}.")
        await ctx.send(f"🎥 Here's an idea:\n\n**{response.text}**")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
async def script(ctx, *, prompt: str):
    """Generate a video script with Gemini"""
    await ctx.send(f"✍️ Writing your script for: **{prompt}** ...")

    try:
        response = model.generate_content(f"Write a short YouTube video script about: {prompt}.")
        await ctx.send(f"🎬 **Script:**\n\n{response.text}")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

# ==============================
# 🚀 Run Flask + Discord
# ==============================
def run_flask():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    bot.run(DISCORD_TOKEN)
