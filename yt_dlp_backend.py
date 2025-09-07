import eventlet
eventlet.monkey_patch()
import yt_dlp
from flask import Flask, request, render_template, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
import threading
import os
import json
import webbrowser
import logging
import subprocess
import sys
from outsourced_functions import save, read, merging_video_audio, convert_audio_to_mp3
from datetime import datetime, timedelta

download_thread = False
abort_flag = False

is_downloading = False
video_data = []

state = True

state_logger = True
download_type = ""

get_video_name_thread = False

quality_map = {
    "bestvideo": "Best",
    "best": "Average",
    "worstvideo": "Worst"
}

video_quality_cmd = list(quality_map.keys())

console_socket = []

video_queue = []

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
    emit_queue()

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

    video_quality.remove(deafult_video_quality)
    video_quality.insert(0, deafult_video_quality)
    video_quality = convert_command_to_text(video_quality)

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

    found = next((v for v in video_data if v["video_url"] == video_url), None)

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
            "audio_checkbox": audio_checkbox
        }

        video_data.append(entry)
        start_get_name(video_url)
        emit_queue()
        logging.basicConfig(filename="debug.log", level=logging.DEBUG)
        logging.debug(video_data)
        logging.debug(f"Saving video_quality = {video_quality!r} (type={type(video_quality)})")

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
    global download_thread, abort_flag, is_downloading, video_data, state, state_logger, download_type

    #abort_flag = False
    #print("download")
    console("Preparing download")
    try:
        while True:  # Endlosschleife, solange es noch Videos gibt
            if not video_data:
                break  # Queue leer → beenden
            is_downloading = True
            current_video = video_data.pop(0)
            emit_queue()
            logging.basicConfig(filename="debug.log", level=logging.DEBUG)
            logging.debug(video_data)

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
                        download_type = "video"
                        ydl_opts_video = {
                            'format': video_input,
                            'outtmpl': os.path.join(download_folder, '%(title)s_video.%(ext)s'),
                            'progress_hooks': [progress_hook],
                            'no_color': True, # Suppresses coloured output, as otherwise the numbers cannot be displayed correctly in the browser
                            'logger': Logger()
                        }

                        with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
                            info_video = ydl.extract_info(video_url, download=True)
                            video_file = ydl.prepare_filename(info_video)  # returns the absolute path of the video file

                    state_logger = True # So that logger knows, when new video starts, helps to display "Download" only once per video

                    if audio_checkbox:
                        download_type = "audio"
                        ydl_opts_audio = {
                            'format': audio_input,
                            'outtmpl': os.path.join(download_folder, '%(title)s_audio.%(ext)s'),
                            'progress_hooks': [progress_hook],
                            'no_color': True, # Suppresses coloured output, as otherwise the numbers cannot be displayed correctly in the browser
                            #'logger': Logger()
                        }

                        with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
                            info_audio = ydl.extract_info(video_url, download=True)
                            audio_file = ydl.prepare_filename(info_audio)

                        state_logger = True # So that logger knows, when new video starts, helps to display "Download" only once per video
                        console("Done downloading. Processing.")

                    if video_checkbox and audio_checkbox:
                        console("Merging...")
                        output_file = video_file + "_merged." + video_container
                        result = merging_video_audio(video_file, audio_file, output_file)
                        if result:
                            console("Merging successful.")
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
        console("Download aborted")
        raise yt_dlp.utils.DownloadError("Abort Download!")

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
            'message': '✅ Finished Download!'})
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
            if not video_checkbox == "yes" and audio_checkbox == "yes":
                cmd_audio = "bestaudio/best"
            else:
                cmd_audio = False  # "Average" = nur Video
        elif description == "Worst":
            cmd_audio = "worstaudio/worst"
    return cmd_video, cmd_audio

class Logger:
    def debug(self, msg):
        global is_downloading, state_logger, download_type
        if msg.startswith("[info] Testing format"):
            command = "[yt-dlp]: Testing formats"
            console(command)
        elif msg.startswith("[download]"):
            if is_downloading:
                if state_logger:
                    command = "[" + download_type + "] Downloading..."
                    state_logger = False
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

def console(command):
    global console_socket
    if command == "Client connected":
        if "Client connected" in console_socket:
            return
    elif command == "[yt-dlp]: Testing formats":
        if "[yt-dlp]: Testing formats" in console_socket:
            return
    socketio.emit("console", command)
    socketio.sleep(0)
    console_socket.append(command)
    return

def emit_queue():
    # Take names of videos
    queue_names = [video["video_name"] for video in video_data]
    socketio.emit("queue", queue_names)
    socketio.sleep(0)

def open_browser():
    url = "http://127.0.0.1:5000"
    webbrowser.open(url)
    return

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

def update_title_in_queue(title, video_url):
    if video_data:
        if title:
            video = next((v for v in video_data if v["video_url"] == video_url), None)
            if video:
                video["video_name"] = title
                emit_queue()

def get_name(video_url):
    with yt_dlp.YoutubeDL({}) as ydl:
        video_metadata = ydl.extract_info(video_url, download=False)
        print("Titel:", video_metadata['title'])
        update_title_in_queue(video_metadata['title'], video_url)

def start_get_name(video_url):
    t = threading.Thread(target=get_name, args=(video_url,))
    t.start()


if __name__ == '__main__':
    update_yt_dlp()
    # open_browser()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

# TODO: Sinnlose prints löschen
# TODO: Only Audio/ Only Video Custom res und normal, normal worst, middle, best (testen, ob video und audio separat bei custom Download gehen)
# TODO: README.MD aktualisieren wegen Qualitätseinstellungen und yt-dlp Library aktuell halte + automatischer Update und ffmpeg installieren
# TODO: Bei merge Fortschrittsanzeige
# TODO: if only audio download, mp3 format
# TODO: test, ob ffmpeg installiert ist
# TODO: HOT: bei only audio & mp3 konvertieren