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
    userdata = file["userdata"]
    if video_data["video_container"] != "mp3":
        if video_data["video_checkbox"]:
            task_list.append({"name": "Download Video", "status": video_task})
        if video_data["audio_checkbox"]:
            task_list.append({"name": "Download Audio", "status": audio_task})
        if userdata["auto_merge"] == "yes" and video_data["video_checkbox"] and video_data["audio_checkbox"]:
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

    tmp_old_files = os.path.join("tmp", "old_files")
    if not os.path.exists(tmp_old_files):
        os.makedirs(tmp_old_files)

    tmp_old_files_launcher = os.path.join("tmp", "old_files", "launcher")
    if not os.path.exists(tmp_old_files_launcher):
        os.makedirs(tmp_old_files_launcher)

    tmp_old_files_main = os.path.join("tmp", "old_files", "main")
    if not os.path.exists(tmp_old_files_main):
        os.makedirs(tmp_old_files_main)
    return

def check_for_updates(url_version, file_name, update):
    new_version_file = os.path.join("tmp", file_name)
    result = get_file(url_version, new_version_file)
    if result:
        try:
            if update == "launcher":
                version_file = file_name
            elif update == "main":
                version_file = os.path.join("program_files", file_name)
            else:
                return f"Wrong update mode set: {update}."

            if not os.path.exists(version_file):
                with open(version_file, "w", encoding="utf-8") as f:
                    f.write("0.0")

            with open(version_file, "r", encoding="utf-8") as file:
                program_version = float(file.read().strip())
            with open(new_version_file, "r", encoding="utf-8") as file:
                new_version = float(file.read().strip())
            if new_version > program_version:
                return "Update"
            else:
                print("Program is up to date")
                logger.info("Program is up to date")
                return "Launch"
        except Exception as e:
            logger.error(f"No {file_name} available.")
            return "Update"
    else:
        return "Launch"

def get_file(url, save_path):
    file = read("file")
    program_data = file["program_data"]
    response_version = requests.get(url)
    if response_version.status_code == 200:
        with open(save_path, "wb") as file:
            file.write(response_version.content)
            logger.info(f"{save_path} stored in /tmp")
            return True
    else:
        logger.error(f"File {save_path} is unreachable on repo {program_data["update_repo"]} and branch {program_data["update_branch"]}.")
        return False

def update_launcher():
    file = read("file")
    server_data = file["server_data"]
    branch = server_data["update_branch"]
    repo = server_data["update_repo"]
    url_launcher_py = f"https://raw.githubusercontent.com/{repo}/refs/heads/{branch}/launcher.py"
    url_launcher_bat = f"https://raw.githubusercontent.com/{repo}/refs/heads/{branch}/launcher.bat"
    tmp_launcher_folder = os.path.join("tmp", "launcher")
    launcher_py_path = os.path.join(tmp_launcher_folder, "launcher.py")
    launcher_bat_path = os.path.join(tmp_launcher_folder, "launcher.bat")
    launcher_py_old_path = os.path.join("tmp", "old_files", "launcher", "launcher.py")
    launcher_bat_old_path = os.path.join("tmp", "old_files", "launcher", "launcher.bat")
    result = get_file(url_launcher_py, launcher_py_path)
    if not result:
        return False
    result = get_file(url_launcher_bat, launcher_bat_path)
    if not result:
        return False

    try:
        shutil.move("launcher.py", launcher_py_old_path)
        shutil.move("launcher.bat", launcher_bat_old_path)
    except PermissionError as e:
        logger.error(f"Unable to move old launcher files: {e}")

    try:
        shutil.move(launcher_py_path, "launcher.py")
        shutil.move(launcher_bat_path, "launcher.bat")
    except PermissionError as e:
        logger.error(f"Permission error: {e}")
        shutil.move(launcher_py_old_path, "launcher.py")
        shutil.move(launcher_bat_old_path, "launcher.bat")


    logger.info("Launcher successfully updated.")
    new_launcher_version_path = os.path.join("tmp", "launcher_version.txt")
    for path in [launcher_py_old_path, launcher_bat_old_path, "launcher_version.txt"]:
        _check_path(path)
        os.remove(path)

    shutil.move(new_launcher_version_path, "launcher_version.txt")
    logger.info("Old files deleted.")
    return

def check_for_update_launcher():
    file = read("file")
    program_data = file["program_data"]
    branch = program_data["update_branch"]
    repo = program_data["update_repo"]
    url_version = f"https://raw.githubusercontent.com/{repo}/refs/heads/{branch}/launcher_version.txt"
    file_name = "launcher_version.txt"
    update = "launcher"
    result = check_for_updates(url_version, file_name, update)
    if result == "Update":
        logger.info("Update program launcher.")
        print("Update program launcher.")
        update_launcher()
    elif result == "Launch":
        logger.info("Launcher is up to date.")
    else:
        logger.error(f"Error in update process: {result}")