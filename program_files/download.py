import yt_dlp
import os
import subprocess
import sys
import json
import argparse
import program_files.globals as global_variables

parser = argparse.ArgumentParser()
parser.add_argument("--project-dir", default=None)
args, _ = parser.parse_known_args()

if args.project_dir:
    global_variables.project_dir = args.project_dir

from program_files.logger import logger
from program_files.outsourced_functions import send_status, read
import program_files.safe_shutil as shutil
from program_files.download_functions import progress_hook, Logger
from program_files.merge import merging_video_audio, convert_audio_to_mp3
import program_files.download_merge_globals as download_merge_globals
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Ordner, wo die aktuelle Datei liegt
userdata_file = os.path.join(BASE_DIR, "..", "userdata.json")

def download_video(video_input, download_folder, video_url):
    ydl_opts_video = {
        'format': video_input,
        'outtmpl': os.path.join(download_folder, '%(title)s_video.%(ext)s'),
        'progress_hooks': [progress_hook],
        'no_color': True, # Suppresses coloured output, as otherwise the numbers cannot be displayed correctly in the browser
        'restrictfilenames': True,
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
        'no_color': True, # Suppresses coloured output, as otherwise the numbers cannot be displayed correctly in the browser
        'restrictfilenames': True,
        'logger': Logger()
    }

    with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
        info_audio = ydl.extract_info(video_url, download=True)
        audio_file = ydl.prepare_filename(info_audio)
    return audio_file

def create_download_commands(custom_resolution, video_resolution, video_quality, video_checkbox, audio_quality, audio_checkbox, source, ):
    video_input = ""
    audio_input = ""
    if custom_resolution == "yes":
        filename_addition = video_resolution
        if video_checkbox and not audio_checkbox:
            video_input = 'bv[height<=' + video_resolution + ']/best'
        elif video_checkbox and audio_checkbox:
            video_input = 'bv[height<=' + video_resolution + ']'
            audio_input = 'bestaudio'
        elif not video_checkbox and audio_checkbox:
            # audio_input = 'ba[height<=' + video_resolution + ']'
            audio_input = 'bestaudio'
        else:
            send_status("console", ["No stream selected.", source])
    else:
        if video_checkbox and not audio_checkbox:
            video_input = video_quality
            logger.info(f"Video input: {video_input}")
            if video_input == "best":
                logger.info("In if")
                filename_addition = "average"  # Because "best" corresponds to "average", best is the best available and already merged stream, while bestvideo is the best available unmerged video stream
            else:
                logger.info("In else")
                filename_addition = video_quality
        elif video_checkbox and audio_checkbox:
            video_input = video_quality
            audio_input = audio_quality

            logger.info(f"Video input: {video_input}")
            if video_input == "best":
                logger.info("In if")
                filename_addition = "average"  # Because "best" corresponds to "average", best is the best available and already merged stream, while bestvideo is the best available unmerged video stream
            else:
                logger.info("In else")
                filename_addition = video_quality
        elif not video_checkbox and audio_checkbox:
            audio_input = audio_quality

            filename_addition = audio_quality
        else:
            send_status("console", ["No stream selected.", source])
            return
    return video_input, audio_input, filename_addition

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

