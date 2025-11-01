# video_maker.py
import os
import uuid
import asyncio
import tempfile
import textwrap
from io import BytesIO
from pathlib import Path
from typing import Optional, Callable

from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp
from gtts import gTTS
import requests
import time

# Try import google gen ai SDK (two common names)
GENAI = None
try:
    # new style
    import google.genai as genai_client
    GENAI = genai_client
except Exception:
    try:
        import google.generativeai as genai_client
        GENAI = genai_client
    except Exception:
        GENAI = None

VIDEO_DIR = Path("videos")
VIDEO_DIR.mkdir(exist_ok=True)

class VideoMaker:
    def __init__(self, gemini_api_key: Optional[str] = None):
        self.gemini_api_key = gemini_api_key
        self.have_gemini = bool(gemini_api_key and GENAI is not None)
        if self.have_gemini:
            # configure client for both lib variants
            try:
                # google.genai style
                if hasattr(GENAI, "Client"):
                    self.client = GENAI.Client(api_key=gemini_api_key)
                else:
                    # google.generativeai style
                    GENAI.configure(api_key=gemini_api_key)
                    self.client = GENAI
            except Exception as e:
                print("⚠️ Failed to init Gemini client:", e)
                self.have_gemini = False
                self.client = None
        else:
            self.client = None

    # ---------------------
    # Step A: Generate script text via Gemini (or fallback)
    # ---------------------
    def _generate_script(self, prompt: str) -> str:
        if self.have_gemini:
            try:
                # Try common modern client patterns
                # google.genai.Client().models.generate_content(...) style:
                if hasattr(self.client, "models") and hasattr(self.client.models, "generate_content"):
                    resp = self.client.models.generate_content(model="gemini-2.5-pro", content=f"Write a short 60-90s video narration and 4 scene descriptions for: {prompt}")
                    text = getattr(resp, "text", None) or resp.output_text if hasattr(resp,'output_text') else None
                    if not text and isinstance(resp, dict):
                        text = resp.get("content") or resp.get("output") or ""
                    if text:
                        return text.strip()
                # google.generativeai.generate_text style
                if hasattr(self.client, "generate_text"):
                    resp = self.client.generate_text(model="gemini-2.5-pro", prompt=f"Write a short 60-90s video narration and 4 scene descriptions for: {prompt}")
                    if isinstance(resp, dict):
                        return resp.get("result", "") or resp.get("text","")
                    if hasattr(resp, "text"):
                        return resp.text
            except Exception as e:
                print("⚠️ Gemini script generation failed:", e)

        # fallback simple script
        return (
            f"Title: {prompt}\n\n"
            "Scene 1: Quick intro - open with a short hook introducing the topic.\n"
            "Scene 2: Main idea - explain the core concept in clear sentences.\n"
            "Scene 3: Visual example - show a relatable example.\n"
            "Scene 4: Closing - 1-line call to action.\n"
        )

    # ---------------------
    # Step B: Generate images (Gemini Imagen preferred, else Unsplash fallback)
    # Returns path to saved image file
    # ---------------------
    def _generate_image(self, scene_prompt: str) -> str:
        # Use Gemini image generation if available
        if self.have_gemini:
            try:
                # Try a few possible client APIs
                # 1) google.genai.Client().images.generate(...)
                if hasattr(self.client, "images") and hasattr(self.client.images, "generate"):
                    # modern genai client
                    img_resp = self.client.images.generate(model="imagen-3-bison", prompt=scene_prompt)
                    # The response might contain binary or base64 urls; try to extract bytes
                    if hasattr(img_resp, "image") and isinstance(img_resp.image, (bytes, bytearray)):
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                        tmp.write(img_resp.image)
                        tmp.close()
                        return tmp.name
                    if isinstance(img_resp, dict) and img_resp.get("images"):
                        # base64 content
                        b64 = img_resp["images"][0].get("b64_json") or img_resp["images"][0].get("base64")
                        if b64:
                            import base64
                            data = base64.b64decode(b64)
                            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                            tmp.write(data); tmp.close()
                            return tmp.name
                # 2) google.generativeai.images.create(...)
                if hasattr(self.client, "images") and hasattr(self.client.images, "create"):
                    resp = self.client.images.create(model="imagen-3-bison", prompt=scene_prompt, size="1280x720")
                    # resp may contain a data list with b64
                    if isinstance(resp, dict) and resp.get("data"):
                        b64 = resp["data"][0].get("b64_json") or resp["data"][0].get("base64")
                        if b64:
                            import base64, tempfile
                            data = base64.b64decode(b64)
                            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                            tmp.write(data); tmp.close()
                            return tmp.name
            except Exception as e:
                print("⚠️ Gemini image generation failed; falling back:", e)

        # Unsplash fallback (quick and free but static)
        try:
            query = requests.utils.requote_uri(scene_prompt)
            url = f"https://source.unsplash.com/1280x720/?{query}"
            r = requests.get(url, timeout=20)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.write(r.content); tmp.close()
            return tmp.name
        except Exception as e:
            print("⚠️ Unsplash fallback failed:", e)
            # final fallback: black image
            img = Image.new("RGB", (1280,720), (10,10,10))
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            img.save(tmp.name)
            return tmp.name

    # ---------------------
    # Step C: Generate TTS audio (Gemini TTS preferred else gTTS)
    # ---------------------
    def _generate_tts(self, text: str) -> str:
        if self.have_gemini:
            try:
                # try common API shapes
                if hasattr(self.client, "audio") and hasattr(self.client.audio, "synthesize"):
                    # hypothetical modern method
                    resp = self.client.audio.synthesize(model="gemini-tts-1", text=text, voice="alloy", format="mp3")
                    if isinstance(resp, bytes):
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                        tmp.write(resp); tmp.close()
                        return tmp.name
                    if isinstance(resp, dict) and resp.get("audio"):
                        import base64
                        data = base64.b64decode(resp["audio"])
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                        tmp.write(data); tmp.close()
                        return tmp.name
                # alternative older style
                if hasattr(self.client, "text_to_speech") or hasattr(self.client, "tts"):
                    # best-effort; many SDK shapes exist
                    try:
                        out = self.client.text_to_speech.synthesize(text=text)  # may throw
                        if isinstance(out, bytes):
                            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                            tmp.write(out); tmp.close()
                            return tmp.name
                    except Exception:
                        pass
            except Exception as e:
                print("⚠️ Gemini TTS failed; falling back to gTTS:", e)

        # gTTS fallback
        try:
            tts = gTTS(text, lang="en", slow=False)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(tmp.name)
            return tmp.name
        except Exception as e:
            print("❌ gTTS also failed:", e)
            raise

    # ---------------------
    # Build final video by:
    # - generating script -> splitting into short segments
    # - generating image for each segment (with slight pan/zoom)
    # - generating audio for the whole script (or per segment)
    # - stitching with moviepy
    # notify_func optionally sends status updates (a coroutine or callable)
    # ---------------------
    async def make_video_for_prompt(self, prompt: str, notify_func: Optional[Callable] = None) -> str:
        """
        Returns local filepath of generated video (mp4).
        notify_func: function that accepts a string (status message).
        """
        def notify(msg):
            if notify_func:
                try:
                    # if notify_func is coroutine-sending ctx.send, schedule it
                    if asyncio.iscoroutinefunction(notify_func):
                        asyncio.create_task(notify_func(msg))
                    else:
                        # if notify_func returns coroutine, run it
                        res = notify_func(msg)
                        if asyncio.iscoroutine(res):
                            asyncio.create_task(res)
                except Exception:
                    pass

        notify("✍️ Creating script...")
        # 1) generate script
        script = await asyncio.to_thread(self._generate_script, prompt)

        notify("🖼️ Generating scene images...")
        # split into sentences/short segments
        segments = [s.strip() for s in textwrap.wrap(script, width=140)]
        if len(segments) < 3:
            # try splitting on lines
            segments = [s.strip() for s in script.split("\n") if s.strip()]

        if not segments:
            segments = [prompt]

        # 2) generate images (one per segment)
        images = []
        for i, seg in enumerate(segments[:10]):  # limit to 10 segments for speed
            notify(f"🖼️ Scene {i+1}/{len(segments)}: generating image...")
            # craft a prompt for image generation (more cinematic)
            scene_prompt = f"{prompt} — cinematic, dramatic, realistic photograph, wide shot. {seg}"
            img_path = await asyncio.to_thread(self._generate_image, scene_prompt)
            images.append((img_path, seg))

        # 3) generate narration audio — create one full narration to keep lip-sync simple
        notify("🎙️ Generating narration audio...")
        full_narration = script
        audio_path = await asyncio.to_thread(self._generate_tts, full_narration)

        # 4) assemble video — create slight Ken Burns effect for each image
        notify("🎬 Assembling final video (this may take a while)...")
        audio_clip = mp.AudioFileClip(audio_path)
        audio_dur = audio_clip.duration or max(3, len(segments)*3)

        # set durations proportional to segment count
        per_segment = audio_dur / max(1, len(images))

        clips = []
        for (img_path, seg) in images:
            # create image clip
            try:
                clip = mp.ImageClip(img_path).set_duration(per_segment)
            except Exception:
                # fallback blank
                from PIL import Image
                tmpimg = Image.new("RGB", (1280,720), (10,10,10))
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                tmpimg.save(tmp.name)
                clip = mp.ImageClip(tmp.name).set_duration(per_segment)

            # add subtle zoom (Ken Burns)
            clip = clip.resize(width=1280)
            clip = clip.fx(mp.vfx.zoom_in, 1.03) if hasattr(mp, "vfx") else clip

            # overlay the segment text as subtitle
            subtitle = mp.TextClip(seg, fontsize=40, color='white', size=(clip.w - 80, None), method='caption')
            subtitle = subtitle.set_position(("center","bottom")).set_duration(per_segment)
            scene = mp.CompositeVideoClip([clip, subtitle.set_opacity(0.9)])
            clips.append(scene)

        final = mp.concatenate_videoclips(clips, method="compose").set_audio(audio_clip)
        final = final.set_fps(24)

        uid = uuid.uuid4().hex[:8]
        out_path = str(VIDEO_DIR / f"{uid}.mp4")

        def write_final():
            # verbose moviepy may be noisy; keep it quiet
            final.write_videofile(out_path, codec="libx264", audio_codec="aac", threads=2, verbose=False, logger=None)

        await asyncio.to_thread(write_final)

        notify("✅ Video ready!")
        # cleanup temp audio if desired (not deleting to keep for debug)
        return out_path
