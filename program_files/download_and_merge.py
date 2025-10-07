import yt_dlp
import os
import logging
import subprocess
import sys
import json

state_logger_download = False
state_logger_prepare = True
download_type = ""

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Ordner, wo die aktuelle Datei liegt
userdata_file = os.path.join(BASE_DIR, "..", "userdata.json")

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

def get_frame_count_estimate(video_file):
    # --- 1. Versuch: nb_frames direkt auslesen ---
    cmd_nb = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=nb_frames',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_file
    ]
    result_nb = subprocess.run(cmd_nb, capture_output=True, text=True)
    nb_frames_str = result_nb.stdout.strip()

    if nb_frames_str and nb_frames_str != "N/A":
        try:
            return int(nb_frames_str)
        except ValueError:
            pass  # Fallback

    # --- 2. Fallback: fps × duration ---
    cmd_fps = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=avg_frame_rate',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_file
    ]
    fps_str = subprocess.run(cmd_fps, capture_output=True, text=True).stdout.strip()

    cmd_dur = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_file
    ]
    duration_str = subprocess.run(cmd_dur, capture_output=True, text=True).stdout.strip()

    fps = 0.0
    if fps_str and fps_str != "N/A":
        try:
            if "/" in fps_str:
                num, den = map(int, fps_str.split('/'))
                if den != 0:
                    fps = num / den
            else:
                fps = float(fps_str)
        except Exception:
            fps = 0.0

    duration = 0.0
    if duration_str and duration_str != "N/A":
        try:
            duration = float(duration_str)
        except Exception:
            duration = 0.0

    if fps > 0 and duration > 0:
        return int(duration * fps)

    # --- Wenn gar nichts geht ---
    return 0



def send_status(function_name, function_args):
    cmd = json.dumps({"function": function_name, "args": function_args})
    print(cmd)
    return

def progress_hook(d):
    #if global_variables.abort_flag:
    #    console("Download aborted")
    #   raise yt_dlp.utils.DownloadError("Abort Download!")

    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0.0%').strip()
        speed = d.get('_speed_str', 'N/A')
        eta = d.get('_eta_str', 'N/A')
        send_status("progress", ["downloading", percent, speed, eta])

class Logger:
    def debug(self, msg):
        global state_logger_download, download_type, state_logger_prepare
        source = "yt-dlp"
        if msg.startswith("[info] Testing format"):
            command = "Testing formats"
            send_status("console", [command, source])
        elif msg.startswith("[download]"):
            if state_logger_download:
                    command = "Downloading..."
                    state_logger_download = False
                    send_status("console", [command, source])
            else:
                pass
        elif msg.startswith("[youtube]"):
            if state_logger_prepare:
                command = "Downloading resources."
                send_status("console", [command, source])
                state_logger_prepare = False
            else:
                pass
        else:
            command = msg
            send_status("console", [command, source])
    def warning(self, msg):
        print("WARN:", msg)
        send_status("console", [msg, "[yt-dlp warning]"])

    def error(self, msg):
        print("ERROR:", msg)
        send_status("console", [msg, "yt-dlp error"])



