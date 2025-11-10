import os

video_queue = []
task_list = []
console_socket = []
is_downloading = False
state_logger = True
download_type = ""
abort_flag = False
current_video_data = {}
abort = False
project_dir = ""
userdata_file = os.path.join(project_dir, "..", "userdata.json")

quality_map = {
    "bestvideo": "Best",
    "best": "Average",
    "worstvideo": "Worst"
}

userdata = {
    "open_browser": "yes",
    "auto_update": "yes",
    "download_previous_queue": "yes",
    "force_h264": False
}

program_data = {
    "download_folder": os.path.join(os.path.expanduser("~"), "Videos"),
    "yt_dlp_update_time": "2025-09-06T17:40:36.348409",
    "video_queue": [],
    "update_branch": "master",
    "update_repo": "johnnyjack123/YouTube_Downloader"
}

download_data = {
    "video_quality": "best",
    "video_resolution": "1080",
    "video_resolution_command": "bv[height<=1080]+ba[height<=1080]",
    "video_container": "mp4",
    "custom_resolution_checkbox": False,
    "video_checkbox": True,
    "audio_checkbox": True,
    "auto_merge": "yes"

}