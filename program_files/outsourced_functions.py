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
from program_files.update import check_for_update_launcher
from program_files.yt_dlp_functions import update_yt_dlp
from program_files.file_handling import save, read

download_process = None

def get_os():
    if global_variables.operating_system == "":
        operating_system = sys.platform
        global_variables.operating_system = operating_system
        logger.info(f"Set operating system to: {operating_system}.")
        return
    else:
        logger.info("Already os entry in global_variables.operating_systems")
        return

def ensure_ffmpeg():
    if shutil.which("ffmpeg") is not None:
        return "run"
    else:
        print("ffmpeg is not installed. It is necessary to have ffmpeg installed on your computer so the downloaded video and audio stream can merged together")
        install = input("Do you wanna install ffmpeg now? Type [yes] or [no]. You also can manually download ffmpeg from the official ffmpeg website: https://ffmpeg.org/download.html . You are not able to use this tool without ffmpeg installed.")
        if install == "yes":
                try:
                    if global_variables.operating_system == "win32":
                        subprocess.run(
                            ["winget", "install", "-e", "--id", "Gyan.FFmpeg"],
                            check=True
                        )
                        print("ffmpeg successfully installed.")
                        return "restart"
                    elif global_variables.operating_system == "linux":
                        subprocess.run(
                            ["sudo", "apt", "install", "-y", "ffmpeg"],
                            check=True
                        )
                        print("ffmpeg successfully installed.")
                        return "restart"
                    elif global_variables.operating_system == "darwin":
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

def create_task_list(video_entry, video_task, audio_task, merge_task):
    task_list = []
    file = read("file")
    download_data = file["download_data"]
    if video_entry["video_container"] != "mp3":
        if video_entry["video_checkbox"]:
            task_list.append({"name": "Download Video", "status": video_task})
        if video_entry["audio_checkbox"] and not video_entry["video_quality"] == "best":
            task_list.append({"name": "Download Audio", "status": audio_task})
        if download_data["auto_merge"] == "yes" and video_entry["video_checkbox"] and video_entry["audio_checkbox"] and not video_entry["video_quality"] == "best":
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
            logger.info(f"Video download data: {video_entry}")
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
                [sys.executable, "-m", "program_files.download", video_json, "--project-dir", os.path.abspath("."), "--operating_system", global_variables.operating_system],
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
                        global_variables.task_list = create_task_list(video_entry, data["args"][0], data["args"][1], data["args"][2])
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
                    save("whole_file", file)
                    #console("Subprocess output: " + str(line)) <-- uncomment for error messages in the web console

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



def send_status(function_name, function_args): #Important for download and merge process
    cmd = json.dumps({"function": function_name, "args": function_args})
    print(cmd, flush=True)
    return

def get_gpu():
    file = read("file")
    program_data = file["program_data"]
    if global_variables.operating_system == "win32":
        out = subprocess.check_output(
            ["wmic", "path", "Win32_VideoController", "get", "Name"],
            text=True, stderr=subprocess.STDOUT
        )
        # erste Zeile ist Header "Name"
        name = [line.strip() for line in out.splitlines() if line.strip() and line.strip().lower() != "name"]
        logger.info(f"name: {name}")
        if len(name) == 0:
            return False
        elif program_data["gpu"] != []:
            logger.info(f"GPU-Name: {program_data["gpu"][0]}")
            if set(program_data["gpu"]) != set(name):
                program_data["gpu"] = name
                file["program_data"] = program_data
                save("whole_file", file)
                logger.warning("Radical GPU Hardware change detected. Please select your current GPU in settings page if you want to use GPU-acceleration.")
                console("Radical GPU Hardware change detected. Please select your current GPU in settings page if you want to use GPU-acceleration.", "python")
                print("Radical GPU Hardware change detected. Please select your current GPU in settings page if you want to use GPU-acceleration.")
            return True
        else:
            program_data["gpu"] = name
            file["program_data"] = program_data
            save("whole_file", file)
            #platform, video_option, decoder = get_platform(name)
    elif global_variables.operating_system == "linux":
        out = subprocess.check_output(["lspci"], text=True)
        name = [l for l in out.splitlines() if ("VGA compatible controller" in l) or ("3D controller" in l)]
        if len(name) == 0:
            return False
        elif program_data["gpu"] != []:
            logger.info(f"GPU-Name: {program_data["gpu"]}")
            return True
        else:
            program_data["gpu"] = name
            file["program_data"] = program_data
            save("whole_file", file)
    elif global_variables.operating_system == "darwin":
        platform = "Apple"
        video_option = "h264_videotoolbox"
    else:
        decoder = False
        video_option = False
        platform = False
    #return decoder, video_option, platform

def prepare_program():
    get_os()
    check_for_update_launcher()
    update_yt_dlp()
    check_for_queue() #Checks, if there is still a queue from the previous download process saved in userdata.json
    start_download() #Starts manage_download worker
    data = read("file")
    userdata = data["userdata"]
    if userdata["open_browser"] == "yes":
        open_browser()
    if userdata["gpu_acceleration"]:
        get_gpu()
    return