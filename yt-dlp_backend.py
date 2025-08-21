import eventlet
eventlet.monkey_patch()
import yt_dlp
from flask import Flask, request, render_template, redirect, url_for, jsonify
from flask_socketio import SocketIO
import threading
import os
import json
import webbrowser

download_thread = False
abort_flag = False

state = True

app = Flask(
    __name__,
    template_folder = "./templates",
    static_folder = "./static",
)

socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

@app.route('/', methods=["GET", "POST"])
def home():
    deafult_download_folder = os.path.join(os.path.expanduser("~"), "Videos")
    deafult_content = {
    "download_folder": deafult_download_folder,
    "video_quality": "best",
    "video_resolution": "1080",
    "video_resolution_command": "bv[height<=1080]+ba/best[height<=1080]",
    "video_container": "mp4",
    "checkbox": False
    }

    if not os.path.exists("userdata.json"):
        with open("userdata.json", "w", encoding="utf-8") as f:
            json.dump(deafult_content, f, indent=4, ensure_ascii=False)

    video_quality = ["best", "worst", "bestvideo", "bestaudio", "worstvideo", "worstaudio", "bestvideo+bestaudio/best"]
    video_resolution = ["720", "1080", "1920", "1440"]
    video_container = ["mp4", "mov", "mkv", "webm", "avi"]

    data = read("file")
    download_folder = data["download_folder"]

    deafult_video_quality = data["video_quality"]
    video_quality.remove(deafult_video_quality)
    video_quality.insert(0, deafult_video_quality)
    for x, cmd in enumerate(video_quality):
        description = convert_command_to_text(cmd)
        video_quality[x] = description

    deafult_video_resolution = data["video_resolution"]
    video_resolution.remove(deafult_video_resolution)
    video_resolution.insert(0, deafult_video_resolution)

    deafult_video_container = data["video_container"]
    video_container.remove(deafult_video_container)
    video_container.insert(0, deafult_video_container)

    checkbox = read("checkbox")
    return render_template('index.html',
                           download_folder=download_folder,
                           video_quality=video_quality,
                           video_resolution=video_resolution,
                           video_container=video_container,
                           checkbox=checkbox)

@app.route('/video_settings', methods=["GET", "POST"])
def video_settings():
    custom_resolution = request.form.get("custom_resolution")
    if custom_resolution == "yes":
        video_resolution = request.form.get("video_resolution")
        if not video_resolution:
            return "No resolution set"
        video_resolution_command = 'bv[height<=' + video_resolution + ']+ba/best[height<=' + video_resolution + ']'
        save("video_resolution", video_resolution)
        save("video_resolution_command", video_resolution_command)
        save("checkbox", True)
        video_data = video_resolution_command
    else:
        video_quality = request.form.get("video_quality")
        video_quality = convert_text_to_command(video_quality)
        save("video_quality", video_quality)
        save("checkbox", False)
        video_data = video_quality
    video_container = request.form.get("video_container")
    save("video_container", video_container)
    video_url = request.form.get("video_url")
    print("URL: " + video_url)
    start_download(video_url, video_data, video_container)
    return redirect(url_for("home"))

def start_download(video_url, video_data, video_container):
    global download_thread
    if not download_thread:
        download_thread = True
        socketio.start_background_task(download, video_url, video_data, video_container)


def download(video_url, video_data, video_container):
    global download_thread, abort_flag
    abort_flag = False
    if video_url:
        # Hier senden wir eine reine Statusnachricht ohne Fortschrittsdaten
        socketio.emit('progress', {
            'message': '⏳ Download processing...'
        })

        download_folder = read("download_folder")
        if not os.path.exists(download_folder):
            return "Not valid folder"

        # Den Pfad für den Download setzen
        ydl_opts = {
            'format': video_data,  # schlechteste Qualität, um Beispiel zu zeigen
            'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),
            'merge_output_format': video_container,
            'progress_hooks': [progress_hook],
            'no_color': True, # Suppresses coloured output, as otherwise the numbers cannot be displayed correctly in the browser
        }
        print(ydl_opts)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
        except yt_dlp.utils.DownloadError as e:
            print("Download aborted:", e)
        download_thread = False

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
    new_path = path.rsplit("\\", 1)[0]
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

def save(entry, video_data):
    with open("userdata.json", "r", encoding="utf-8") as file:
        data = json.load(file)
        data[entry] = video_data
    with open("userdata.json", "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    return

def read(entry):
    if entry == "file":
        with open("userdata.json", "r", encoding="utf-8") as file:
            data = json.load(file)
            return data
    elif entry:
        with open("userdata.json", "r", encoding="utf-8") as file:
            data = json.load(file)
            video_data = data[entry]
            return video_data

def convert_command_to_text(cmd):
    video_quality_cmd = ["best", "worst", "bestvideo", "bestaudio", "worstvideo", "worstaudio", "bestvideo+bestaudio/best"]

    video_quality = ["Best video and audio",
                     "Worst video and audio",
                     "Best video (video only)",
                     "Best audio (audio only)",
                     "Worst video (video only)",
                     "Worst audio (audio only)",
                     "Best video and best audio (seperated downloads, merged after download, provides in some cases better quality)"]
    index = video_quality_cmd.index(cmd)
    description = video_quality[index]
    return description

def convert_text_to_command(description):
    video_quality_cmd = ["best", "worst", "bestvideo", "bestaudio", "worstvideo", "worstaudio",
                         "bestvideo+bestaudio/best"]

    video_quality = ["Best video and audio",
                     "Worst video and audio",
                     "Best video (video only)",
                     "Best audio (audio only)",
                     "Worst video (video only)",
                     "Worst audio (audio only)",
                     "Best video and best audio (seperated downloads, merged after download, provides in some cases better quality)"]
    index = video_quality.index(description)
    cmd = video_quality_cmd[index]
    return cmd

def open_browser():
    url = "http://127.0.0.1:5000"
    webbrowser.open(url)
    return

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)


