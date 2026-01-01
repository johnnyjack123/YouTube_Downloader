import subprocess
from program_files.outsourced_functions import send_status, read
import program_files.safe_shutil as shutil
import os

def get_va_codecs(source, video_file, audio_file):
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
    return video_codec, audio_codec

def choose_merging_option(source, video_file, video_codec, audio_codec, output_file): # Chooses, whether va will be just muxed or have to re-encode completely
    # --- Default: try copy ---
    audio_option = "copy" if audio_codec.lower() == "aac" else "aac"

    file = read("file")
    userdata = file["userdata"]
    if userdata["force_h264"]:
        is_mp4_container = video_file.lower().endswith(".mp4")

        if is_mp4_container and video_codec.lower() == "h264":
            send_status("console", ["MP4 with H.264 detected – muxing without re-encode.", source])
            video_option = "copy"  # Nur stream kopieren
        else:
            send_status("console", [f"Re-encoding video to H.264 (was: {video_codec})", source])
            video_option = "libx264"
    else:
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
    return video_option, audio_option

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

def gpu_acceleration_cmd():
    decoder = [
    "-hwaccel", "cuda",
    "-hwaccel_output_format", "cuda",
]
    video_option = "h264_nvenc"
    return decoder, video_option

def move_video_file(video_file, download_folder, filename_addition):
    file_name, video_container = os.path.splitext(os.path.basename(video_file))
    output_file = os.path.join(download_folder, file_name + "_" + filename_addition + video_container)
    folder = os.path.dirname(video_file)
    new_name = os.path.join(folder, file_name + "_" + filename_addition + video_container)
    shutil.rename(video_file, new_name)
    shutil.move(new_name, output_file, True)

def move_audio_file(audio_file, download_folder, filename_addition, video_file = ""):
    if video_file:
        file_name, audio_container = os.path.splitext(os.path.basename(audio_file))
        output_file = os.path.join(download_folder, file_name + "_" + filename_addition + audio_container)
        folder = os.path.dirname(audio_file)
        new_name = os.path.join(folder, file_name + "_" + filename_addition + audio_container)
        shutil.rename(video_file, new_name)
        shutil.move(new_name, output_file, True)
    else:
        file_name, audio_container = os.path.splitext(os.path.basename(audio_file))
        output_file = os.path.join(download_folder, file_name + audio_container)
        folder = os.path.dirname(audio_file)
        new_name = os.path.join(folder, file_name + audio_container)
        shutil.rename(audio_file, new_name)
        shutil.move(new_name, output_file, True)