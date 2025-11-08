# YouTube Downloader

## Introduction

YouTube Downloader is a tool based on [yt-dlp](https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file) that allows you to easily download YouTube videos to your computer.

## Installation

### Automatic installation (easy and quick, recommended)

1. Clone this Git repository or save it as a zip file anywhere on your computer.
2. Move to the main folder of this program, where the `launcher.py` file is located.
3. INFO: By performing step 4 or 5 the script will probably install Python and ffmpeg, if they are not already installed on your computer. These programs are necessary to run this program correctly.
4. If you are on Windows simply doubleclick the windows_launcher.bat file. A dialog will pop up which warns you of a danger to your computer. You have to execute the file nevertheless. That happens due to a missing signature from Microsoft for the batch file, which unfortunately costs lots of money.
5. If you are on Linux/MacOs, move in the command line at the same folder and run the command `chmod +x mac_os_or_linux_launcher.sh` followed by `./mac_os_or_linux_launcher.sh`. Now you can always start this program via `./mac_os_or_linux_launcher.sh` from this directory.
6. If everything works correctly a browser window will open. You are also able to reach the hosted website at <http://localhost:5000> .

### Manual installation

1. Clone this Git repository.
2. Make sure [Python](https://www.python.org/downloads/) is installed on your PC.
3. It as also necessary to have [FFmpeg](https://ffmpeg.org) installed on your PC. In this script is an implemented downloader for FFmpeg, if it is not installed. If the script is asking you, if you want to install FFmpeg, type in "yes" followed from enter in the command line. FFmpeg is used to merge the video and audio stream provided by YouTube. You are not able to use this tool without FFmpeg installed.
4. If you want to run this program in a venv (virtual environment) you can activate it now at the `YouTube_Downloader` directory, where the `launcher.py` file is located ([Tutorial](https://realpython.com/python-virtual-environments-a-primer/#create-it)).
5. Move in the command line to the folder `YouTube_Downloader/program_files` where the `requirements.txt` file is located.
6. Run the command `pip install -r requirements.txt` to install the necessary libraries.
7. Run the command `python launcher.py` to launch the program.
8. If everything works correctly a browser window will open. You are also able to reach the hosted website at <http://localhost:5000> .

## Using YouTube Downloader

1. Simply paste a YouTube video link or a link to a public YouTube playlist (can be unlisted) in the corresponding input field.

2. Select a folder where the video will be saved after download. Use the integrated explorer for this, which you can access via the corresponding button at the path bar on the top.

3. Choose the download quality in the corresponding dropdown. If you prefer to have the full control over your download resolution, select "Custom" from the dropdown for a custom resolution download and you are able to choose your preferred resolution.

4. You can choose an output video container. FFmpeg will convert your downloaded streams after downloading to this container.
5. Furthermore you have a console, which informs you about the status of the download and a task list, which shows the following steps for the downloading process. **In addition, you are able to paste another link during the download into the corresponding input field and hit `Start Download` again. The video gets added to the video queue and the download starts automatically after finishing the first video. You can add as many videos as you want to the video queue.**
6. Once the video is downloaded and merged, you can find it in the folder you selected earlier.
7. If you download only the audio stream you are able to select 'mp3' in the video container dropdown.
8. Make sure to check out the settings page, where you can decide of you want automatic updates, etc.
