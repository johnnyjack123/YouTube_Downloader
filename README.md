### YouTube Downloader
#### Introduction

YouTube Downloader is a tool based on [yt-dlp](https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file) that allows you to easily download YouTube videos to your computer.

#### Installation

1. Clone this Git repository.
2. Make sure [Python](https://www.python.org/downloads/) is installed on your PC.
3. It as also necessary to have [FFmpeg](https://ffmpeg.org) installed on your PC. In this script is an implemented downloader for FFmpeg, if it is not installed. If the script is asking you, if you want to install FFmpeg, type in "yes" followed from enter in the command line. FFmpeg is used to merge the video and audio stream provided by YouTube. You are not able to use this tool without FFmpeg installed.
3. Move in the command line to the folder where the `launcher.py` file is located.
4. Run the command `pip install -r requirements.txt` to install the necessary libraries.
5. Run the command `python launcher.py` to launch the program.
6. If everything works correctly a browser window will open.

#### Using YouTube Downloader

1. Simply paste a YouTube video link or a link to a public YouTube playlist (can be unlisted) in the corresponding input field.

2. Select a folder where the video will be saved after download. Use the integrated explorer for this, which you can access via the corresponding button.

3. Choose the download quality in the corresponding drop down. If you prefer to have the full control over your download resolution you can check the checkbox for a custom resolution download and you are able to choose your preferred resolution.

4. You can choose an output video container. FFmpeg will convert your downloaded streams after downloading to this container.

6. Once the video is downloaded and merged, you can find it in the folder you selected earlier.
7. If you download only the audio stream you are able to select 'mp3' in the video container dropdown.
8. Make sure to check out the settings page, where you can decide of you want automatic updates, etc.
