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
from program_files.download_functions import progress_hook, Logger, create_download_commands
from program_files.merge import initiate_merge
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
                result = initiate_merge(video_file, video_checkbox, video_input, video_container, audio_file, audio_checkbox,
                                        audio_input, merge, video_task, audio_task, download_folder, source, filename_addition,
                                        download_tmp_folder)
                if result == "Success":
                    send_status("progress", ["finished", False, False, False])
                    logger.info("Successfully downloaded video.")
                    send_status("console", [f"Successfully downloaded video. Your video is now stored in {download_folder}.", source])
                else:
                    raise RuntimeError(f"Download failed due to {result}")
            except Exception as e:
                print("Download failed:", e)
                logger.error(f"Download failed: {e}")
    finally:
        download_thread = False

if __name__ == "__main__":
    download()
