"""
Utility functions for searching and downloading audio from YouTube.
"""
import os
import tempfile
from dotenv import load_dotenv
from googleapiclient.discovery import build
import yt_dlp

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def search_youtube(query):
    """Search YouTube for a video and return the first result's ID and title."""
    if not GOOGLE_API_KEY:
        return None, "Google API Key missing."

    try:
        youtube = build("youtube", "v3", developerKey=GOOGLE_API_KEY)
        request = youtube.search().list(  # pylint: disable=no-member
            q=query,
            part="snippet",
            maxResults=1,
            type="video"
        )
        response = request.execute()

        if not response["items"]:
            return None, "No results found."

        video_id = response["items"][0]["id"]["videoId"]
        video_title = response["items"][0]["snippet"]["title"]
        return video_id, video_title
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"YouTube API Error: {e}. Falling back to yt-dlp search...")
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                if 'entries' in info and info['entries']:
                    entry = info['entries'][0]
                    return entry['id'], entry['title']
        except Exception as e2:  # pylint: disable=broad-exception-caught
            print(f"yt-dlp search error: {e2}")

        return None, str(e)

def get_audio_url(video_id):
    """Get the audio URL (or download path) for a YouTube video."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    # We'll download to a temporary file
    temp_dir = tempfile.gettempdir()
    output_template = os.path.join(temp_dir, f"jarvis_music_{video_id}.%(ext)s")

    webm_path = output_template.replace('%(ext)s', 'webm')
    if os.path.exists(webm_path):
        try:
            os.remove(webm_path)
        except OSError:
            pass

    m4a_path = output_template.replace('%(ext)s', 'm4a')
    if os.path.exists(m4a_path):
        try:
            os.remove(m4a_path)
        except OSError:
            pass

    ydl_opts = {
        # Limit to 128kbps or lower for speed, but keep it playable.
        # It will try to find the best audio under or equal to 128k.
        'format': 'bestaudio[abr<=128]/bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'noplaylist': True,
        'quiet': True,
        'continuedl': False, # Disable resume to avoid 416 errors
        'nocheckcertificate': True,
        'ignoreerrors': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            # Find the actual file path
            ext = info.get('ext')
            file_path = output_template.replace('%(ext)s', ext)
            return file_path
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"yt-dlp error: {e}")
        return None

if __name__ == "__main__":
    # Quick test
    vid, title = search_youtube("Lana Del Rey Summertime Sadness")
    print(f"Found: {title} ({vid})")
    if vid:
        path = get_audio_url(vid)
        print(f"Downloaded to: {path}")