def merging_video_audio(video_file, audio_file, output_file):
    source = "python"
    send_status("console", ["Initiating merging of video and audio stream...", source])

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

    send_status("console", [f"Audio codec detected: {audio_codec}", source])
    send_status("console", [f"Video codec detected: {video_codec}", source])

    # --- Default: try copy ---
    audio_option = "copy" if audio_codec.lower() == "aac" else "aac"
    video_option = "copy"

    # --- Container compatibility check ---
    if output_file.lower().endswith(".mov"):
        # MOV cannot handle VP9 or AV1 reliably
        if video_codec.lower() in ["vp9", "av1"]:
            print(f"Video codec {video_codec} not supported in MOV, re-encoding to H.264")
            send_status("console", [f"Video codec {video_codec} not supported in MOV, re-encoding to H.264", source])
            video_option = "libx264"
        if audio_codec.lower() != "aac":
            send_status("console", [f"Audio codec {audio_codec} not supported in MOV, re-encoding to AAC", source])
            audio_option = "aac"

    total_frames = get_frame_count_estimate(video_file)
    print(f"DEBUG: total_frames={total_frames!r}")
    send_status("console", [f"Total frames: {total_frames}.", source])

    try:
        total_frames = int(total_frames)
    except (ValueError, TypeError):
        total_frames = 0  # oder ein Fallback, wenn du es gar nicht bestimmen kannst

    cmd = [
        "ffmpeg", "-y",
        "-i", video_file,
        "-i", audio_file,
        "-c:v", video_option,
        "-c:a", audio_option,
        "-progress", "pipe:1",  # ← FFmpeg writes progress to stdout
        "-nostats",  # supress logs in console
        output_file
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)

    send_status("console", ["Start merging...", source])

    for line in process.stdout:
        line = line.strip()
        if line.startswith("frame="):
            try:
                frame_value = line.split("=")[1].strip()
                if frame_value != "N/A":
                    current_frame = int(frame_value)
                    if total_frames > 0:
                        percent = round((current_frame / total_frames) * 100, 1)
                        send_status("progress", ["downloading", f"{percent}%", 0, 0])
            except Exception as e:
                print(f"Error in line={line!r}, total_frames={total_frames}: {e}")
                send_status("console", [f"Error in line={line!r}, total_frames={total_frames}: {e}", source])

    process.wait()
    if process.returncode != 0:
        print("\nMerging failed!")
        send_status("console", ["Merging failed", "ffmpeg"])
        return False
    else:
        print("\nMerging successful.")
        send_status("console", ["Merging successful", "ffmpeg"])
        return True


def convert_audio_to_mp3(input_file, output_file):
    source = "python"
    send_status("console", ["Converting audio to MP3...", source])

    # --- Check codec ---
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_file
    ], capture_output=True, text=True)

    audio_codec = result.stdout.strip().lower()
    send_status("console", [f"Detected audio codec: {audio_codec}", source])

    # --- Decide conversion method ---
    if audio_codec == "mp3":
        # Already MP3 → just copy
        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-c:a", "copy",
            output_file
        ]

        send_status("console", ["Audio is already MP3, using stream copy.", source])
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
        send_status("console", [f"Re-encoding audio ({audio_codec}) to MP3.", source])

    # --- Run conversion ---
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"Audio successfully saved as {output_file}")
        send_status("console", [f"Audio successfully saved as {output_file}", "ffmpeg"])
        return True
    else:
        print("Audio conversion failed")
        send_status("console", ["Audio conversion failed", "ffmpeg"])
        return False

def download_video(video_input, download_folder, video_url):
    ydl_opts_video = {
        'format': video_input,
        'outtmpl': os.path.join(download_folder, '%(title)s_video.%(ext)s'),
        'progress_hooks': [progress_hook],
        'no_color': True,
        # Suppresses coloured output, as otherwise the numbers cannot be displayed correctly in the browser
        'logger': Logger()
    }

    with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
        info_video = ydl.extract_info(video_url, download=True)
        video_file = ydl.prepare_filename(info_video)  # returns the absolute path of the video file
    return video_file

def download_audio(audio_input, download_folder, video_url):
    ydl_opts_audio = {
        'format': audio_input,
        'outtmpl': os.path.join(download_folder, '%(title)s_audio.%(ext)s'),
        'progress_hooks': [progress_hook],
        'no_color': True,
        # Suppresses coloured output, as otherwise the numbers cannot be displayed correctly in the browser
        'logger': Logger()
    }

    with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
        info_audio = ydl.extract_info(video_url, download=True)
        audio_file = ydl.prepare_filename(info_audio)
    return audio_file

