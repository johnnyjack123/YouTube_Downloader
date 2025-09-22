import program_files.globals as global_variables

socketio = None

def init_socket(socketio_instance):
    global socketio
    socketio = socketio_instance

    # Hier registrierst du die Events
    @socketio.on("connect")
    def handle_connect():
        #global task_list
        print("Client connected")
        console("Client connected", "python")
        emit_queue()
        update_tasks()
        update_current_video(global_variables.current_name)

def update_tasks():
    socketio.emit("update_tasks", global_variables.task_list)

def update_title_in_queue(title, video_url):
    if global_variables.video_data:
        if title:
            video = next((v for v in global_variables.video_data if v["video_url"] == video_url), None)
            if video:
                video["video_name"] = title
                emit_queue()

def update_current_video(title):
    socketio.emit("current_video", title)
    socketio.sleep(0)

def console(command, source):
    #global console_socket
    if command == "Client connected":
        if "Client connected" in global_variables.console_socket:
            return
    elif command == "[yt-dlp]: Testing formats":
        if "[yt-dlp]: Testing formats" in global_variables.console_socket:
            return
    print(f"[console] [{source}] {command}")
    socketio.emit("console", f"[{source}] {command}")
    socketio.sleep(0)
    global_variables.console_socket.append(f"[{source}] {command}")
    return

def emit_queue():
    # Take names of videos
    queue_names = [video["video_name"] for video in global_variables.video_data]
    socketio.emit("queue", queue_names)
    socketio.sleep(0)

def progress(status, percent, speed, eta):
    if status == "downloading":
        # Send progress to client
        socketio.emit('progress', {
            'percent': percent,
            'speed': speed,
            'eta': eta
        })
        socketio.sleep(0)
    if status == "finished":
        socketio.emit('progress', {
            'percent': '100%',
            'speed': '0',
            'eta': '0',
            'message': 'Finished!'})
    if status == "preparing":
        socketio.emit('progress', {
            'percent': '0%',
            'speed': '0',
            'eta': '0',
            'message': 'Preparing...'})