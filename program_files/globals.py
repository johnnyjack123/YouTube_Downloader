video_queue = []
task_list = []
console_socket = []
is_downloading = False
state_logger = True
download_type = ""
abort_flag = False
current_video_data = {}
abort = False

quality_map = {
    "bestvideo": "Best",
    "best": "Average",
    "worstvideo": "Worst"
}