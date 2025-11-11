from flask import Flask, request, render_template, redirect, url_for
from flask_socketio import SocketIO
import os
import argparse
import program_files.globals as global_variables

parser = argparse.ArgumentParser()
parser.add_argument("--project-dir", default=None)
args, _ = parser.parse_known_args()

if args.project_dir:
    global_variables.project_dir = args.project_dir

from program_files.outsourced_functions import (save, read,
                                                check_for_userdata, ensure_ffmpeg, open_browser, convert_command_to_text,
                                                convert_text_to_command, search_download_folder, start_download, abort_download,
                                                check_for_queue, check_for_update_launcher)
from program_files.yt_dlp_functions import update_yt_dlp, start_get_name
from program_files.sockets import cancel_button



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
from program_files.sockets import console, emit_queue
sockets.init_socket(socketio)

@app.route('/', methods=["GET", "POST"])
def home():
    video_quality = ["bestvideo", "best", "worstvideo"]
    video_resolution = ["720", "1080", "1440", "1920", "2160"]
    video_container = ["mp4", "mov", "mkv", "webm", "avi"]

    data = read("file")
    program_data = data["program_data"]
    download_data = data["download_data"]
    download_folder = program_data["download_folder"]

    default_video_quality = download_data["video_quality"]
    video_quality.remove(default_video_quality)
    video_quality.insert(0, default_video_quality)
    video_quality = convert_command_to_text(video_quality)

    default_video_resolution = download_data["video_resolution"]
    video_resolution.remove(default_video_resolution)
    video_resolution.insert(0, default_video_resolution)

    default_video_container = download_data["video_container"]
    if default_video_container == "mp3":
        video_container.insert(0, "mp3")
    else:
        video_container.remove(default_video_container)
        video_container.insert(0, default_video_container)

    checkbox = download_data["custom_resolution_checkbox"]
    video_checkbox = download_data["video_checkbox"]
    audio_checkbox = download_data["audio_checkbox"]

    return render_template('index.html',
                           download_folder=download_folder,
                           video_quality=video_quality,
                           video_resolution=video_resolution,
                           video_container=video_container,
                           checkbox=checkbox,
                           console_socket=global_variables.console_socket,
                           video_checkbox=video_checkbox,
                           audio_checkbox=audio_checkbox,
                           abort=global_variables.abort)

@app.route('/video_settings', methods=["GET", "POST"])
def video_settings():
    global_variables.abort = False
    custom_resolution = request.form.get("custom_resolution")
    video_checkbox = request.form.get("video_checkbox")
    audio_checkbox = request.form.get("audio_checkbox")
    file = read("file")
    download_data = file["download_data"]
    program_data = file["program_data"]
    if custom_resolution == "yes":
        video_resolution = request.form.get("video_resolution")
        if not video_resolution:
            return "No resolution set"
        download_data["video_resolution"] = video_resolution
        download_data["custom_resolution_checkbox"] = True
        video_quality = False
        audio_quality = False
    else:
        video_quality = request.form.get("video_quality")
        print(f"Video quality: {video_quality}")
        video_quality, audio_quality = convert_text_to_command(video_quality, video_checkbox, audio_checkbox)
        download_data["custom_resolution_checkbox"] = False

        video_resolution = False
        if video_quality:
            download_data["video_quality"] = video_quality

    if video_checkbox == "yes":
        download_data["video_checkbox"] = True
    else:
        download_data["video_checkbox"] = False

    if audio_checkbox == "yes":
        download_data["audio_checkbox"] = True
    else:
        download_data["audio_checkbox"] = False

    video_container = request.form.get("video_container")
    #if not video_container == "mp3":
    download_data["video_container"] = video_container
    video_url = request.form.get("video_url")
    file["download_data"] = download_data
    found = next((v for v in global_variables.video_queue if v["video_url"] == video_url), None)

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
        global_variables.video_queue.append(entry)
        program_data["video_queue"] = global_variables.video_queue
        file["program_data"] = program_data
        save("whole_file", file)

        start_get_name(video_url)
        emit_queue()
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
    file = read("file")
    program_data = file["program_data"]
    program_data["download_folder"] = request.args.get("path")
    file["program_data"] = program_data
    save("whole_file", file)
    return redirect(url_for("home"))

@app.route('/previous_folder', methods=["GET", "POST"])
def previous_folder():
    path = request.args.get("path")
    new_path = os.path.dirname(path) #
    return redirect(url_for("choose_download_folder_page", path=new_path))

@app.route('/settings_page', methods=["GET"])
def settings_page():
    data = read("file")
    userdata = data["userdata"]
    download_data = data["download_data"]

    open_browser_window = userdata["open_browser"]
    auto_update = userdata["auto_update"]
    auto_merge = download_data["auto_merge"]
    download_previous_queue = userdata["download_previous_queue"]
    force_h264 = userdata["force_h264"]

    return render_template('settings.html',
                           open_browser_window=open_browser_window,
                           auto_update=auto_update,
                           auto_merge=auto_merge,
                           download_previous_queue=download_previous_queue,
                           force_h264=force_h264)

@app.route('/settings', methods=["POST"])
def settings():
    data = read("file")
    userdata = data["userdata"]
    download_data = data["download_data"]

    open_browser_window = request.form.get("open_browser_window")
    userdata["open_browser"] = open_browser_window

    auto_update = request.form.get("auto_update")
    userdata["auto_update"] = auto_update

    auto_merge = request.form.get("auto_merge")
    download_data["auto_merge"] = auto_merge

    download_previous_queue = request.form.get("download_previous_queue")
    userdata["download_previous_queue"] = download_previous_queue

    force_h264 = request.form.get("force_h264")
    userdata["force_h264"] = force_h264

    data["userdata"] = userdata
    data["download_data"] = download_data

    save("whole_file", data)
    return redirect(url_for("settings_page"))

@app.route('/abort', methods=["GET", "POST"])
def abort():
    global_variables.abort = True
    console("Pause download.", "python")
    abort_download()
    global_variables.is_downloading = False
    cancel_button()
    return redirect(url_for("home"))

@app.route('/resume_download', methods=["GET"])
def resume_download():
    global_variables.abort = False
    console("Resuming download.", "python")
    return redirect(url_for("home"))

@app.route('/cancel_download', methods=["GET"])
def cancel_download():
    global_variables.abort = False
    global_variables.video_queue = []
    file = read("file")
    program_data = file["program_data"]
    program_data["video_queue"] = []
    file["program_data"] = program_data
    save("whole_file", file)
    console("Aborted download", "python")
    return redirect(url_for("home"))

if __name__ == '__main__':
    check_for_update_launcher()
    result = ensure_ffmpeg()
    if result == "run":
        check_for_userdata()
        data = read("file")
        userdata = data["userdata"]
        if userdata["open_browser"] == "yes":
            open_browser()
        update_yt_dlp()
        check_for_queue()
        start_download()
        socketio.run(app, host="0.0.0.0", port=5000, debug=False)

    elif result == "restart":
        print("Please restart this python script and the whole command line.")
    else:
        print("Error. Either ffmpeg is not installed or not entered in the system environment variables.")
