import os
import discord
from discord.ext import commands
from flask import Flask
import google.generativeai as genai

# ==============================
# 🔧 Load Environment Variables
# ==============================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY not found in environment variables!")
else:
    print("✅ GEMINI_API_KEY loaded successfully.")

if not DISCORD_TOKEN:
    print("❌ DISCORD_TOKEN not found in environment variables!")
else:
    print("✅ DISCORD_TOKEN loaded successfully.")

# ==============================
# 🚀 Configure Gemini
# ==============================
genai.configure(api_key=GEMINI_API_KEY)

# ==============================
# 🤖 Setup Discord Bot
# ==============================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------------
# Gemini Text Command
# ------------------------------
@bot.command()
async def ask(ctx, *, prompt: str):
    """Ask Gemini AI something"""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        await ctx.send(response.text[:1900])  # Discord limit
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

# ------------------------------
# Bot Ready Event
# ------------------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print("Bot is online and ready to use!")

# ==============================
# 🌐 Flask App (for Render port binding)
# ==============================
app = Flask(__name__)

@app.route('/')
def home():
    return "CineAI Bot is running!"

# ==============================
# 🏁 Main Entrypoint
# ==============================
if __name__ == "__main__":
    import threading

    # Run Discord bot in a separate thread
    def run_discord():
        bot.run(DISCORD_TOKEN)

    threading.Thread(target=run_discord).start()

    # Run Flask app
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
