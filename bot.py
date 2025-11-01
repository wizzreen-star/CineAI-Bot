import os
import discord
import asyncio
import google.generativeai as genai
from discord.ext import commands
from dotenv import load_dotenv
from video_maker import make_video

# Load environment variables
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN or not GEMINI_API_KEY:
    raise ValueError("❌ Missing DISCORD_TOKEN or GEMINI_API_KEY in .env file!")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command(name="video")
async def generate_video(ctx, *, topic: str):
    """Generates an AI video from a topic using Gemini + MoviePy."""
    await ctx.reply(f"🎬 Generating a video for: **{topic}** — please wait...")

    try:
        # Step 1: Generate script
        await ctx.send("✍️ Writing script...")
        prompt = f"Write a short, engaging 5-sentence script about: {topic}"
        response = model.generate_content(prompt)
        script = response.text.strip()

        # Step 2: Generate video
        await ctx.send("🎥 Building the video...")
        video_path = make_video(script, topic)

        # Step 3: Send result
        if os.path.exists(video_path):
            await ctx.send("✅ Done! Here's your video:", file=discord.File(video_path))
        else:
            await ctx.send("❌ Failed to create video file.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
def run_discord():
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not set.")
        return
    bot.run(DISCORD_TOKEN)


# -------------------
# Start Everything
# -------------------
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    run_discord()
    lines = textwrap.wrap(text, width=40)
    line_heights = [font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines]
    total_h = sum(line_heights) + 10 * len(lines)
    y = (H - total_h) // 2

    for line, h in zip(lines, line_heights):
        w = font.getlength(line)
        draw.text(((W - w) / 2, y), line, font=font, fill=(240, 240, 240))
        y += h + 10

    # Save to a temporary PNG
    temp_path = VIDEO_DIR / f"{uuid.uuid4().hex[:6]}.png"
    img.save(temp_path)
    return temp_path


# -------------------
# Video Builder
# -------------------
async def build_video(prompt: str, script: str, lang="en") -> Path:
    """Generate narrated video."""
    uid = uuid.uuid4().hex[:8]
    audio_path = VIDEO_DIR / f"{uid}.mp3"
    video_path = VIDEO_DIR / f"{uid}.mp4"

    # Step 1: Text → Speech
    def make_tts():
        tts = gTTS(script, lang=lang)
        tts.save(str(audio_path))
    await asyncio.to_thread(make_tts)

    # Step 2: Load audio
    audio_clip = mp.AudioFileClip(str(audio_path))
    duration = audio_clip.duration

    # Step 3: Create slides
    slides = split_text_into_segments(script)
    per_slide = duration / max(len(slides), 1)
    clips = []

    for s in slides:
        img_path = create_image(s)
        clip = mp.ImageClip(str(img_path)).set_duration(per_slide)
        clips.append(clip)

    # Step 4: Combine
    final_clip = mp.concatenate_videoclips(clips, method="compose")
    final_clip = final_clip.set_audio(audio_clip).set_fps(24)

    # Step 5: Save
    def write_file():
        final_clip.write_videofile(str(video_path), codec="libx264", audio_codec="aac", verbose=False, logger=None)
    await asyncio.to_thread(write_file)

    # Cleanup
    audio_clip.close()
    for clip in clips:
        try:
            os.remove(clip.filename)
        except Exception:
            pass

    return video_path


# -------------------
# Discord Commands
# -------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} — ready to make videos!")

@bot.command(name="hello")
async def hello(ctx):
    await ctx.send("👋 Hey! I’m CineAI — I can turn your ideas into short videos!")

@bot.command(name="video")
async def make_video(ctx, *, prompt: str):
    await ctx.send(f"🎬 Generating a video for: **{prompt}** — please wait...")
    await ctx.send("✍️ Writing script...")

    try:
        script = await asyncio.to_thread(generate_script, prompt)
        await ctx.send("🎙️ Generating voice narration...")
        video_path = await build_video(prompt, script)
        await ctx.send("📤 Uploading your video...")

        size_mb = video_path.stat().st_size / (1024 * 1024)
        if size_mb < 24:
            await ctx.send(file=discord.File(str(video_path)))
        else:
            await ctx.send(f"✅ Video created ({size_mb:.1f} MB). Saved at `{video_path}`.")
    except Exception as e:
        await ctx.send(f"❌ Failed to build video: {e}")


# -------------------
# Flask (for Render)
# -------------------
app = Flask("cineai")

@app.route("/")
def index():
    return Response("✅ CineAI bot running!", mimetype="text/plain")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def run_discord():
    bot.run(DISCORD_TOKEN)

# -------------------
# Start
# -------------------
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    run_discord()
