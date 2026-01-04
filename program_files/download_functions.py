from program_files.outsourced_functions import send_status
import program_files.download_merge_globals as download_merge_globals
from program_files.logger import logger

def progress_hook(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0.0%').strip()
        speed = d.get('_speed_str', 'N/A')
        eta = d.get('_eta_str', 'N/A')
        send_status("progress", ["downloading", percent, speed, eta])

class Logger:
    def debug(self, msg):
        source = "yt-dlp"
        if msg.startswith("[info] Testing format"):
            command = "Testing formats"
            send_status("console", [command, source])
        elif msg.startswith("[download]"):
            if download_merge_globals.state_logger_download:
                    command = "Downloading..."
                    state_logger_download = False
                    send_status("console", [command, source])
            else:
                pass
        elif msg.startswith("[youtube]"):
            if download_merge_globals.state_logger_prepare:
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