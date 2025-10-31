import os
import discord
from discord.ext import commands
import google.generativeai as genai
from flask import Flask

# --- Load Environment Variables ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY not found in environment variables!")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def hello(ctx):
    await ctx.send("👋 Hello! I’m CineAI — your movie assistant bot!")

@bot.command()
async def video(ctx, *, prompt: str):
    """Generate a creative video idea (text only for now) using Gemini"""
    if not GEMINI_API_KEY:
        await ctx.send("⚠️ Gemini API key missing — please set GEMINI_API_KEY in Render.")
        return

    await ctx.send(f"🎬 Thinking of a cool AI video idea for: **{prompt}** ... ⏳")

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Write a short creative video script for: {prompt}")
        await ctx.send(f"🎥 **AI Video Idea:**\n{response.text}")
    except Exception as e:
        await ctx.send(f"❌ Gemini API error: {e}")

# --- Flask App (for Render port binding) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 CineAI Discord Bot is running!"

# --- Run both Flask & Discord ---
if __name__ == "__main__":
    import threading

    def run_discord():
        if DISCORD_TOKEN:
            bot.run(DISCORD_TOKEN)
        else:
            print("❌ DISCORD_TOKEN not found in environment variables!")

    threading.Thread(target=run_discord).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
