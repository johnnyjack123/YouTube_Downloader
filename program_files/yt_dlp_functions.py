from datetime import datetime, timedelta
import subprocess
import sys
from program_files.outsourced_functions import read, save
import yt_dlp
from program_files.sockets import update_title_in_queue, update_current_video
import threading
import program_files.globals as global_variables
download_process = None

def update_yt_dlp():
    now = datetime.now()

    last_update_str = read("yt-dlp_update_time")  # liest den String
    last_update = None
    if last_update_str:
        try:
            last_update = datetime.fromisoformat(last_update_str)
        except ValueError:
            last_update = None

    if last_update:
        if now - last_update < timedelta(days=1):
            return
        else:
            subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
            save("yt-dlp_update_time", now.isoformat())
    else:
        subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
        save("yt-dlp_update_time", now.isoformat())
    return

def get_name(video_url):
    with yt_dlp.YoutubeDL({}) as ydl:
        video_metadata = ydl.extract_info(video_url, download=False)
        if video_url == global_variables.current_video_url:
            global_variables.current_name = video_metadata['title']
            update_current_video()
        else:
            update_title_in_queue(video_metadata['title'], video_url)
            for entry in global_variables.video_data:
                if entry["video_url"] == video_url:
                    entry["video_name"] = video_metadata['title']
                    break


def start_get_name(video_url):
    t = threading.Thread(target=get_name, args=(video_url,))
    t.start()