import yt_dlp
import json
import subprocess
import os

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

def merging_video_audio(video_url, video_format, audio_format, download_folder, progress_hook):
    # There are sometimes problems with the merging of files. If updating yt-dlp dont help there is a
    # code snipped to do the merging both video clips manually with ffmpeg.



    print("Merging")
    subprocess.run([
        'ffmpeg', '-y',
        '-i', video_file,
        '-i', audio_file,
        '-c', 'copy',  # Re-Encoding vermeiden
        output_file
    ])


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
