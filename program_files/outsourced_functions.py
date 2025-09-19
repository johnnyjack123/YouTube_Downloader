import yt_dlp
import json
import subprocess
import os
import shutil
import sys
import json
import program_files.globals as global_variables
from program_files.sockets import progress, console, update_tasks, emit_queue
import webbrowser
import threading
import time

download_process = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Ordner, wo die aktuelle Datei liegt
userdata_file = os.path.join(BASE_DIR, "..", "userdata.json")

video_quality_cmd = list(global_variables.quality_map.keys())

def sort_formats(video_url, video_resolution):
    # Check if quality is available
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl_extract:
        info_dict = ydl_extract.extract_info(video_url, download=False)
        formats_list = info_dict.get('formats', [])
        title = info_dict.get("title", "video")

    # Filter video formats
    video_formats = [f for f in formats_list if f.get('vcodec') != 'none']
    #resolutions = [(f["height"], f["format_id"]) for f in video_formats if f.get("height")]

    # Filter audio formats
    audio_formats = [f for f in formats_list if f.get('acodec') != 'none']

    # Sort videos by resolution (height)
    video_formats_sorted = sorted(video_formats, key=lambda f: f.get('height') or 0)

    # Sort audio by bitrate
    audio_formats_sorted = sorted(audio_formats, key=lambda f: f.get('abr') or 0)

    file = read("file")
    # Find the correct quality dependent on users choice
    if not file["checkbox"]:
        if video_resolution == "Best":
            # Best quality
            video_format = video_formats_sorted[-1]['format_id']
            audio_format = audio_formats_sorted[-1]['format_id']
        elif video_resolution == "Average":
            # Medium quality
            video_format = video_formats_sorted[len(video_formats_sorted) // 2]['format_id']
            audio_format = audio_formats_sorted[len(audio_formats_sorted) // 2]['format_id']
        elif video_resolution == "Worst":
            # Worst quality
            video_format = video_formats_sorted[0]['format_id']
            audio_format = audio_formats_sorted[0]['format_id']
        else:
            print("Quality preset not found.")

        print("Audio formats found:", [f['format_id'] for f in audio_formats_sorted])
        print("Video format: " + video_format)
        print("Audio format: " + audio_format)

        # Create command for yt-dlp
        if video_format and audio_format:
            video_resolution = f"{video_format}+{audio_format}"
        elif video_format:
            video_resolution = f"{video_format}"
        elif audio_format:
            video_resolution = f"{audio_format}"
        print("Video resolution: " + video_resolution)

def find_closest_resolution(video_height, video_formats):
    # Nur Formate mit definierter Höhe
    valid_formats = [f for f in video_formats if f.get("height")]
    # Sortieren nach Höhe
    valid_formats.sort(key=lambda f: f["height"])
    # Nächstgelegene finden
    closest = min(valid_formats, key=lambda f: abs(f["height"] - video_height))
    return closest["format_id"], closest["height"]

def get_frame_count_estimate(video_file):
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=avg_frame_rate,duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_file
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    fps_str, duration_str = result.stdout.strip().split("\n")

    # FPS ist oft ein Bruch wie "30000/1001"
    num, den = map(int, fps_str.split('/'))
    fps = num / den
    duration = float(duration_str)

    return int(duration * fps)

def save(entry, video_data):
    with open(userdata_file, "r", encoding="utf-8") as file:
        data = json.load(file)
        data[entry] = video_data
    with open(userdata_file, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    return

def read(entry):
    if entry == "file":
        with open(userdata_file, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data
    elif entry:
        with open(userdata_file, "r", encoding="utf-8") as file:
            data = json.load(file)
            video_data = data[entry]
            return video_data

def check_for_userdata():
    default_download_folder = os.path.join(os.path.expanduser("~"), "Videos")
    default_content = {
        "download_folder": default_download_folder,
        "video_quality": "best",
        "video_resolution": "1080",
        "video_resolution_command": "bv[height<=1080]+ba[height<=1080]",
        "video_container": "mp4",
        "custom_resolution_checkbox": False,
        "video_checkbox": True,
        "audio_checkbox": True,
        "yt-dlp_update_time": "2025-09-06T17:40:36.348409",
        "open_browser": "yes",
        "auto_update": "yes",
        "auto_merge": "yes"
    }
    if not os.path.exists(userdata_file):
        with open(userdata_file, "w", encoding="utf-8") as f:
            json.dump(default_content, f, indent=4, ensure_ascii=False)

def ensure_ffmpeg():
    if shutil.which("ffmpeg") is not None:
        print("ffmpeg found.")
        return "run"
    else:
        print("ffmpeg is not installed. It is necessary to have ffmpeg installed on your computer so the downloaded video and audio stream can merged together")
        install = input("Do you wanna install ffmpeg now? Type [yes] or [no]. You also can manually download ffmpeg from the official ffmpeg website: https://ffmpeg.org/download.html . You are not able to use this tool without ffmpeg installed.")
        if install == "yes":
                try:
                    if sys.platform == "win32":
                        subprocess.run(
                            ["winget", "install", "-e", "--id", "Gyan.FFmpeg"],
                            check=True
                        )
                        print("ffmpeg successfully installed.")
                        return "restart"
                    elif sys.platform == "linux":
                        subprocess.run(
                            ["sudo", "apt", "install", "-y", "ffmpeg"],
                            check=True
                        )
                        return "restart"
                    elif sys.platform == "darwin":
                        subprocess.run(
                            ["brew", "install", "ffmpeg"],
                            check=True
                        )
                        return "restart"
                    else:
                        print("OS not found. Please install ffmpeg manually from the official website: https://ffmpeg.org/download.html")
                        return False
                except Exception as e:
                    print("Installation failed:", e)
                    return False
        else:
            return False

def create_task_list(video_data, video_task, audio_task, merge_task):
    task_list = []
    if video_data["video_checkbox"]:
        task_list.append({"name": "Download Video", "status": video_task})
    if video_data["audio_checkbox"]:
        task_list.append({"name": "Download Audio", "status": audio_task})
    data = read("file")
    if data["auto_merge"] == "yes":
        task_list.append({"name": "Merge", "status": merge_task})
    return task_list

def open_browser():
    url = "http://127.0.0.1:5000"
    webbrowser.open(url)
    return

def convert_text_to_command(description, video_checkbox, audio_checkbox):
    reverse_map = {v: k for k, v in global_variables.quality_map.items()}

    cmd_video = False
    cmd_audio = False

    if video_checkbox == "yes":
        if description in reverse_map:
            cmd_video = reverse_map[description]

    if audio_checkbox == "yes":
        if description == "Best":
            cmd_audio = "bestaudio/best" #Not the best way, because by single video downloads there is noch fallback.
        elif description == "Average":
            if not video_checkbox == "yes" and audio_checkbox == "yes":
                cmd_audio = "bestaudio/best"
            else:
                cmd_audio = False  # "Average" = nur Video
        elif description == "Worst":
            cmd_audio = "worstaudio/worst"
    return cmd_video, cmd_audio

def convert_command_to_text(cmd_list):
    text = []
    for entry in cmd_list:
        if entry in global_variables.quality_map:
            text.append(global_variables.quality_map[entry])
        else:
            text.append(entry)  # fallback: gib original zurück
    return text

def search_download_folder(folder, path):
    if folder:
        path = os.path.join(path, folder)
    else:
        path = path
    folders = [
        f for f in os.listdir(path)
        if os.path.isdir(os.path.join(path, f)) and not f.startswith(".")  # hidden Unix-directories
    ]
    return folders, path

def start_download():
    manage_download_thread = threading.Thread(target=manage_download, daemon=True)
    manage_download_thread.start()
    return

def manage_download():
    global download_process
    print("Manage download.")
    while True:
        if global_variables.video_data:

            global_variables.is_downloading = True
            #while global_variables.video_data:
            video_entry = global_variables.video_data.pop(0)
            video_json = json.dumps(video_entry)
            download_process = subprocess.Popen(
                [sys.executable, "-u", "program_files/download_and_merge.py", video_json],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Fehler landen auch im stdout
                text=True,
                bufsize=1
            )

            for line in download_process.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data["function"] == "task_list":
                        global_variables.task_list = create_task_list(data["args"][0], data["args"][1], data["args"][2], data["args"][3])
                        update_tasks()
                    elif data["function"] == "progress":
                        progress(data["args"][0], data["args"][1], data["args"][2], data["args"][3])
                    elif data["function"] == "download_type":
                        global_variables.download_type = data["args"]
                    elif data["function"] == "state_logger":
                        global_variables.state_logger = data["args"]
                    elif data["function"] == "console":
                        console(data["args"])
                    else:
                        print(data)
                except json.JSONDecodeError:
                    print("Subprocess output:", line)
                    #console("Subprocess output: " + str(line)) <-- uncomment for error messages in the web console

            download_process.wait()
            print("Prozess beendet mit Code", download_process.returncode)
            global_variables.is_downloading = False
        else:
            time.sleep(0.2)

def abort_download():
    global download_process
    download_process.terminate()