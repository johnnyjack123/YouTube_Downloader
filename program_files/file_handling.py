import program_files.globals as global_variables
import json
import os
import program_files.safe_shutil as shutil

def save(entry, video_data):
    userdata_file = global_variables.userdata_file
    with open(userdata_file, "r", encoding="utf-8") as file:
        data = json.load(file)
        if entry == "whole_file":
            data = video_data
        else:
            data[entry] = video_data
    with open(userdata_file, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    return

def read(entry):
    userdata_file = global_variables.userdata_file
    if entry == "file":
        with open(userdata_file, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data
    elif entry:
        with open(userdata_file, "r", encoding="utf-8") as file:
            data = json.load(file)
            video_data = data[entry]
            return video_data

def check_for_userdata():
    print("Check for userdata.")
    userdata_file = global_variables.userdata_file
    entry = {
        "userdata": global_variables.userdata,
        "program_data": global_variables.program_data,
        "download_data": global_variables.download_data
    }
    if not os.path.exists(userdata_file):
        with open(userdata_file, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=4, ensure_ascii=False)
        print("Created userdata")
    return

def create_folders():
    if not os.path.exists("tmp"):
        os.makedirs("tmp")

    tmp_launcher_folder = os.path.join("tmp", "launcher")
    if not os.path.exists(tmp_launcher_folder):
        os.makedirs(tmp_launcher_folder)
    else:
        shutil.rmtree(tmp_launcher_folder)
        os.makedirs(tmp_launcher_folder)

    tmp_old_files = os.path.join("tmp", "old_files")
    if not os.path.exists(tmp_old_files):
        os.makedirs(tmp_old_files)
    else:
        shutil.rmtree(tmp_old_files)
        os.makedirs(tmp_old_files)

    tmp_old_files_launcher = os.path.join("tmp", "old_files", "launcher")
    if not os.path.exists(tmp_old_files_launcher):
        os.makedirs(tmp_old_files_launcher)
    else:
        shutil.rmtree(tmp_old_files_launcher)
        os.makedirs(tmp_old_files_launcher)

    tmp_old_files_main = os.path.join("tmp", "old_files", "main")
    if not os.path.exists(tmp_old_files_main):
        os.makedirs(tmp_old_files_main)
    else:
        shutil.rmtree(tmp_old_files_main)
        os.makedirs(tmp_old_files_main)

    va = os.path.join("tmp", "va")
    if not os.path.exists(va):
        os.makedirs(va)
    else:
        shutil.rmtree(va)
        os.makedirs(va)
    return