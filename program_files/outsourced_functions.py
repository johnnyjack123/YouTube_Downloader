import subprocess
import os
import sys
import json
import webbrowser
import threading
import time
import requests
import program_files.globals as global_variables
from program_files.sockets import progress, console, update_tasks, emit_queue, update_current_video, cancel_button
from program_files.logger import logger
import program_files.safe_shutil as shutil
from program_files.safe_shutil import _check_path

download_process = None

def save(entry, video_data):
    userdata_file = global_variables.userdata_file
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
    userdata_file = global_variables.userdata_file
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
    print("Check for userdata.")
    userdata_file = global_variables.userdata_file
    entry = {
        "userdata": global_variables.userdata,
        "program_data": global_variables.program_data,
        "download_data": global_variables.download_data
    }
    if not os.path.exists(userdata_file):
        with open(userdata_file, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=4, ensure_ascii=False)
        print("Created userdata")
    return

def ensure_ffmpeg():
    if shutil.which("ffmpeg") is not None:
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
                        print("ffmpeg successfully installed.")
                        return "restart"
                    elif sys.platform == "darwin":
                        subprocess.run(
                            ["brew", "install", "ffmpeg"],
                            check=True
                        )
                        print("ffmpeg successfully installed.")
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
    file = read("file")
    download_data = file["download_data"]
    if video_data["video_container"] != "mp3":
        if video_data["video_checkbox"]:
            task_list.append({"name": "Download Video", "status": video_task})
        if video_data["audio_checkbox"]:
            task_list.append({"name": "Download Audio", "status": audio_task})
        if download_data["auto_merge"] == "yes" and video_data["video_checkbox"] and video_data["audio_checkbox"]:
            task_list.append({"name": "Merge", "status": merge_task})
    else:
        task_list.append({"name": "Download Audio", "status": audio_task})
        task_list.append({"name": "Re-encode audio to mp3", "status": merge_task})
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
            cmd_audio = "bestaudio/best" #Not the best way, because by single video downloads there is no fallback.
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
    while True:
        if global_variables.video_queue and not global_variables.abort:
            global_variables.is_downloading = True
            cancel_button()
            video_entry = global_variables.video_queue[0]
            file = read("file")
            program_data = file["program_data"]
            program_data["video_queue"] = global_variables.video_queue
            file["program_data"] = program_data
            save("whole_file", file)
            emit_queue()

            global_variables.current_video_data = video_entry
            update_current_video()
            video_json = json.dumps(video_entry)

            download_process = subprocess.Popen(
                [sys.executable, "-m", "program_files.download_and_merge", video_json, "--project-dir", os.path.abspath(".")],
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
                    file = read("file")
                    program_data = file["program_data"]
                    program_data["video_queue"] = global_variables.video_queue
                    file["program_data"] = program_data
                    save("whole_file", file)                    #console("Subprocess output: " + str(line)) <-- uncomment for error messages in the web console

            download_process.wait()
            print("Process finished with code", download_process.returncode)

            global_variables.is_downloading = False
            cancel_button()

            if download_process.returncode == 0 and not global_variables.abort:
                global_variables.video_queue.pop(0)
                file = read("file")
                program_data = file["program_data"]
                program_data["video_queue"] = global_variables.video_queue
                file["program_data"] = program_data
                save("whole_file", file)
            else:
                console("Download interrupted — keeping in queue.", "python")
                file = read("file")
                program_data = file["program_data"]
                program_data["video_queue"] = global_variables.video_queue
                file["program_data"] = program_data
                save("whole_file", file)
        else:
            global_variables.current_video_data["video_name"] = "No active download."
            update_current_video()
            time.sleep(0.2)

def abort_download():
    global download_process
    download_process.terminate()

def check_for_queue():
    data = read("file")
    userdata = data["userdata"]
    program_data = data["program_data"]
    download_previous_queue = userdata["download_previous_queue"]
    if download_previous_queue == "yes":
        video_queue = program_data["video_queue"]
        if video_queue:
            global_variables.video_queue = video_queue
            console("Continuing download previous queue.", "python")
    else:
        program_data["video_queue"] = []
        data["program_data"] = program_data
        save("whole_file", data)

def create_folders():
    if not os.path.exists("tmp"):
        os.makedirs("tmp")

    tmp_launcher_folder = os.path.join("tmp", "launcher")
    if not os.path.exists(tmp_launcher_folder):
        os.makedirs(tmp_launcher_folder)
    else:
        shutil.rmtree(tmp_launcher_folder)
        os.makedirs(tmp_launcher_folder)

    tmp_old_files = os.path.join("tmp", "old_files")
    if not os.path.exists(tmp_old_files):
        os.makedirs(tmp_old_files)
    else:
        shutil.rmtree(tmp_old_files)
        os.makedirs(tmp_old_files)

    tmp_old_files_launcher = os.path.join("tmp", "old_files", "launcher")
    if not os.path.exists(tmp_old_files_launcher):
        os.makedirs(tmp_old_files_launcher)
    else:
        shutil.rmtree(tmp_old_files_launcher)
        os.makedirs(tmp_old_files_launcher)

    tmp_old_files_main = os.path.join("tmp", "old_files", "main")
    if not os.path.exists(tmp_old_files_main):
        os.makedirs(tmp_old_files_main)
    else:
        shutil.rmtree(tmp_old_files_main)
        os.makedirs(tmp_old_files_main)

    va = os.path.join("tmp", "va")
    if not os.path.exists(va):
        os.makedirs(va)
    else:
        shutil.rmtree(va)
        os.makedirs(va)
    return