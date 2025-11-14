import os
import requests
from program_files.logger import logger
from program_files.outsourced_functions import read
import program_files.safe_shutil as shutil
from program_files.safe_shutil import _check_path

def check_for_updates(url_version, file_name, update):
    new_version_file = os.path.join("tmp", file_name)
    result = get_file(url_version, new_version_file)
    if result:
        try:
            if update == "launcher":
                version_file = file_name
            elif update == "main":
                version_file = os.path.join("program_files", file_name)
            else:
                return f"Wrong update mode set: {update}."

            if not os.path.exists(version_file):
                with open(version_file, "w", encoding="utf-8") as f:
                    f.write("0.0")

            with open(version_file, "r", encoding="utf-8") as file:
                program_version = float(file.read().strip())
            with open(new_version_file, "r", encoding="utf-8") as file:
                new_version = float(file.read().strip())
            if new_version > program_version:
                return "Update"
            else:
                print("Program is up to date")
                logger.info("Program is up to date")
                return "Launch"
        except Exception as e:
            logger.error(f"No {file_name} available.")
            return "Update"
    else:
        return "Launch"

def get_file(url, save_path):
    file = read("file")
    program_data = file["program_data"]
    response_version = requests.get(url)
    if response_version.status_code == 200:
        with open(save_path, "wb") as file:
            file.write(response_version.content)
            logger.info(f"{save_path} stored in /tmp")
            return True
    else:
        logger.error(f"File {save_path} is unreachable on repo {program_data["update_repo"]} and branch {program_data["update_branch"]}.")
        return False

def update_launcher():
    file = read("file")
    program_data = file["program_data"]
    branch = program_data["update_branch"]
    repo = program_data["update_repo"]
    batch_file_name = "windows_launcher.bat"
    url_launcher_py = f"https://raw.githubusercontent.com/{repo}/refs/heads/{branch}/launcher.py"
    url_launcher_bat = f"https://raw.githubusercontent.com/{repo}/refs/heads/{branch}/{batch_file_name}"
    tmp_launcher_folder = os.path.join("tmp", "launcher")
    launcher_py_path = os.path.join(tmp_launcher_folder, "launcher.py")
    launcher_bat_path = os.path.join(tmp_launcher_folder, batch_file_name)
    launcher_py_old_path = os.path.join("tmp", "old_files", "launcher", "launcher.py")
    launcher_bat_old_path = os.path.join("tmp", "old_files", "launcher", batch_file_name)
    result = get_file(url_launcher_py, launcher_py_path)
    if not result:
        return False
    result = get_file(url_launcher_bat, launcher_bat_path)
    if not result:
        return False

    try:
        shutil.move("launcher.py", launcher_py_old_path, False)
        shutil.move("launcher.bat", launcher_bat_old_path, False)
    except PermissionError as e:
        logger.error(f"Unable to move old launcher files: {e}")

    try:
        shutil.move(launcher_py_path, "launcher.py", False)
        shutil.move(launcher_bat_path, "launcher.bat", False)
    except PermissionError as e:
        logger.error(f"Permission error: {e}")
        shutil.move(launcher_py_old_path, "launcher.py", False)
        shutil.move(launcher_bat_old_path, "launcher.bat", False)


    logger.info("Launcher successfully updated.")
    new_launcher_version_path = os.path.join("tmp", "launcher_version.txt")
    for path in [launcher_py_old_path, launcher_bat_old_path, "launcher_version.txt"]:
        _check_path(path)
        os.remove(path)

    shutil.move(new_launcher_version_path, "launcher_version.txt", False)
    logger.info("Old files deleted.")
    return

def check_for_update_launcher():
    file = read("file")
    program_data = file["program_data"]
    branch = program_data["update_branch"]
    repo = program_data["update_repo"]
    url_version = f"https://raw.githubusercontent.com/{repo}/refs/heads/{branch}/launcher_version.txt"
    file_name = "launcher_version.txt"
    update = "launcher"
    result = check_for_updates(url_version, file_name, update)
    if result == "Update":
        logger.info("Update program launcher.")
        print("Update program launcher.")
        update_launcher()
    elif result == "Launch":
        logger.info("Launcher is up to date.")
    else:
        logger.error(f"Error in update process: {result}")