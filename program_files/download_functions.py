from program_files.outsourced_functions import send_status
import program_files.download_merge_globals as download_merge_globals

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

