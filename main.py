import os
import sys
import json
import re
import random
import asyncio
import requests
import urllib.parse
import edge_tts
from moviepy.editor import (
    VideoFileClip, 
    AudioFileClip, 
    CompositeAudioClip, 
    concatenate_videoclips, 
    concatenate_audioclips
)

from google import genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Environment Secrets
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")

def generate_content():
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    topics = [
        "Lord Krishna's Life Lessons and Mahabharat Wisdom", 
        "The Loyalty and Sacrifice of Karna in Mahabharat", 
        "Bheeshma Pitamah's Vow and Duty", 
        "The Bravery of Abhimanyu in the Chakravyuha", 
        "Yudhishthira's Powerful Lessons on Dharma",
        "Draupadi's Courage and Divine Faith",
        "The Laws of Karma from the Mahabharat Epic"
    ]
    chosen_topic = random.choice(topics)
    
    prompt = f"""
    Create a 30-to-40 second viral YouTube Short about '{chosen_topic}'.
    Narrate a short story, quote, or life lesson from the Mahabharat.
    
    Return strictly valid JSON format with keys:
    - "title": catchy title in Hindi/Hinglish with hashtags (e.g. #Mahabharat #Krishna #Spiritual #Shorts)
    - "description": summary in Hindi with relevant hashtags
    - "search_term": single 1-word ENGLISH string for Pexels background video matching the scene (e.g. warrior, temple, chariot, sunset, fire)
    - "script": captivating storytelling voiceover text written STRICTLY IN DEVANAGARI HINDI (हिंदी script) (approx 50-65 words). Ensure natural Hindi grammar.
    
    Do not add markdown formatting or extra text outside JSON.
    """

    print("Generating script using gemini-3.6-flash...")
    try:
        res = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
    except Exception as e:
        raise RuntimeError(f"gemini-3.6-flash model failed: {e}")

    if not res or not res.text:
        raise RuntimeError("gemini-3.6-flash returned an empty response.")

    response_text = res.text.strip()

    # Clean JSON response if wrapped in markdown fences
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    
    data = json.loads(response_text.strip())
    
    # Clean search_term string to avoid list/bracket issues
    search_term = data.get("search_term", "temple")
    if isinstance(search_term, list):
        search_term = " ".join(search_term)
    search_term = str(search_term).replace("[", "").replace("]", "").replace("'", "").replace('"', "").strip()
    
    return data["title"], data["description"], search_term, data["script"]

async def generate_voiceover(text, output_file="voice.mp3"):
    print("Generating Hindi voiceover with Edge-TTS...")
    
    # Strip quotes, dashes, and special characters that break Edge-TTS SSML parsing
    clean_text = re.sub(r"['\"`“”‘’\-\[\]\(\)\{\}\!]", " ", text)
    clean_text = " ".join(clean_text.split())
    
    voices = ["hi-IN-MadhurNeural", "hi-IN-SwaraNeural"]
    
    for voice in voices:
        try:
            print(f"Trying voice: {voice}...")
            communicate = edge_tts.Communicate(clean_text, voice)
            await communicate.save(output_file)
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                print(f"Voiceover successfully generated using {voice}.")
                return
        except Exception as e:
            print(f"Voice {voice} failed with error: {e}")
            
    raise RuntimeError("Failed to generate voiceover with all available Hindi voices.")

def download_trending_bgm(output_file="trending_bgm.mp3"):
    print("Downloading royalty-free dramatic instrumental BGM...")
    bgm_urls = [
        "[https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a7322d.mp3](https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a7322d.mp3)",
        "[https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3](https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3)",
        "[https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0a13f69d2.mp3](https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0a13f69d2.mp3)"
    ]
    
    selected_url = random.choice(bgm_urls)
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        resp = requests.get(selected_url, headers=headers, timeout=30)
        if resp.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(resp.content)
            print("Successfully downloaded background music.")
            return True
        else:
            print(f"Failed to download BGM, status code: {resp.status_code}")
            return False
    except Exception as e:
        print(f"Could not download BGM: {e}")
        return False

