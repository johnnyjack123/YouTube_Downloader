import eventlet
from PyInstaller.lib.modulegraph.modulegraph import entry
eventlet.monkey_patch()
from flask import Flask, request, render_template, redirect, url_for
from flask_socketio import SocketIO
import threading
import os
import json
import logging
import subprocess
import sys
from program_files.outsourced_functions import (save, read, merging_video_audio, convert_audio_to_mp3,
                                                check_for_userdata, ensure_ffmpeg, create_task_list, open_browser, convert_command_to_text,
                                                convert_text_to_command, search_download_folder)
import program_files.globals as global_variables
from program_files.yt_dlp_functions import update_yt_dlp, download_video, download_audio, start_get_name


BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Directory of this file
userdata_file = os.path.join(BASE_DIR, "..", "userdata.json")

download_thread = False

state = True

get_video_name_thread = False

video_queue = []

app = Flask(
    __name__,
    template_folder = "./templates",
    static_folder = "./static",
)

socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")
import program_files.sockets as sockets
from program_files.sockets import init_socket, update_tasks, update_title_in_queue, console, emit_queue, progress
sockets.init_socket(socketio)

@app.route('/', methods=["GET", "POST"])
def home():
    video_quality = ["bestvideo", "best", "worstvideo"]
    video_resolution = ["720", "1080", "1920", "1440", "2160"]
    video_container = ["mp4", "mov", "mkv", "webm", "avi"]

    data = read("file")
    download_folder = data["download_folder"]

    default_video_quality = data["video_quality"]

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
    custom_resolution = request.form.get("custom_resolution")
    video_checkbox = request.form.get("video_checkbox")
    audio_checkbox = request.form.get("audio_checkbox")
    if custom_resolution == "yes":
        video_resolution = request.form.get("video_resolution")
        if not video_resolution:
            return "No resolution set"
        video_resolution_command = 'bv[height<=' + video_resolution + ']+ba' #TODO: Dynamisch mit worst audio, audio wird aber separat in zweitem download herunter geladen
        save("video_resolution", video_resolution)
        #save("video_resolution_command", video_resolution_command)
        save("custom_resolution_checkbox", True)
        #video_resolution = video_resolution_command
        video_quality = False
        audio_quality = False
    else:
        video_quality = request.form.get("video_quality")

        video_quality, audio_quality = convert_text_to_command(video_quality, video_checkbox, audio_checkbox)
        print("Audio Quality: " + audio_quality)
        save("custom_resolution_checkbox", False)

        #video_resolution = video_quality + "+" + audio_quality
        video_resolution = False
        if video_quality:
            save("video_quality", video_quality)
        logging.debug(f"Saving video_quality = {video_quality!r} (type={type(video_quality)})")

    if video_checkbox == "yes":
        save("video_checkbox", True)
    else:
        save("video_checkbox", False)

    if audio_checkbox == "yes":
        save("audio_checkbox", True)
    else:
        save("audio_checkbox", False)

    video_container = request.form.get("video_container")
    if not video_container == "mp3":
        save("video_container", video_container)
    video_url = request.form.get("video_url")

    found = next((v for v in global_variables.video_data if v["video_url"] == video_url), None)

    if found:
        console("Video already in Queue.")
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
        logging.basicConfig(filename="debug.log", level=logging.DEBUG)
        logging.debug(global_variables.video_data)
        logging.debug(f"Saving video_quality = {video_quality!r} (type={type(video_quality)})")

        if not global_variables.is_downloading:
            print("start")
            start_download()
    return redirect(url_for("home"))

def start_download():
    global download_thread
    if not download_thread:
        download_thread = True
        socketio.start_background_task(download)

