#import eventlet
import json
from program_files.globals import video_data
#eventlet.monkey_patch()
from flask import Flask, request, render_template, redirect, url_for
from flask_socketio import SocketIO
import os
import json
import logging
import subprocess
import sys
from program_files.outsourced_functions import (save, read,
                                                check_for_userdata, ensure_ffmpeg, open_browser, convert_command_to_text,
                                                convert_text_to_command, search_download_folder, start_download, abort_download, manage_download)
import program_files.globals as global_variables
from program_files.yt_dlp_functions import update_yt_dlp, start_get_name
import time
from datetime import datetime
import threading

logging.basicConfig(
    filename="program_files/debug2.log",
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Directory of this file
userdata_file = os.path.join(BASE_DIR, "..", "userdata.json")

download_thread = False

state = True

get_video_name_thread = False

video_queue = []

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")
import program_files.sockets as sockets
from program_files.sockets import init_socket, update_tasks, update_title_in_queue, console, emit_queue, progress
sockets.init_socket(socketio)

def log_event(msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"{now} | {msg}")   # geht in die Konsole
    logging.debug(msg)        # geht in die Datei

@app.route('/', methods=["GET", "POST"])
def home():
    print("Start home")
    video_quality = ["bestvideo", "best", "worstvideo"]
    video_resolution = ["720", "1080", "1920", "1440", "2160"]
    video_container = ["mp4", "mov", "mkv", "webm", "avi"]

    data = read("file")
    download_folder = data["download_folder"]

    default_video_quality = data["video_quality"]
    print(f"Default video quality: {default_video_quality}")
    video_quality.remove(default_video_quality)
    video_quality.insert(0, default_video_quality)
    video_quality = convert_command_to_text(video_quality)

    default_video_resolution = data["video_resolution"]
    video_resolution.remove(default_video_resolution)
    video_resolution.insert(0, default_video_resolution)

    default_video_container = data["video_container"]
    video_container.remove(default_video_container)
    video_container.insert(0, default_video_container)

    checkbox = read("custom_resolution_checkbox")
    video_checkbox = read("video_checkbox")
    audio_checkbox = read("audio_checkbox")
    print(f"Video Quality List: {video_quality}")
    return render_template('index.html',
                           download_folder=download_folder,
                           video_quality=video_quality,
                           video_resolution=video_resolution,
                           video_container=video_container,
                           checkbox=checkbox,
                           console_socket=global_variables.console_socket,
                           video_checkbox=video_checkbox,
                           audio_checkbox=audio_checkbox)

@app.route('/video_settings', methods=["GET", "POST"])
def video_settings():
    #log_event(global_variables.console_socket)
    custom_resolution = request.form.get("custom_resolution")
    video_checkbox = request.form.get("video_checkbox")
    audio_checkbox = request.form.get("audio_checkbox")
    file = read("file")
    if custom_resolution == "yes":
        video_resolution = request.form.get("video_resolution")
        if not video_resolution:
            return "No resolution set"
        file["video_resolution"] = video_resolution
        file["custom_resolution_checkbox"] = True
        video_quality = False
        audio_quality = False
    else:
        video_quality = request.form.get("video_quality")
        print(f"Video quality form: {video_quality}")
        video_quality, audio_quality = convert_text_to_command(video_quality, video_checkbox, audio_checkbox)
        print(f"Video quality: {video_quality}")
        print(f"Audio Quality: {audio_quality}")
        file["custom_resolution_checkbox"] = False
        #save("custom_resolution_checkbox", False)

        video_resolution = False
        if video_quality:
            file["video_quality"] = video_quality

    if video_checkbox == "yes":
        file["video_checkbox"] = True
    else:
        file["video_checkbox"] = False

    if audio_checkbox == "yes":
        file["audio_checkbox"] = True
    else:
        file["audio_checkbox"] = False

    video_container = request.form.get("video_container")
    if not video_container == "mp3":
        file["video_container"] = video_container
        #save("video_container", video_container)
    video_url = request.form.get("video_url")

    save("whole_file", file)
    found = next((v for v in global_variables.video_data if v["video_url"] == video_url), None)

    if found:
        console("Video already in Queue.", "python")
    else:
        entry = {
            "video_url": video_url,
            "video_resolution": video_resolution,
            "custom_resolution_checkbox": custom_resolution,
            "video_quality": video_quality,
            "audio_quality": audio_quality,
            "video_container": video_container,
            "video_name": "Loading name...",
            "video_checkbox": video_checkbox,
            "audio_checkbox": audio_checkbox,
        }
        global_variables.video_data.append(entry)
        start_get_name(video_url)
        emit_queue()
        print("End settings")
    return redirect(url_for("home"))

@app.route('/abort', methods=["GET", "POST"])
def abort():
    global_variables.abort_flag = True
    console("Abort download.", "python")
    abort_download()
    return redirect(url_for("home"))

@app.route('/choose_download_folder_page', methods=["GET", "POST"])
def choose_download_folder_page():
    folder = request.args.get("folder", "")
    path = request.args.get("path")
    if not path:
        path = os.path.expanduser("~")
    folders, new_path = search_download_folder(folder, path)
    if path == os.path.expanduser("~"):
        back_button = False
    else:
        back_button = True
    return render_template('explorer.html', folders=folders, path=new_path, back_button=back_button)

@app.route('/choose_download_folder', methods=["POST", "GET"])
def choose_download_folder():
    folder = request.args.get("folder", "")
    path = request.args.get("path")
    if not path:
        path = os.path.expanduser("~")
    folders, new_path = search_download_folder(folder, path)
    return redirect(url_for("choose_download_folder_page", folders=folders, path=new_path))

@app.route('/change_download_folder', methods=["GET", "POST"])
def change_download_folder():
    global userdata_file
    with open(userdata_file, "r", encoding="utf-8") as file:
        data = json.load(file)
        data["download_folder"] = request.args.get("path")
    with open(userdata_file, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        return redirect(url_for("home"))

@app.route('/previous_folder', methods=["GET", "POST"])
def previous_folder():
    path = request.args.get("path")
    new_path = os.path.dirname(path) #
    return redirect(url_for("choose_download_folder_page", path=new_path))

@app.route('/settings_page', methods=["GET"])
def settings_page():
    data = read("file")
    open_browser_window = data["open_browser"]
    auto_update = data["auto_update"]
    auto_merge = data["auto_merge"]
    return render_template('settings.html', open_browser_window=open_browser_window, auto_update=auto_update, auto_merge=auto_merge)

@app.route('/settings', methods=["POST"])
def settings():
    open_browser_window = request.form.get("open_browser_window")
    save("open_browser", open_browser_window)

    auto_update = request.form.get("auto_update")
    save("auto_update", auto_update)

    auto_merge = request.form.get("auto_merge")
    save("auto_merge", auto_merge)
    return redirect(url_for("settings_page"))

if __name__ == '__main__':
    result = ensure_ffmpeg()
    if result == "run":
        check_for_userdata()
        data = read("file")
        if data["open_browser"] == "yes":
            open_browser()
        update_yt_dlp()
        start_download()
        print("Started background task")
        socketio.run(app, host="0.0.0.0", port=5000, debug=True)

    elif result == "restart":
        print("Please restart this python script and the whole command line.")
    else:
        print("Error. Either ffmpeg is not installed or not entered in the system environment variables.")

# TODO: Sinnlose prints löschen
# TODO: README.MD aktualisieren wegen Qualitätseinstellungen und yt-dlp Library aktuell halte + automatischer Update und ffmpeg installieren
# TODO: Pixabay Bild erwähnen in LIENSE.md
# TODO: Console in Browser scrollbar machen
# TODO: Standard hintergrund dunkel machen
# TODO: Downloading REssources bei video download anzeigen lassen, bug
# TODO: Console nicht scrollbar
# TODO: machen dass nach reload (wenn zum Beispiel video in Queue ist) ganze Consolen History geladen wird
# TODO: Download Queue auf Seite von Console, damit Ladebalken nicht gekürzt wird, stattdessen cancel Download Button unter den PRogress Balken
# TODO: Rechtschreibfehler in Logo fixen
# TODO: Automatische Installation und start über Batch-Datei, die auch venv aktiviert