def download_background_video(search_term, output_file="background.mp4"):
    clean_term = urllib.parse.quote(search_term)
    print(f"Searching Pexels for stock footage: {search_term} (URL encoded: {clean_term})...")
    
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"[https://api.pexels.com/videos/search?query=](https://api.pexels.com/videos/search?query=){clean_term}&per_page=5&orientation=portrait"
    
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"Pexels API failed with status {resp.status_code}: {resp.text}")
        
    data = resp.json()
    if not data.get("videos"):
        print(f"No vertical videos found for '{search_term}'. Falling back to 'temple'...")
        url = "[https://api.pexels.com/videos/search?query=temple&per_page=5&orientation=portrait](https://api.pexels.com/videos/search?query=temple&per_page=5&orientation=portrait)"
        data = requests.get(url, headers=headers).json()

    video = random.choice(data["videos"])
    video_files = video["video_files"]
    download_url = video_files[0]["link"]
    
    for vf in video_files:
        if vf.get("width") and vf.get("height") and vf["height"] > vf["width"]:
            download_url = vf["link"]
            break

    print("Downloading stock video footage...")
    v_resp = requests.get(download_url)
    with open(output_file, "wb") as f:
        f.write(v_resp.content)

def create_final_video(video_file="background.mp4", audio_file="voice.mp3", bgm_file="trending_bgm.mp3", output_file="final_short.mp4"):
    print("Editing video with MoviePy...")
    voice = AudioFileClip(audio_file)
    video = VideoFileClip(video_file)

    # Trim/loop video to match Hindi voice length
    if video.duration < voice.duration:
        loops = int(voice.duration / video.duration) + 1
        video = concatenate_videoclips([video] * loops)
    video = video.subclip(0, voice.duration)

    # Mix low volume BGM if downloaded
    if os.path.exists(bgm_file):
        print("Mixing low-volume BGM with Hindi voiceover...")
        try:
            bgm = AudioFileClip(bgm_file)
            if bgm.duration < voice.duration:
                loops = int(voice.duration / bgm.duration) + 1
                bgm = concatenate_audioclips([bgm] * loops)
            
            # Set BGM volume to 12% so Hindi narration is clear
            bgm = bgm.subclip(0, voice.duration).volumex(0.12)
            final_audio = CompositeAudioClip([voice, bgm])
        except Exception as e:
            print(f"Error mixing audio ({e}), using voiceover only...")
            final_audio = voice
    else:
        print("No BGM found, proceeding with Hindi voiceover only...")
        final_audio = voice

    final_video = video.set_audio(final_audio)
    
    final_video.write_videofile(
        output_file, 
        codec="libx264", 
        audio_codec="aac", 
        fps=24,
        logger=None
    )
    print("Final video created successfully.")

def upload_to_youtube(video_file="final_short.mp4", title="Shorts", description=""):
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
            "tags": ["Mahabharat", "HindiFacts", "Spiritual", "Shorts"],
            "categoryId": "22"
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
    print("--- STARTING HINDI AUTOMATED SHORTS PIPELINE ---")
    
    # 1. Content Generation in Hindi using gemini-3.6-flash
    title, description, search_term, script = generate_content()
    print(f"Title: {title}")
    print(f"Pexels Search Term: {search_term}")
    print(f"Hindi Script: {script}\n")

    # 2. Hindi Voiceover
    asyncio.run(generate_voiceover(script))

    # 3. Download Background Music
    download_trending_bgm()

    # 4. Download Video
    download_background_video(search_term)

    # 5. Render Video
    create_final_video()

    # 6. YouTube Upload
    upload_to_youtube(title=title, description=description)

    print("--- PIPELINE FINISHED SUCCESSFULLY ---")

if __name__ == "__main__":
    main()
    