def download():
    console("Preparing download")
    try:
        while True:  # Endlosschleife, solange es noch Videos gibt
            if not global_variables.video_data:
                break  # Queue leer → beenden
            global_variables.is_downloading = True
            current_video = global_variables.video_data.pop(0)

            video_task = "pending"
            audio_task = "pending"
            merge_task = "pending"
            global_variables.task_list = create_task_list(current_video, video_task, audio_task, merge_task)
            update_tasks()

            emit_queue()
            logging.basicConfig(filename="debug.log", level=logging.DEBUG)
            logging.debug(global_variables.video_data)

            socketio.emit('video_list', {
                "queue": global_variables.video_data,
                "current": current_video
            })

            video_url = current_video["video_url"]
            video_resolution = current_video["video_resolution"]
            video_container = current_video["video_container"]
            video_quality = current_video["video_quality"]
            audio_quality = current_video["audio_quality"]
            custom_resolution = current_video["custom_resolution_checkbox"]
            video_checkbox = current_video["video_checkbox"]
            audio_checkbox = current_video["audio_checkbox"]

            if video_url:
                socketio.emit('progress', {
                    'message': '⏳ Download processing...'
                })

                download_folder = read("download_folder")
                if not os.path.exists(download_folder):
                    return "Not valid folder"

                if custom_resolution == "yes":
                    if video_checkbox and not audio_checkbox:
                        video_input = 'bv[height<=' + video_resolution + ']/best'
                    elif video_checkbox and audio_checkbox:
                        video_input = 'bv[height<=' + video_resolution + ']'
                        audio_input = 'ba[height<=' + video_resolution + ']/best' # TODO: Fallback dynamisch machen
                    elif not video_checkbox and audio_checkbox:
                        #audio_input = 'ba[height<=' + video_resolution + ']'
                        audio_input = 'bestaudio'
                    else:
                        console("[Error] No stream selected.")
                else:
                    if video_checkbox and not audio_checkbox:
                        video_input = video_quality
                    elif video_checkbox and audio_checkbox:
                        video_input = video_quality
                        audio_input = audio_quality
                    elif not video_checkbox and audio_checkbox:
                        audio_input = audio_quality
                    else:
                        console("[Error] No stream selected.")
                try:
                    if video_checkbox:
                        video_task = "working"
                        global_variables.task_list = create_task_list(current_video, video_task, audio_task, merge_task)
                        update_tasks()
                        global_variables.download_type = "video"
                        console(f"[{global_variables.download_type}] Preparing to download {global_variables.download_type}.")

                        video_file = download_video(video_input, download_folder, video_url)

                        global_variables.state_logger = True # So that logger knows, when new video starts, helps to display "Download" only once per video
                        console(f"[{global_variables.download_type}]Done downloading {global_variables.download_type}.")
                        video_task = "done"
                        global_variables.task_list = create_task_list(current_video, video_task, audio_task, merge_task)
                        update_tasks()

                    if audio_checkbox:
                        audio_task = "working"
                        global_variables.task_list = create_task_list(current_video, video_task, audio_task, merge_task)
                        update_tasks()

                        global_variables.download_type = "audio"
                        console(f"[{global_variables.download_type}] Preparing to download {global_variables.download_type}.")

                        audio_file = download_audio(audio_input, download_folder, video_url)

                        global_variables.state_logger = True # So that logger knows, when new video starts, helps to display "Download" only once per video
                        console(f"[{global_variables.download_type}]Done downloading {global_variables.download_type}.")
                        audio_task = "done"
                        global_variables.task_list = create_task_list(current_video, video_task, audio_task, merge_task)
                        update_tasks()

                    file_data = read("file")
                    merge = file_data["auto_merge"]
                    if video_checkbox and audio_checkbox and merge:
                        merge_task = "working"
                        global_variables.task_list = create_task_list(current_video, video_task, audio_task, merge_task)
                        update_tasks()
                        console("Merging video and audio stream.")
                        output_file = video_file + "_merged." + video_container
                        result = merging_video_audio(video_file, audio_file, output_file)
                        if result:
                            console("Merging successful.")
                            merge_task = "done"
                            global_variables.task_list = create_task_list(current_video, video_task, audio_task, merge_task)
                            update_tasks()
                            os.remove(video_file)
                            os.remove(audio_file)
                        else:
                            print("Merging failed. Downloaded video and audio are still storaged in your download folder.")
                            console("Merging failed. Downloaded video and audio are still storaged in your download folder.")

                    elif not video_checkbox and audio_checkbox and video_container == "mp3": # Exception for mp3 Format, so you can download for example music as a mp3 file
                        console("Convert audio in mp3...")
                        output_file = audio_file + "_merged." + video_container
                        result = convert_audio_to_mp3(audio_file, output_file)
                        if result:
                            console("Merging successful.")
                            os.remove(audio_file)
                        else:
                            print(
                                "Merging failed. Downloaded video and audio are still storaged in your download folder.")
                            console(
                                "Merging failed. Downloaded video and audio are still storaged in your download folder.")

                    progress("finished", False, False, False)

                except Exception as e:
                    print("Download failed:", e)
    finally:
        download_thread = False
        global_variables.is_downloading = False

@app.route('/abort', methods=["GET", "POST"])
def abort():
    global_variables.abort_flag = True
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
        socketio.run(app, host="0.0.0.0", port=5000, debug=True)
    elif result == "restart":
        print("Please restart this python script and the whole command line.")
    else:
        print("Error. Either ffmpeg is not installed or not entered in the system environment variables.")

# TODO: Sinnlose prints löschen
# TODO: README.MD aktualisieren wegen Qualitätseinstellungen und yt-dlp Library aktuell halte + automatischer Update und ffmpeg installieren