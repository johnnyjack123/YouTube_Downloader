import yt_dlp
import json
import subprocess
import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Ordner, wo die aktuelle Datei liegt
userdata_file = os.path.join(BASE_DIR, "..", "userdata.json")

def sort_formats(video_url, video_resolution):
    # Check if quality is available
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl_extract:
        info_dict = ydl_extract.extract_info(video_url, download=False)
        formats_list = info_dict.get('formats', [])
        title = info_dict.get("title", "video")

    # Filter video formats
    video_formats = [f for f in formats_list if f.get('vcodec') != 'none']
    #resolutions = [(f["height"], f["format_id"]) for f in video_formats if f.get("height")]

    # Filter audio formats
    audio_formats = [f for f in formats_list if f.get('acodec') != 'none']

    # Sort videos by resolution (height)
    video_formats_sorted = sorted(video_formats, key=lambda f: f.get('height') or 0)

    # Sort audio by bitrate
    audio_formats_sorted = sorted(audio_formats, key=lambda f: f.get('abr') or 0)

    file = read("file")
    # Find the correct quality dependent on users choice
    if not file["checkbox"]:
        if video_resolution == "Best":
            # Best quality
            video_format = video_formats_sorted[-1]['format_id']
            audio_format = audio_formats_sorted[-1]['format_id']
        elif video_resolution == "Average":
            # Medium quality
            video_format = video_formats_sorted[len(video_formats_sorted) // 2]['format_id']
            audio_format = audio_formats_sorted[len(audio_formats_sorted) // 2]['format_id']
        elif video_resolution == "Worst":
            # Worst quality
            video_format = video_formats_sorted[0]['format_id']
            audio_format = audio_formats_sorted[0]['format_id']
        else:
            print("Quality preset not found.")

        print("Audio formats found:", [f['format_id'] for f in audio_formats_sorted])
        print("Video format: " + video_format)
        print("Audio format: " + audio_format)

        # Create command for yt-dlp
        if video_format and audio_format:
            video_resolution = f"{video_format}+{audio_format}"
        elif video_format:
            video_resolution = f"{video_format}"
        elif audio_format:
            video_resolution = f"{audio_format}"
        print("Video resolution: " + video_resolution)

def find_closest_resolution(video_height, video_formats):
    # Nur Formate mit definierter Höhe
    valid_formats = [f for f in video_formats if f.get("height")]
    # Sortieren nach Höhe
    valid_formats.sort(key=lambda f: f["height"])
    # Nächstgelegene finden
    closest = min(valid_formats, key=lambda f: abs(f["height"] - video_height))
    return closest["format_id"], closest["height"]

def merging_video_audio(video_file, audio_file, output_file):
    print("Merging")

    # --- Audio codec check ---
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_file
    ], capture_output=True, text=True)
    audio_codec = result.stdout.strip()

    # --- Video codec check ---
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_file
    ], capture_output=True, text=True)
    video_codec = result.stdout.strip()

    print(f"Audio codec detected: {audio_codec}")
    print(f"Video codec detected: {video_codec}")
    print("Start merging.")

    # --- Default: try copy ---
    audio_option = "copy" if audio_codec.lower() == "aac" else "aac"
    video_option = "copy"

    # --- Container compatibility check ---
    if output_file.lower().endswith(".mov"):
        # MOV cannot handle VP9 or AV1 reliably
        if video_codec.lower() in ["vp9", "av1"]:
            print(f"Video codec {video_codec} not supported in MOV, re-encoding to H.264")
            video_option = "libx264"
        if audio_codec.lower() != "aac":
            print(f"Audio codec {audio_codec} not supported in MOV, re-encoding to AAC")
            audio_option = "aac"

    result = subprocess.run([
        "ffmpeg", "-y",
        "-i", video_file,
        "-i", audio_file,
        "-c:v", video_option,
        "-c:a", audio_option,
        output_file
    ])

    if result.returncode == 0:
        print("Merging successful")
        return True
    else:
        print("Merging failed")
        return False

def convert_audio_to_mp3(input_file, output_file):
    print("Converting audio to MP3...")

    # --- Check codec ---
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_file
    ], capture_output=True, text=True)

    audio_codec = result.stdout.strip().lower()
    print(f"Detected audio codec: {audio_codec}")

    # --- Decide conversion method ---
    if audio_codec == "mp3":
        # Already MP3 → just copy
        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-c:a", "copy",
            output_file
        ]
        print("Audio is already MP3, using stream copy.")
    else:
        # Not MP3 → re-encode to MP3
        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-c:a", "libmp3lame",  # best MP3 encoder
            "-b:a", "192k",        # standard bitrate
            output_file
        ]
        print(f"Re-encoding audio ({audio_codec}) to MP3.")

    # --- Run conversion ---
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"Audio successfully saved as {output_file}")
        return True
    else:
        print("Audio conversion failed")
        return False

def save(entry, video_data):
    with open(userdata_file, "r", encoding="utf-8") as file:
        data = json.load(file)
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
        "auto_update": "yes"
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