import os
import datetime
from moviepy.editor import *
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- 1. VIDEO GENERATION ---

def generate_geography_short():
    """
    Generates a 30-second vertical video (9:16 aspect ratio).
    Replace the text/color clips with your doodle assets or AI API calls.
    """
    print("Generating Geography Short...")
    
    # Define vertical resolution for Shorts
    width, height = 1080, 1920
    
    # Determine which part of the syllabus to teach based on the time
    current_hour = datetime.datetime.utcnow().hour
    if current_hour < 10: # Morning run
        topic = "Maharashtra Geography:\nThe Western Ghats (Sahyadris)\nBlock moisture, create heavy rain!"
    else: # Evening run
        topic = "Maharashtra Geography:\nThe Deccan Plateau\nFormed by volcanic lava flows!"

    # Create a basic background (replace ColorClip with ImageClip for actual doodles)
    background = ColorClip(size=(width, height), color=(240, 240, 240)).set_duration(30)
    
    # Create the text layer
    text_clip = TextClip(
        topic, 
        fontsize=70, 
        color='black', 
        font='Arial-Bold',
        method='caption',
        size=(900, None),
        align='center'
    ).set_position('center').set_duration(30)

    # Composite the video
    final_video = CompositeVideoClip([background, text_clip])
    
    output_filename = "maharashtra_geo_short.mp4"
    final_video.write_videofile(output_filename, fps=24, codec="libx264", audio=False, preset="ultrafast")
    print(f"Video saved as {output_filename}")
    return output_filename

# --- 2. YOUTUBE AUTHENTICATION & UPLOAD ---

def authenticate_youtube():
    """
    Authenticates using the token.json file. 
    It will automatically refresh the token if it has expired.
    """
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/youtube.upload'])

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Access token expired. Refreshing...")
            creds.refresh(Request())
            # Save the updated token back to the file
            with open('token.json', 'w') as token_file:
                token_file.write(creds.to_json())
        else:
            raise Exception("Invalid or missing token.json. You must authenticate locally first.")

    return build('youtube', 'v3', credentials=creds)

def upload_to_youtube(youtube, video_file):
    print("Preparing YouTube Upload...")
    
    # The title and description must include #Shorts
    title = f"Class 10 Geography - Maharashtra Board #Shorts"
    description = "Daily geography facts for Maharashtra Board Class 10! #geography #maharashtra #class10 #ssc #shorts"
    
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': ['education', 'geography', 'maharashtra board', 'class 10', 'shorts'],
            'categoryId': '27' # 27 is Education
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False 
        }
    }

    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )

    response = None
    print("Uploading file...")
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")

    print(f"Upload Complete! Video ID: {response['id']}")

# --- 3. MAIN EXECUTION ---

if __name__ == "__main__":
    try:
        video_path = generate_geography_short()
        youtube_service = authenticate_youtube()
        upload_to_youtube(youtube_service, video_path)
    except Exception as e:
        print(f"Pipeline failed: {e}")
        exit(1)
        
