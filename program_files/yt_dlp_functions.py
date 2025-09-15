from datetime import datetime, timedelta
import subprocess
import sys
from program_files.outsourced_functions import read, save
import yt_dlp
import os
from program_files.sockets import console, progress, update_title_in_queue
import threading
import program_files.globals as global_variables

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

def progress_hook(d):
    if global_variables.abort_flag:
        console("Download aborted")
        raise yt_dlp.utils.DownloadError("Abort Download!")

    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0.0%').strip()
        speed = d.get('_speed_str', 'N/A')
        eta = d.get('_eta_str', 'N/A')
        progress("downloading", percent, speed, eta)

class Logger:
    def debug(self, msg):
        if msg.startswith("[info] Testing format"):
            command = "[yt-dlp]: Testing formats"
            console(command)
        elif msg.startswith("[download]"):
            if global_variables.is_downloading:
                if global_variables.state_logger:
                    command = "[" + global_variables.download_type + "] Downloading..."
                    global_variables.state_logger = False
                    console(command)
                else:
                    pass
        elif msg.startswith("[youtube]"):
            console("Downloading resources.") # TODO: noch machen, dass nur einmal pro Video geschrieben wird
        else:
            command = "[yt-dlp]" + msg
            console(command)
    def warning(self, msg):
        print("WARN:", msg)
        console(msg)

    def error(self, msg):
        print("ERROR:", msg)
        console(msg)

def download_video(video_input, download_folder, video_url):
    ydl_opts_video = {
        'format': video_input,
        'outtmpl': os.path.join(download_folder, '%(title)s_video.%(ext)s'),
        'progress_hooks': [progress_hook],
        'no_color': True,
        # Suppresses coloured output, as otherwise the numbers cannot be displayed correctly in the browser
        'logger': Logger()
    }

    with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
        info_video = ydl.extract_info(video_url, download=True)
        video_file = ydl.prepare_filename(info_video)  # returns the absolute path of the video file
    return video_file

def download_audio(audio_input, download_folder, video_url):
    ydl_opts_audio = {
        'format': audio_input,
        'outtmpl': os.path.join(download_folder, '%(title)s_audio.%(ext)s'),
        'progress_hooks': [progress_hook],
        'no_color': True,
        # Suppresses coloured output, as otherwise the numbers cannot be displayed correctly in the browser
        'logger': Logger()
    }

    with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
        info_audio = ydl.extract_info(video_url, download=True)
        audio_file = ydl.prepare_filename(info_audio)
    return audio_file

def get_name(video_url):
    with yt_dlp.YoutubeDL({}) as ydl:
        video_metadata = ydl.extract_info(video_url, download=False)
        print("Titel:", video_metadata['title'])
        update_title_in_queue(video_metadata['title'], video_url)

def start_get_name(video_url):
    t = threading.Thread(target=get_name, args=(video_url,))
    t.start()