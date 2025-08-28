import eventlet
eventlet.monkey_patch()
import yt_dlp
from flask import Flask, request, render_template, redirect, url_for, jsonify
from flask_socketio import SocketIO
import threading
import os
import json
import webbrowser
import logging
import subprocess
import sys
from outsourced_functions import sort_formats, save, read, merging_video_audio
from pathlib import Path

download_thread = False
abort_flag = False

is_downloading = False
video_data = []

state = True

quality_map = {
    "bestvideo": "Best",
    "best": "Average",
    "worstvideo": "Worst"
}

video_quality_cmd = list(quality_map.keys())

console_socket = []

app = Flask(
    __name__,
    template_folder = "./templates",
    static_folder = "./static",
)

socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

@socketio.on("connect")
def handle_connect():
    # TODO: Console in Array, Array wird immer bei reload mitgeschickt
    print("Client connected")
    console("Client connected")
    #socketio.emit("console", "Client connected")

@app.route('/', methods=["GET", "POST"])
def home():
    global video_quality_cmd
    deafult_download_folder = os.path.join(os.path.expanduser("~"), "Videos")

    deafult_content = {
        "download_folder": deafult_download_folder,
        "video_quality": "best",
        "video_resolution": "1080",
        "video_resolution_command": "bv[height<=1080]+ba[height<=1080]",
        "video_container": "mp4",
        "checkbox": False,
        "video_checkbox": True,
        "audio_checkbox": True
        }

    if not os.path.exists("userdata.json"):
        with open("userdata.json", "w", encoding="utf-8") as f:
            json.dump(deafult_content, f, indent=4, ensure_ascii=False)

    video_quality = ["bestvideo", "best", "worstvideo"]
    video_resolution = ["720", "1080", "1920", "1440", "2160"]
    video_container = ["mp4", "mov", "mkv", "webm", "avi"]

    data = read("file")
    download_folder = data["download_folder"]

    deafult_video_quality = data["video_quality"]

    #if deafult_video_quality in video_quality:
    video_quality.remove(deafult_video_quality)
    video_quality.insert(0, deafult_video_quality)
    video_quality = convert_command_to_text(video_quality)
        # Erzeuge neue video_quality-Liste basierend auf quality_map
    #video_quality = [quality_map[cmd] for cmd in video_quality_cmd]

    deafult_video_resolution = data["video_resolution"]
    video_resolution.remove(deafult_video_resolution)
    video_resolution.insert(0, deafult_video_resolution)

    deafult_video_container = data["video_container"]
    video_container.remove(deafult_video_container)
    video_container.insert(0, deafult_video_container)

    checkbox = read("custom_resolution_checkbox")
    video_checkbox = read("video_checkbox")
    audio_checkbox = read("audio_checkbox")

    return render_template('index.html',
                           download_folder=download_folder,
                           video_quality=video_quality,
                           video_resolution=video_resolution,
                           video_container=video_container,
                           checkbox=checkbox,
                           console_socket=console_socket,
                           video_checkbox=video_checkbox,
                           audio_checkbox=audio_checkbox)

@app.route('/video_settings', methods=["GET", "POST"])
def video_settings():
    global video_data, is_downloading
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

        save("custom_resolution_checkbox", False)

        #video_resolution = video_quality + "+" + audio_quality
        video_resolution = False
        save("video_quality", video_quality)

    if video_checkbox == "yes":
        save("video_checkbox", True)
    else:
        save("video_checkbox", False)

    if audio_checkbox == "yes":
        save("audio_checkbox", True)
    else:
        save("audio_checkbox", False)

    video_container = request.form.get("video_container")
    save("video_container", video_container)
    video_url = request.form.get("video_url")

    # TODO: In Thread auslagern
    #with yt_dlp.YoutubeDL({}) as ydl:
    #    video_metadata = ydl.extract_info(video_url, download=False)
    #    print("Titel:", video_metadata['title'])

    entry = {
        "video_url": video_url,
        "video_resolution": video_resolution,
        "custom_resolution_checkbox": custom_resolution,
        "video_quality": video_quality,
        "audio_quality": audio_quality,
        "video_container": video_container,
        "video_name": "Test", #video_metadata["title"]
        "video_checkbox": video_checkbox,
        "audio_checkbox": audio_checkbox
    }

    video_data.append(entry)

    socketio.emit('video_list', {
        "queue": video_data,
        "current": None  # hier gerade kein Wechsel, aktuelles Video bleibt unverändert
    })
    #print("Queue: " + str(video_data))
    #print("URL: " + video_url)
    logging.basicConfig(filename="debug.log", level=logging.DEBUG)
    logging.debug(video_data)
    if not is_downloading:
        print("start")
        start_download()
    return redirect(url_for("home"))

def start_download():
    global download_thread
    if not download_thread:
        download_thread = True
        socketio.start_background_task(download)

