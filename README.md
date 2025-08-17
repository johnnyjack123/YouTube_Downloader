### YouTube Downloader
#### Introduction

YouTube Downloader is a tool based on [yt-dlp](https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file#general-options) that allows you to easily download YouTube videos to your computer.

#### Installation

1. Clone this Git repository.

2. Make sure Python is installed on your PC.

3. Run the yt-dlp_backend.py file.

4. A browser window will open.

#### Using YouTube Downloader

1. Simply paste a YouTube video link or a link to a public YouTube playlist (can be unlisted) in the corresponding input field.

2. Select a folder where the video will be saved after download. Use the integrated explorer for this, which you can access via the corresponding button.

3. Choose the download quality. Best means that the best available stream where audio and video are already merged will be downloaded. This is most likely not the best video quality available. In this case, you have to choose Best video and best audio (separated downloads, merged after download, sometimes providing better quality) or select a custom resolution. If you check the checkbox for a custom resolution, you can choose your preferred resolution.

4. You can choose an output video container. If you download in low resolutions, you will probably not get the selected video container. This happens because a pre-merged video and audio stream is used, which is downloaded as-is. For higher resolutions, there are no pre-merged streams, so YouTube-dlp running in the background will merge audio and video together. In this case, it will also convert the video container to the one you chose.

5. There is still a bug I can’t fix: after pressing Download, it may seem like nothing happened. But after a few seconds, the download will start, and you can watch the progress on the web page.

6. Once the video is downloaded, you can find it in the folder you selected earlier.
