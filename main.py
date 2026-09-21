import os
import random
import requests
import asyncio
import edge_tts
from google import genai
from moviepy.editor import VideoFileClip, AudioFileClip
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 1. Fetch Environment Variables
GEMINI_KEY = os.environ["GEMINI_API_KEY"]
PEXELS_KEY = os.environ["PEXELS_API_KEY"]
CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]
CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]

# Topics array - expandable anytime
TOPICS = ["mindblowing space facts", "interesting psychological facts", "crazy historical facts", "weird nature facts"]

async def generate_speech(text, output_file="voice.mp3"):
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(output_file)

def get_pexels_video(query):
    headers = {"Authorization": PEXELS_KEY}
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=5"
    response = requests.get(url, headers=headers).json()
    
    videos = response.get("videos", [])
    if not videos:
        url = "https://api.pexels.com/videos/search?query=nature&orientation=portrait&per_page=5"
        videos = requests.get(url, headers=headers).json().get("videos", [])
        
    video_url = videos[0]["video_files"][0]["link"]
    
    video_data = requests.get(video_url).content
    with open("background.mp4", "wb") as f:
        f.write(video_data)

def generate_content():
    client = genai.Client(api_key=GEMINI_KEY)
    topic = random.choice(TOPICS)
    
    prompt = f"""
    Create a catchy, engaging 30-second script about {topic} for a YouTube Short.
    Provide output in this EXACT format:
    TITLE: [Insert title here with hashtags]
    DESCRIPTION: [Insert brief description]
    SEARCH: [One word search query for background video, e.g. galaxy, ocean, history]
    SCRIPT: [The narration spoken text only]
    """
    
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )
    
    text = response.text
    lines = text.split("\n")
    
    title = "Interesting Fact #Shorts"
    description = "Automated Short"
    search_term = "space"
    script = ""
    
    for line in lines:
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("DESCRIPTION:"):
            description = line.replace("DESCRIPTION:", "").strip()
        elif line.startswith("SEARCH:"):
            search_term = line.replace("SEARCH:", "").strip()
        elif line.startswith("SCRIPT:"):
            script = line.replace("SCRIPT:", "").strip()
            
    if not script:
        script = text
        
    return title, description, search_term, script

def build_video():
    audio = AudioFileClip("voice.mp3")
    video = VideoFileClip("background.mp4")
    
    # Loop video if audio is longer than background video
    if video.duration < audio.duration:
        video = video.loop(duration=audio.duration)
    else:
        video = video.subclip(0, audio.duration)
        
    final_video = video.set_audio(audio)
    final_video.write_videofile("final_short.mp4", fps=30, codec="libx264", audio_codec="aac")

def upload_to_youtube(title, description):
    creds = Credentials(
        None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    
    youtube = build("youtube", "v3", credentials=creds)
    
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "categoryId": "27"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }
    
    media = MediaFileUpload("final_short.mp4", chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")
            
    print(f"Video uploaded successfully! Video ID: {response['id']}")

if __name__ == "__main__":
    print("Generating video script...")
    title, description, search_term, script = generate_content()
    
    print("Generating voiceover...")
    asyncio.run(generate_speech(script))
    
    print("Downloading background video...")
    get_pexels_video(search_term)
    
    print("Stitching video and audio together...")
    build_video()
    
    print("Uploading to YouTube...")
    upload_to_youtube(title, description)
    print("Done!")
  
