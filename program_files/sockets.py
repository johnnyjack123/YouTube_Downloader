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
        console("Client connected")
        emit_queue()
        update_tasks()

def update_tasks():
    socketio.emit("update_tasks", global_variables.task_list)

def update_title_in_queue(title, video_url):
    if global_variables.video_data:
        if title:
            video = next((v for v in global_variables.video_data if v["video_url"] == video_url), None)
            if video:
                video["video_name"] = title
                emit_queue()

def console(command):
    #global console_socket
    if command == "Client connected":
        if "Client connected" in global_variables.console_socket:
            return
    elif command == "[yt-dlp]: Testing formats":
        if "[yt-dlp]: Testing formats" in global_variables.console_socket:
            return
    socketio.emit("console", command)
    socketio.sleep(0)
    global_variables.console_socket.append(command)
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