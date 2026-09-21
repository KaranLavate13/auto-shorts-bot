import os
import sys
import json
import random
import time
import requests
import urllib.parse
from moviepy.editor import (
    ImageClip, 
    AudioFileClip, 
    CompositeAudioClip
)

from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Environment Secrets
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")

def sanitize_to_str(val):
    """Recursively unwraps lists and strips all stray brackets, quotes, and whitespace."""
    while isinstance(val, (list, tuple)):
        val = val[0] if len(val) > 0 else ""
    s = str(val).strip()
    return s.strip("[]'\" \t\n\r")

def generate_anime_concept():
    # Configure retry options to gracefully handle 503 Server Errors
    retry_config = types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=5,
            initial_delay=2.0,
            max_delay=30.0,
            http_status_codes=[408, 429, 500, 502, 503, 504]
        ),
        timeout=60000
    )
    
    client = genai.Client(api_key=GEMINI_API_KEY, http_options=retry_config)
    
    prompt = """
    Create metadata and an image prompt for a viral Anime / Cyberpunk YouTube Short.
    
    Return strictly valid JSON format with keys:
    - "title": Catchy title with trending hashtags (e.g. #Anime #Cyberpunk #Phonk #Shorts)
    - "description": Short engaging summary with hashtags
    - "image_prompt": Detailed English description for an AI anime art generator (e.g. 'futuristic samurai warrior in neon Tokyo rain, glowing eyes, cyberpunk aesthetic, masterpiece, highly detailed, 8k resolution, cinematic lighting')
    """

    models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash"]
    res = None

    for model_name in models_to_try:
        try:
            print(f"Generating anime concept using {model_name}...")
            res = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if res and res.text:
                break
        except Exception as e:
            print(f"Warning: {model_name} failed with error: {e}. Trying fallback model...")
            time.sleep(3)

    if not res or not res.text:
        raise RuntimeError("Failed to generate content from Gemini API across all attempted models.")

    text = res.text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    
    data = json.loads(text.strip())
    
    title = sanitize_to_str(data.get("title", "Anime Short"))
    description = sanitize_to_str(data.get("description", "#Anime #Shorts"))
    image_prompt = sanitize_to_str(data.get("image_prompt", "cyberpunk anime samurai"))
    
    return title, description, image_prompt

def download_ai_anime_image(prompt, output_file="anime_art.jpg"):
    clean_p = sanitize_to_str(prompt)
    print(f"Generating 9:16 AI Anime art for prompt: '{clean_p}'...")
    
    full_prompt = f"{clean_p}, vertical portrait aspect ratio 9:16, masterpiece, highly detailed anime art style"
    encoded_prompt = urllib.parse.quote(full_prompt)
    
    image_url = f"[https://image.pollinations.ai/prompt/](https://image.pollinations.ai/prompt/){encoded_prompt}?width=1080&height=1920&nologo=true"
    image_url = sanitize_to_str(image_url)
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    resp = requests.get(image_url, headers=headers, timeout=60)
    
    if resp.status_code == 200:
        with open(output_file, "wb") as f:
            f.write(resp.content)
        print("9:16 AI image downloaded successfully.")
    else:
        raise RuntimeError(f"Failed to generate AI image. HTTP Status: {resp.status_code}")

def download_phonk_bgm(output_file="phonk_bgm.mp3"):
    print("Downloading royalty-free Phonk track...")
    phonk_urls = [
        "[https://cdn.pixabay.com/download/audio/2023/04/12/audio_13b0c51cf9.mp3](https://cdn.pixabay.com/download/audio/2023/04/12/audio_13b0c51cf9.mp3)",
        "[https://cdn.pixabay.com/download/audio/2022/11/06/audio_c1e2e13a44.mp3](https://cdn.pixabay.com/download/audio/2022/11/06/audio_c1e2e13a44.mp3)",
        "[https://cdn.pixabay.com/download/audio/2023/02/28/audio_b2d2db7e1d.mp3](https://cdn.pixabay.com/download/audio/2023/02/28/audio_b2d2db7e1d.mp3)"
    ]
    
    raw_choice = random.choice(phonk_urls)
    selected_url = sanitize_to_str(raw_choice)
    headers = {"User-Agent": "Mozilla/5.0"}
    
    resp = requests.get(selected_url, headers=headers, timeout=30)
    if resp.status_code == 200:
        with open(output_file, "wb") as f:
            f.write(resp.content)
        print("Phonk BGM downloaded successfully.")
    else:
        raise RuntimeError(f"Failed to download BGM, status code: {resp.status_code}")

def create_animated_short(image_file="anime_art.jpg", bgm_file="phonk_bgm.mp3", output_file="final_short.mp4", duration=15):
    print("Converting 9:16 image to motion video with dynamic zoom...")
    
    bgm = AudioFileClip(bgm_file).subclip(0, duration)
    clip = ImageClip(image_file).set_duration(duration)

    animated_clip = clip.resize(lambda t: 1 + 0.03 * t)
    animated_clip = animated_clip.set_position(('center', 'center'))

    final_video = animated_clip.set_audio(bgm)
    final_video.write_videofile(
        output_file, 
        codec="libx264", 
        audio_codec="aac", 
        fps=30,
        logger=None
    )
    print("Video rendered successfully.")

def upload_to_youtube(video_file="final_short.mp4", title="Anime Short", description=""):
    print("Authenticating with YouTube API...")
    creds = Credentials(
        token=None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        token_uri="[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)",
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET
    )

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:95],
            "description": description,
            "tags": ["AnimeEdits", "Phonk", "Cyberpunk", "AIArt", "Shorts"],
            "categoryId": "1"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(video_file, chunksize=-1, resumable=True)

    print("Uploading video to YouTube...")
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    response = request.execute()
    print(f"Upload Complete! Video ID: {response.get('id')}")

def main():
    print("--- STARTING 100% FREE 9:16 AI ANIME PIPELINE ---")
    
    title, description, image_prompt = generate_anime_concept()
    print(f"Title: {title}")
    print(f"AI Prompt: {image_prompt}\n")

    download_ai_anime_image(image_prompt)
    download_phonk_bgm()
    create_animated_short()
    upload_to_youtube(title=title, description=description)

    print("--- PIPELINE FINISHED SUCCESSFULLY ---")

if __name__ == "__main__":
    main()
    
