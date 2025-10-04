import yt_dlp
import json
import subprocess
import os
import shutil
import sys
import json
import program_files.globals as global_variables
from program_files.sockets import progress, console, update_tasks, emit_queue, update_current_video, cancel_button
import webbrowser
import threading
import time

download_process = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Ordner, wo die aktuelle Datei liegt
userdata_file = os.path.join(BASE_DIR, "..", "userdata.json")

def save(entry, video_data):
    with open(userdata_file, "r", encoding="utf-8") as file:
        data = json.load(file)
        if entry == "whole_file":
            data = video_data
        else:
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
        "auto_merge": "yes",
        "download_previous_queue": "yes",
        "video_queue": []
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
        if global_variables.video_queue and not global_variables.abort:

            global_variables.is_downloading = True
            cancel_button()
            video_entry = global_variables.video_queue.pop(0)
            emit_queue()

            #global_variables.current_video_url = video_entry["video_url"]
            #global_variables.current_name = video_entry["video_name"]
            global_variables.current_video_data = video_entry
            update_current_video()
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
                        cmd = data["args"][0]
                        source = data["args"][1]
                        console(cmd, source)
                    else:
                        print(data)
                except json.JSONDecodeError:
                    print("Subprocess output:", line)
                    #console("Subprocess output: " + str(line)) <-- uncomment for error messages in the web console

            download_process.wait()
            print("Process finished with code", download_process.returncode)
            global_variables.is_downloading = False
            cancel_button()
            save("video_queue", global_variables.video_queue)
        else:
            global_variables.current_video_data["video_name"] = "No active download."
            update_current_video()
            time.sleep(0.2)

def abort_download():
    global download_process
    download_process.terminate()

def check_for_queue():
    data = read("file")
    download_previous_queue = data["download_previous_queue"]
    if download_previous_queue == "yes":
        video_queue = data["video_queue"]
        if video_queue:
            global_variables.video_queue = video_queue
            console("Continuing download previous queue.", "python")
    else:
        data["video_queue"] = []
        save("whole_file", data)
