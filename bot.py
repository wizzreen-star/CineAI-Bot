import os
import discord
from discord.ext import commands
import google.generativeai as genai

# --- Load environment variables ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Configure Gemini ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro")

# --- Discord Bot setup ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def hello(ctx):
    await ctx.send("👋 Hello! I’m CineAI — now powered by Gemini AI!")

@bot.command()
async def video(ctx, *, prompt: str):
    """Generate AI video script or idea with Gemini"""
    await ctx.send(f"🎬 Creating concept for: **{prompt}** ... please wait ⏳")

    try:
        response = model.generate_content(
            f"Create a detailed video scene description for: {prompt}. "
            f"Include camera angles, transitions, and visuals."
        )
        result = response.text
        await ctx.send(f"🎞️ **Gemini video concept:**\n{result[:1900]}")  # limit to Discord message size
    except Exception as e:
        await ctx.send(f"⚠️ Gemini API error: {e}")

# --- Run bot ---
if not DISCORD_TOKEN:
    print("❌ ERROR: DISCORD_TOKEN missing.")
else:
    bot.run(DISCORD_TOKEN)
