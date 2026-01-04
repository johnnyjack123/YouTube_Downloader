import subprocess
from program_files.outsourced_functions import send_status, read
from program_files.logger import logger
from program_files.merge_functions import get_frame_count_estimate, get_va_codecs, choose_merging_option, \
    move_video_file, move_audio_file, create_gpu_encode_command
import os
import program_files.safe_shutil as shutil
from program_files.outsourced_functions import get_gpu

def merging_video_audio(video_file, audio_file, output_file, gpu_acceleration):
    source = "python"
    send_status("console", ["Initiating merging of video and audio stream...", source])
    logger.info("Initiating merging of video and audio stream...")

    video_codec, audio_codec = get_va_codecs(source, video_file, audio_file) # Gets video and audio codec

    video_option, audio_option = choose_merging_option(source, video_file, video_codec, audio_codec, output_file)

    default_cmd = [
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

    total_frames = get_frame_count_estimate(video_file)
    logger.info(f"Total frames: {total_frames}")
    try:
        total_frames = int(total_frames)
    except (ValueError, TypeError):
        total_frames = 0  # oder ein Fallback, wenn du es gar nicht bestimmen kannst
    if gpu_acceleration:
        logger.info("GPU-Acceleration enabled")
        file = read("file")
        program_data = file["program_data"]
        platform, new_video_option, decoder = create_gpu_encode_command(program_data["gpu"][0])
        #decoder, new_video_option, platform = get_gpu()
        logger.info(f"Decoder: {decoder}, new_video_option: {new_video_option}, platform: {platform}")
        if decoder and video_option and platform:
            logger.info(f"GPU found, platform: {platform}")
            cmd = [
                "ffmpeg", "-y",
                *decoder,
                "-i", video_file,
                "-i", audio_file,
                "-c:v", new_video_option,
                "-c:a", audio_option,
                "-movflags", "faststart",
                "-progress", "pipe:1",  # FFmpeg writes progress to stdout
                "-nostats",  # supress logs in console
                output_file
            ]
            logger.info(f"ffmpeg command: {cmd}")
        else:
            cmd = default_cmd
    else:
        cmd = default_cmd

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

def initiate_merge(video_file, video_checkbox, video_input, video_container, audio_file, audio_checkbox, audio_input,
                   merge, video_task, audio_task, download_folder, source, filename_addition, download_tmp_folder):
    try:
        # Detect if merge is necessary and move files to the correct chosen download folder
        if (video_checkbox and video_input) and (audio_checkbox and audio_input) and merge == "yes":  # Regular merge
            merge_task = "working"
            send_status("task_list", [video_task, audio_task, merge_task])

            send_status("console", ["Merging video and audio stream.", source])
            logger.info("Merging video and audio stream.")
            output_file = os.path.join(download_folder, os.path.splitext(os.path.basename(video_file))[
                0] + "_" + filename_addition + "." + video_container)  # Absolute path to download folder
            file = read("file")
            gpu_acceleration = file["userdata"]["gpu_acceleration"]
            result = merging_video_audio(video_file, audio_file, output_file, gpu_acceleration)
            if result:
                send_status("console", ["Merging successful.", source])
                logger.info("Merging successful.")
                merge_task = "done"
                send_status("task_list", [video_task, audio_task, merge_task])
                shutil.rmtree(download_tmp_folder)  # Remove old video and audio file after successful merge
                os.makedirs(download_tmp_folder)  # Create the tmp folder again for the next download
            else:
                print("Merging failed. Downloaded video and audio are still storaged in your download folder.")
                send_status("console",
                            ["Merging failed. Downloaded video and audio are still storaged in your download folder.",
                             source])
                logger.error("Merging failed. Downloaded video and audio are still storaged in your download folder.")
                exception = True
                shutil.move(video_file, download_folder, exception)
                shutil.move(audio_file, download_folder, exception)
        elif not video_checkbox and audio_checkbox and video_container == "mp3":  # Exception for mp3 Format, so you can download for example music as a mp3 file
            merge_task = "working"
            send_status("task_list", [video_task, audio_task, merge_task])

            send_status("console", ["Convert audio in mp3...", source])
            logger.info(f"Audio file:{audio_file}")
            output_file = os.path.join(download_folder, os.path.splitext(os.path.basename(audio_file))[
                0] + "." + video_container)  # Absolute path to download folder
            result = convert_audio_to_mp3(audio_file, output_file)
            if result:
                print("In result.")
                merge_task = "done"
                send_status("task_list", [video_task, audio_task, merge_task])
                send_status("console", ["Converting successful.", source])
                # move_video_file(output_file, download_folder, "")
                shutil.remove(audio_file)
            else:
                send_status("console",
                            ["Converting failed. Downloaded audio is still storaged in your download folder.", source])
        elif not video_container == "mp3":  # Exception for non merged videostreams/audiostreams to move from tmp in chosen download folder
            if not merge == "yes" and (video_checkbox and video_input) and (
                    audio_checkbox and audio_input):  # No merge, but video and audio
                logger.info("1")
                move_video_file(video_file, download_folder, filename_addition)
                move_audio_file(audio_file, download_folder, filename_addition, video_file)
            elif (video_checkbox and video_input) and (
                    audio_checkbox and not audio_input):  # Merge, but video and audio already merged
                logger.info("2")
                move_video_file(video_file, download_folder, filename_addition)
            elif (video_checkbox and video_input) or (audio_checkbox and audio_input):  # Merge, but either video or audio
                logger.info("3")
                if video_checkbox:
                    logger.info("3.1")
                    move_video_file(video_file, download_folder, filename_addition)
                elif audio_checkbox:
                    logger.info("3.2")
                    move_audio_file(audio_file, download_folder, filename_addition)
        return "Success"
    except Exception as e:
        return f"Error in initiate_merge: {e}"