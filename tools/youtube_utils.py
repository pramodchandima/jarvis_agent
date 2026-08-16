"""
Utility functions for searching and downloading audio from YouTube.
"""
from core.config_manager import config
from googleapiclient.discovery import build
import yt_dlp

GOOGLE_API_KEY = getattr(config, "GOOGLE_API_KEY", None)

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
