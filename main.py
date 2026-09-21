import os
import sys
import json
import re
import random
import requests
import urllib.parse
from moviepy.editor import (
    ImageClip, 
    AudioFileClip, 
    CompositeAudioClip
)

from google import genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Environment Secrets
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")

def clean_url(url):
    """Strips accidental list brackets, quotes, and whitespace from URL strings."""
    if isinstance(url, list):
        url = url[0] if url else ""
    return str(url).strip("[]'\" ")

def generate_anime_concept():
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = """
    Create metadata and an image prompt for a viral Anime / Cyberpunk YouTube Short.
    
    Return strictly JSON format with keys:
    - "title": Catchy title with trending hashtags (e.g. #Anime #Cyberpunk #Phonk #Shorts)
    - "description": Short engaging summary with hashtags
    - "image_prompt": Detailed English description for an AI anime art generator (e.g. 'futuristic samurai warrior in neon Tokyo rain, glowing eyes, cyberpunk aesthetic, masterpiece, highly detailed, 8k resolution, cinematic lighting')
    """

    print("Generating anime concept using gemini-3.6-flash...")
    res = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )
    
    text = res.text.strip()
    if text.startswith("```json"): text = text[7:]
    if text.startswith("```"): text = text[3:]
    if text.endswith("```"): text = text[:-3]
    
    data = json.loads(text.strip())
    return str(data["title"]), str(data["description"]), str(data["image_prompt"])

def download_ai_anime_image(prompt, output_file="anime_art.jpg"):
    print(f"Generating 9:16 AI Anime art for prompt: '{prompt}'...")
    
    encoded_prompt = urllib.parse.quote(f"{prompt}, vertical portrait aspect ratio 9:16, masterpiece, highly detailed anime art style")
    image_url = f"[https://image.pollinations.ai/prompt/](https://image.pollinations.ai/prompt/){encoded_prompt}?width=1080&height=1920&nologo=true"
    
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
    
    selected_url = clean_url(random.choice(phonk_urls))
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

    # Apply dynamic slow-zoom effect
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
    
