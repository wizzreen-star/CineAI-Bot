import os
import discord
import google.generativeai as genai
from discord.ext import commands
from threading import Thread
from flask import Flask

# === Environment Variables ===
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# === Gemini Setup ===
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None
    print("❌ GEMINI_API_KEY not found in environment variables!")

# === Discord Bot Setup ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def hello(ctx):
    await ctx.send("👋 Hello! I’m CineAI — powered by Google Gemini!")

@bot.command()
async def video(ctx, *, prompt: str):
    """Generate an AI video idea or concept using Gemini"""
    if not model:
        await ctx.send("⚠️ Gemini API key missing — please set GEMINI_API_KEY in Render.")
        return

    await ctx.send(f"🎬 Thinking about: **{prompt}** ... please wait ⏳")

    try:
        response = model.generate_content(f"Create a detailed video concept for: {prompt}")
        idea = response.text or "No response from Gemini."
        await ctx.send(f"✨ **Gemini’s Idea:**\n{idea[:1800]}")
    except Exception as e:
        await ctx.send(f"❌ Gemini error: {e}")

# === Flask Web Server (for Render port binding) ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ CineAI (Gemini Bot) is running successfully!"

def run_web():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_web).start()

# === Run Discord Bot ===
if not DISCORD_TOKEN:
    print("❌ ERROR: DISCORD_TOKEN not found in environment variables.")
else:
    bot.run(DISCORD_TOKEN)