def download():
    source = "python"
    send_status("console", ["Preparing download.", source])
    logger.info("Preparing download.")
    try:
        video_json = sys.argv[1]
        current_video = json.loads(video_json)

        video_task = "pending"
        audio_task = "pending"
        merge_task = "pending"

        send_status("task_list", [video_task, audio_task, merge_task])

        video_url = current_video["video_url"]
        video_resolution = current_video["video_resolution"]
        video_container = current_video["video_container"]
        video_quality = current_video["video_quality"]
        audio_quality = current_video["audio_quality"]
        custom_resolution = current_video["custom_resolution_checkbox"]
        video_checkbox = current_video["video_checkbox"]
        audio_checkbox = current_video["audio_checkbox"]

        file = read("file")
        program_data = file["program_data"]
        download_data = file["download_data"]
        download_folder = program_data["download_folder"]
        merge = download_data["auto_merge"]

        if video_url:
            send_status("progress", ["preparing", 0, 0, 0])

            if merge == "yes":
                download_tmp_folder = os.path.join("tmp", "va")
            else:
                download_tmp_folder = download_folder
            if not os.path.exists(download_tmp_folder):
                logger.info("va folder doesn't exists")
                return "va folder doesn't exists"

            # Create file name addition and download quality command for YouTube dlp
            video_input, audio_input, filename_addition = create_download_commands(custom_resolution, video_resolution, video_quality, video_checkbox, audio_quality, audio_checkbox, source)

            try:
                # Download video and audio
                if video_checkbox and video_input:
                    download_type = "video"
                    video_task = "working"
                    send_status("task_list", [video_task, audio_task, merge_task])
                    send_status("download_type", download_type)
                    send_status("console", [f"Preparing to download {download_type}.", source])

                    video_file = download_video(video_input, download_tmp_folder, video_url)
                    send_status("state_logger", True) # So that logger knows, when new video starts, helps to display "Download" only once per video
                    download_merge_globals.state_logger_download = True
                    download_merge_globals.state_logger_prepare = True
                    send_status("console", [f"Done downloading {download_type}.", source])
                    video_task = "done"
                    send_status("task_list", [video_task, audio_task, merge_task])

                if audio_checkbox and audio_input:
                    download_type = "audio"
                    audio_task = "working"
                    send_status("task_list", [video_task, audio_task, merge_task])

                    send_status("download_type", download_type)
                    send_status("console", [f"Preparing to download {download_type}.", source])

                    audio_file = download_audio(audio_input, download_tmp_folder, video_url)

                    send_status("state_logger",True)  # So that logger knows, when new video starts, helps to display "Download" only once per video
                    download_merge_globals.state_logger_download = True
                    download_merge_globals.state_logger_prepare = True
                    send_status("console", [f"Done downloading {download_type}.", source])
                    audio_task = "done"
                    send_status("task_list", [video_task, audio_task, merge_task])

                download_merge_globals.state_logger_download = False
                download_merge_globals.state_logger_prepare = False

                # Detect if merge is necessary and move files to the correct chosen download folder
                if (video_checkbox and video_input) and (audio_checkbox and audio_input) and merge == "yes": # Regular merge
                    merge_task = "working"
                    send_status("task_list", [video_task, audio_task, merge_task])

                    send_status("console", ["Merging video and audio stream.", source])
                    logger.info("Merging video and audio stream.")
                    output_file = os.path.join(download_folder, os.path.splitext(os.path.basename(video_file))[0] + "_" + filename_addition + "." + video_container) # Absolute path to download folder
                    result = merging_video_audio(video_file, audio_file, output_file)
                    if result:
                        send_status("console", ["Merging successful.", source])
                        logger.info("Merging successful.")
                        merge_task = "done"
                        send_status("task_list", [video_task, audio_task, merge_task])
                        shutil.rmtree(download_tmp_folder) # Remove old video and audio file after successful merge
                        os.makedirs(download_tmp_folder) # Create the tmp folder again for the next download
                    else:
                        print("Merging failed. Downloaded video and audio are still storaged in your download folder.")
                        send_status("console", ["Merging failed. Downloaded video and audio are still storaged in your download folder.", source])
                        logger.error("Merging failed. Downloaded video and audio are still storaged in your download folder.")
                        exception = True
                        shutil.move(video_file, download_folder, exception)
                        shutil.move(audio_file, download_folder, exception)
                elif not video_checkbox and audio_checkbox and video_container == "mp3": # Exception for mp3 Format, so you can download for example music as a mp3 file
                    merge_task = "working"
                    send_status("task_list", [video_task, audio_task, merge_task])

                    send_status("console", ["Convert audio in mp3...", source])
                    logger.info(f"Audio file:{audio_file}")
                    output_file = os.path.join(download_folder, os.path.splitext(os.path.basename(audio_file))[0] + "." + video_container) # Absolute path to download folder
                    result = convert_audio_to_mp3(audio_file, output_file)
                    if result:
                        print("In result.")
                        merge_task = "done"
                        send_status("task_list", [video_task, audio_task, merge_task])
                        send_status("console", ["Converting successful.", source])
                        #move_video_file(output_file, download_folder, "")
                        shutil.remove(audio_file)
                    else:
                        send_status("console",["Converting failed. Downloaded audio is still storaged in your download folder.", source])
                elif not video_container == "mp3": # Exception for non merged videostreams/audiostreams to move from tmp in chosen download folder
                    if not merge == "yes" and (video_checkbox and video_input) and (audio_checkbox and audio_input): # No merge, but video and audio
                        logger.info("1")
                        move_video_file(video_file, download_folder, filename_addition)
                        move_audio_file(audio_file, download_folder, filename_addition, video_file)
                    elif (video_checkbox and video_input) and (audio_checkbox and not audio_input): # Merge, but video and audio already merged
                        logger.info("2")
                        move_video_file(video_file, download_folder, filename_addition)
                    elif (video_checkbox and video_input) or (audio_checkbox and audio_input): # Merge, but either video or audio
                        logger.info("3")
                        if video_checkbox:
                            logger.info("3.1")
                            move_video_file(video_file, download_folder, filename_addition)
                        elif audio_checkbox:
                            logger.info("3.2")
                            move_audio_file(audio_file, download_folder, filename_addition)
                send_status("progress", ["finished", False, False, False])
                logger.info("Successfully downloaded video.")
                send_status("console", [f"Successfully downloaded video. Your video is now stored in {download_folder}.", source])
            except Exception as e:
                print("Download failed:", e)
                logger.error(f"Download failed: {e}")
    finally:
        download_thread = False

if __name__ == "__main__":
    download()