def download():
    global state_logger_download, download_type, state_logger_prepare
    source = "python"
    send_status("console", ["Preparing download.", source])
    try:
        video_json = sys.argv[1]
        current_video = json.loads(video_json)

        video_task = "pending"
        audio_task = "pending"
        merge_task = "pending"

        send_status("task_list", [current_video, video_task, audio_task, merge_task])

        logging.basicConfig(filename="../debug.log", level=logging.DEBUG)
        logging.debug(current_video)

        video_url = current_video["video_url"]
        video_resolution = current_video["video_resolution"]
        video_container = current_video["video_container"]
        video_quality = current_video["video_quality"]
        audio_quality = current_video["audio_quality"]
        custom_resolution = current_video["custom_resolution_checkbox"]
        video_checkbox = current_video["video_checkbox"]
        audio_checkbox = current_video["audio_checkbox"]

        if video_url:
            send_status("progress", ["preparing", 0, 0, 0])

            download_folder = read("download_folder")
            if not os.path.exists(download_folder):
                return "Not valid folder"

            if custom_resolution == "yes":
                if video_checkbox and not audio_checkbox:
                    video_input = 'bv[height<=' + video_resolution + ']/best'
                elif video_checkbox and audio_checkbox:
                    video_input = 'bv[height<=' + video_resolution + ']'
                    audio_input = 'ba[height<=' + video_resolution + ']/best'
                elif not video_checkbox and audio_checkbox:
                    #audio_input = 'ba[height<=' + video_resolution + ']'
                    audio_input = 'bestaudio'
                else:

                    send_status("console", ["No stream selected.", source])
            else:
                if video_checkbox and not audio_checkbox:
                    video_input = video_quality
                elif video_checkbox and audio_checkbox:
                    video_input = video_quality
                    audio_input = audio_quality
                elif not video_checkbox and audio_checkbox:
                    audio_input = audio_quality
                else:
                    send_status("console", ["No stream selected.", source])
            try:
                if video_checkbox:
                    download_type = "video"
                    video_task = "working"
                    send_status("task_list", [current_video, video_task, audio_task, merge_task])
                    send_status("download_type", download_type)
                    send_status("console", [f"Preparing to download {download_type}.", source])

                    video_file = download_video(video_input, download_folder, video_url)

                    send_status("state_logger", True) # So that logger knows, when new video starts, helps to display "Download" only once per video
                    state_logger_download = True
                    state_logger_prepare = True
                    send_status("console", [f"Done downloading {download_type}.", source])
                    video_task = "done"
                    send_status("task_list", [current_video, video_task, audio_task, merge_task])

                if audio_checkbox:
                    download_type = "audio"
                    audio_task = "working"
                    send_status("task_list", [current_video, video_task, audio_task, merge_task])

                    send_status("download_type", download_type)
                    send_status("console", [f"Preparing to download {download_type}.", source])

                    audio_file = download_audio(audio_input, download_folder, video_url)

                    send_status("state_logger",True)  # So that logger knows, when new video starts, helps to display "Download" only once per video
                    state_logger_download = True
                    state_logger_prepare = True
                    send_status("console", [f"Done downloading {download_type}.", source])
                    audio_task = "done"
                    send_status("task_list", [current_video, video_task, audio_task, merge_task])

                file_data = read("file")
                state_logger_download = False
                state_logger_prepare = False
                merge = file_data["auto_merge"]
                if video_checkbox and audio_checkbox and merge:
                    merge_task = "working"
                    send_status("task_list", [current_video, video_task, audio_task, merge_task])

                    send_status("console", ["Merging video and audio stream.", source])
                    output_file = video_file + "_merged." + video_container
                    result = merging_video_audio(video_file, audio_file, output_file)
                    if result:
                        send_status("console", ["Merging successful.", source])
                        merge_task = "done"
                        send_status("task_list", [current_video, video_task, audio_task, merge_task])
                        os.remove(video_file)
                        os.remove(audio_file)
                    else:
                        print("Merging failed. Downloaded video and audio are still storaged in your download folder.")
                        send_status("console", ["Merging failed. Downloaded video and audio are still storaged in your download folder.", source])

                elif not video_checkbox and audio_checkbox and video_container == "mp3": # Exception for mp3 Format, so you can download for example music as a mp3 file
                    send_status("console", ["Convert audio in mp3...", source])
                    output_file = audio_file + "_merged." + video_container
                    result = convert_audio_to_mp3(audio_file, output_file)
                    if result:
                        send_status("console", ["Converting successful.", source])
                        os.remove(audio_file)
                    else:
                        send_status("console",["Converting failed. Downloaded audio is still storaged in your download folder.", source])
                send_status("progress", ["finished", False, False, False])

            except Exception as e:
                print("Download failed:", e)
    finally:
        download_thread = False

if __name__ == "__main__":
    download()