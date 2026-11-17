"""
Inspect YouTube video for captions / audio streams.
"""
import urllib.request
import re
import json

url = "https://www.youtube.com/watch?v=2FHD7FWWYNc"
req = urllib.request.Request(
    url,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
)

html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="ignore")

# Find player response
matches = re.findall(r"ytInitialPlayerResponse\s*=\s*({.+?});", html)
if not matches:
    matches = re.findall(r"var ytInitialPlayerResponse\s*=\s*({.+?});", html)

print(f"Player response matches found: {len(matches)}")
if matches:
    try:
        data = json.loads(matches[0])
        video_details = data.get("videoDetails", {})
        print(f"Title: {video_details.get('title')}")
        print(f"Duration seconds: {video_details.get('lengthSeconds')}")
        print(f"Keywords: {video_details.get('keywords', [])[:5]}")
        
        captions = data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
        print(f"Caption Tracks available: {len(captions)}")
        for c in captions:
            print(f" - Lang: {c.get('languageCode')} ({c.get('name', {}).get('simpleText')}) URL: {c.get('baseUrl')[:60]}...")
    except Exception as e:
        print(f"Error parsing player response: {e}")
