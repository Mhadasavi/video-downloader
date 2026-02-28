import os
import yt_dlp
import subprocess
from pathlib import Path


class VideoDownloader:
    def __init__(self, download_path=r"G:\yt",
                 ffmpeg_path=r"J:\Repo\Resources\python\ffmpeg-master-latest-win64-gpl-shared\ffmpeg-master-latest-win64-gpl-shared\bin"):
        self.download_path = download_path
        self.ffmpeg_path = ffmpeg_path
        os.environ["PATH"] += os.pathsep + ffmpeg_path  # Add ffmpeg to PATH

    def get_download_format(self):
        print("\nChoose download format:")
        print("1. MP4 (Video)")
        print("2. MP3 (Audio)")
        choice = input("Enter 1 or 2: ").strip()
        return "mp4" if choice != "2" else "mp3"

    def get_video_quality(self):
        print("\nChoose video quality:")
        print("1. Best Quality (Auto)")
        print("2. 360p")
        print("3. 480p")
        print("4. 720p (HD)")
        print("5. 1080p (Full HD)")
        print("6. 1440p (2K)")
        print("7. 2160p (4K)")
        choice = input("Enter a number (1-7): ").strip()

        quality_map = {
            "1": "bestvideo+bestaudio/best",
            "2": "bestvideo[height=360]+bestaudio/best",
            "3": "bestvideo[height=480]+bestaudio/best",
            "4": "bestvideo[height=720]+bestaudio/best",
            "5": "bestvideo[height=1080]+bestaudio/best",
            "6": "bestvideo[height=1440]+bestaudio/best",
            "7": "bestvideo[height=2160]+bestaudio/best"
        }

        return quality_map.get(choice, "bestvideo+bestaudio/best")

    def get_partial_download_details(self):
        is_partial = input("\nDo you want to trim the video after download? (y/n): ").strip().lower()
        if is_partial == 'y':
            start = input("Enter start time (HH:MM:SS): ").strip()
            end = input("Enter end time (HH:MM:SS): ").strip()
            if start and end:
                return start, end
        return None, None

    def download_video(self, url):
        download_format = self.get_download_format()
        start_time, end_time = self.get_partial_download_details()

        if download_format == "mp4":
            video_quality = self.get_video_quality()
            ydl_opts = {
                'ffmpeg_location': self.ffmpeg_path,
                'outtmpl': f'{self.download_path}/%(title)s.%(ext)s',
                'format': video_quality,
                'merge_output_format': 'mp4',
                'quiet': True
            }
        else:
            ydl_opts = {
                'ffmpeg_location': self.ffmpeg_path,
                'outtmpl': f'{self.download_path}/%(title)s.%(ext)s',
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'
                }],
                'quiet': True
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                downloaded_file = Path(self.download_path) / f"{info_dict['title']}.{info_dict['ext']}"
            print("\nDownload complete!")

            if download_format == "mp4" and start_time and end_time:
                self.trim_video(downloaded_file, start_time, end_time)

        except Exception as e:
            print(f"Error: {e}")

    @staticmethod
    def trim_video(input_path, start_time, end_time, output_path=None):
        """Trim a local video file between start_time and end_time using ffmpeg."""
        input_path = Path(input_path)
        if not input_path.exists():
            print(f"File not found: {input_path}")
            return

        if output_path is None:
            output_path = input_path.with_name(input_path.stem + "_trimmed" + input_path.suffix)

        command = [
            "ffmpeg",
            "-ss", start_time,
            "-to", end_time,
            "-i", str(input_path),
            "-c", "copy",
            str(output_path)
        ]

        try:
            subprocess.run(command, check=True)
            print(f"Segment saved to: {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error: {e}")

    def run(self):
        video_url = input("Enter video URL: ").strip()
        if video_url:
            self.download_video(video_url)
        else:
            print("Invalid URL. Please enter a valid video link.")

# VideoDownloader.trim_video("G:/yt/Bhajarangi 2.mp4", "02:00:00", "02:15:30")
downloader = VideoDownloader()
downloader.run()

