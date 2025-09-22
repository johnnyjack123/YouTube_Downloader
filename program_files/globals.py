video_data = []
task_list = []
console_socket = []
is_downloading = False
state_logger = True
download_type = ""
abort_flag = False
current_video_url = ""
current_name = ""

quality_map = {
    "bestvideo": "Best",
    "best": "Average",
    "worstvideo": "Worst"
}