def download():
    global download_thread, abort_flag, is_downloading, video_data, state
    is_downloading = True
    #abort_flag = False
    #print("download")
    console("Preparing download")
    try:
        while True:  # Endlosschleife, solange es noch Videos gibt
            if not video_data:
                break  # Queue leer → beenden

            current_video = video_data.pop(0)

            socketio.emit('video_list', {
                "queue": video_data,
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

                """
                # Den Pfad für den Download setzen
                ydl_opts = {
                    'format': video_resolution,
                    'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),
                    'merge_output_format': None,
                    'progress_hooks': [progress_hook],
                    'no_color': True, # Suppresses coloured output, as otherwise the numbers cannot be displayed correctly in the browser
                    #'logger': Logger(),
                    #'noplaylist': True,
                    #'youtube_include_dash_manifest': True,  # erzwingt DASH-Include
                    #'geo_bypass': True,  # falls länderspezifische Sperre
                    #'youtube_skip_dash_manifest': False,
                }

                print(ydl_opts)
                """
                if custom_resolution == "yes":
                    pass
                else:
                    if video_quality:
                        video_input = video_quality
                        video = True
                    else:
                        video = False
                    if audio_quality:
                        audio_input = audio_quality
                        audio = True
                    else:
                        audio = False
                try:

                    if video:
                        ydl_opts_video = {
                            'format': video_input,
                            'outtmpl': os.path.join(download_folder, '%(title)s_video.%(ext)s'),
                            'progress_hooks': [progress_hook]
                        }

                        with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
                            info_video = ydl.extract_info(video_url, download=True)
                            video_file = ydl.prepare_filename(info_video)  # returns the absolute path of the video file

                    if audio:
                        ydl_opts_audio = {
                            'format': audio_input,
                            'outtmpl': os.path.join(download_folder, '%(title)s_audio.%(ext)s'),
                            'progress_hooks': [progress_hook]
                        }

                        with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
                            info_audio = ydl.extract_info(video_url, download=True)
                            audio_file = ydl.prepare_filename(info_audio)

                    if video and audio:
                        output_file = video_file + "_merged." + video_container
                        result = merging_video_audio(video_file, audio_file, output_file)

                        if result:
                            os.remove(video_file)
                            os.remove(audio_file)
                        else:
                            print("Merging failed. Downloaded video and audio are still storaged in your download folder")

                except yt_dlp.utils.DownloadError as e:
                    print("Download failed:", e)
    finally:
        download_thread = False
        is_downloading = False

@app.route('/abort', methods=["GET", "POST"])
def abort():
    global abort_flag
    abort_flag = True
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

def search_download_folder(folder, path):
    if folder:
        path = os.path.join(path, folder)
    else:
        path = path
    folders = [
        f for f in os.listdir(path)
        if os.path.isdir(os.path.join(path, f)) and not f.startswith(".")  # versteckte Unix-Ordner
    ]
    return folders, path

@app.route('/change_download_folder', methods=["GET", "POST"])
def change_download_folder():
    with open("userdata.json", "r", encoding="utf-8") as file:
        data = json.load(file)
        data["download_folder"] = request.args.get("path")
    with open("userdata.json", "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        return redirect(url_for("home"))


@app.route('/previous_folder', methods=["GET", "POST"])
def previous_folder():
    path = request.args.get("path")
    new_path = path.rsplit("\\", 1)[0] # TODO: mit os machen
    return redirect(url_for("choose_download_folder_page", path=new_path))

def progress_hook(d):
    global abort_flag

    if abort_flag:
        raise yt_dlp.utils.DownloadError("Download abgebrochen!")

    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0.0%').strip()
        speed = d.get('_speed_str', 'N/A')
        eta = d.get('_eta_str', 'N/A')

        # Sende Fortschritt an den Client
        socketio.emit('progress', {
            'percent': percent,
            'speed': speed,
            'eta': eta
        })
        socketio.sleep(0)
    elif d['status'] == 'finished':
        socketio.emit('progress', {
            'percent': '100%',
            'speed': '0',
            'eta': '0',
            'message': '✅ Download abgeschlossen!'})
        print("Download abgeschlossen, wird nun verarbeitet...")
        socketio.sleep(0)

def convert_command_to_text(cmd_list):
    text = []
    for entry in cmd_list:
        if entry in quality_map:
            text.append(quality_map[entry])
        else:
            text.append(entry)  # fallback: gib original zurück
    return text

def convert_text_to_command(description, video_checkbox, audio_checkbox):
    reverse_map = {v: k for k, v in quality_map.items()}

    cmd_video = False
    cmd_audio = False

    if video_checkbox == "yes":
        if description in reverse_map:
            cmd_video = reverse_map[description]

    if audio_checkbox == "yes":
        if description == "Best":
            cmd_audio = "bestaudio/best" #Not the best way, because by single video downloads there is noch fallback.
        elif description == "Average":
            cmd_audio = False  # "Average" = nur Video
        elif description == "Worst":
            cmd_audio = "worstaudio/worst"

    return cmd_video, cmd_audio

class Logger:
    def debug(self, msg):
        if msg.startswith("[info] Testing format"):
            command = "[yt-dlp]: Testing formats"
            print(command)
            console(command)
        else:
            command = "[yt-dlp]" + msg
            console(command)

    def warning(self, msg):
        print("WARN:", msg)
        console(msg)

    def error(self, msg):
        print("ERROR:", msg)
        console(msg)

def console(command):
    global console_socket
    if command == "Client connected":
        if "Client connected" in console_socket:
            return
    if command == "[yt-dlp]: Testing formats":
        if "[yt-dlp]: Testing formats" in console_socket:
            return
    socketio.emit("console", command)
    socketio.sleep(0)
    console_socket.append(command)
    return

def open_browser():
    url = "http://127.0.0.1:5000"
    webbrowser.open(url)
    return

def update_yt_dlp():
    subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])


if __name__ == '__main__':
    update_yt_dlp()
    #open_browser()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)


# TODO: QUEUE über query parameter an Website schicken, mit socket aktualisieren
# TODO: Fallback merger mit time out, eigenes ffmpeg wird angestoßen
# TODO: Sinnlose prints löschen
# TODO: Only Audio/ Only Video Custom res und normal, normal worst, middle, best
# TODO: REDME.MD aktualisieren wegen Qualitätseinstellungen und yt-dlp Library aktuell halte + automatischer Update und ffmpeg installieren
# TODO: Bei merge auf gewähltes Dateiformat eingehen
# TODO: Bei merge Fortschrittsanzeige
# TODO: yt-dlp update erst nach einem Tag wieder
