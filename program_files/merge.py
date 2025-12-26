import subprocess
from program_files.outsourced_functions import send_status, read
from program_files.logger import logger
from program_files.merge_functions import get_frame_count_estimate, gpu_acceleration_cmd, get_va_codecs, choose_merging_option


def merging_video_audio(video_file, audio_file, output_file, gpu_acceleration):
    source = "python"
    send_status("console", ["Initiating merging of video and audio stream...", source])
    logger.info("Initiating merging of video and audio stream...")

    video_codec, audio_codec = get_va_codecs(source, video_file, audio_file) # Gets video and audio codec

    video_option, audio_option = choose_merging_option(source, video_file, video_codec, audio_codec, output_file)

    total_frames = get_frame_count_estimate(video_file)
    logger.info(f"Total frames: {total_frames}")
    try:
        total_frames = int(total_frames)
    except (ValueError, TypeError):
        total_frames = 0  # oder ein Fallback, wenn du es gar nicht bestimmen kannst
    if gpu_acceleration:
        decoder, video_option = gpu_acceleration_cmd()
        cmd = [
            "ffmpeg", "-y",
            *decoder,
            "-i", video_file,
            "-i", audio_file,
            "-c:v", video_option,
            "-c:a", audio_option,
            "-movflags", "faststart",
            "-progress", "pipe:1",  # FFmpeg writes progress to stdout
            "-nostats",  # supress logs in console
            output_file
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_file,
            "-i", audio_file,
            "-c:v", video_option,
            "-c:a", audio_option,
            "-movflags", "faststart",
            "-progress", "pipe:1",  # FFmpeg writes progress to stdout
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
    logger.info("Convert audio to mp3.")
    logger.info(f"Input file: {input_file}, output_file: {output_file}")
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