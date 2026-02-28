import yt_dlp


class VideoDownloader:
    def __init__(self, download_path=r"G:\yt",
                 ffmpeg_path=r"J:\Repo\Resources\python\ffmpeg-master-latest-win64-gpl-shared\ffmpeg-master-latest-win64-gpl-shared\bin"):
        """Initialize download and ffmpeg paths."""
        self.download_path = download_path
        self.ffmpeg_path = ffmpeg_path

    def get_download_format(self):
        """Ask the user to choose between MP4 (video) or MP3 (audio)."""
        print("\nChoose download format:")
        print("1. MP4 (Video)")
        print("2. MP3 (Audio)")
        choice = input("Enter 1 or 2: ").strip()

        if choice == "1":
            return "mp4"
        elif choice == "2":
            return "mp3"
        else:
            print("Invalid choice! Defaulting to MP4 (video).")
            return "mp4"

    def get_video_quality(self):
        """Ask the user to select video quality if MP4 is chosen."""
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

    def download_video(self, url):
        """Download a video or audio using yt-dlp."""
        download_format = self.get_download_format()

        if download_format == "mp4":
            video_quality = self.get_video_quality()
            ydl_opts = {
                'ffmpeg_location': self.ffmpeg_path,
                'outtmpl': f'{self.download_path}/%(title)s.%(ext)s',  # Save as title.ext
                'format': video_quality,
                'merge_output_format': 'mp4'
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
                }]
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            print("\nDownload complete!")
        except Exception as e:
            print(f"Error: {e}")

    def run(self):
        """Prompt for video URL and initiate download."""
        video_url = input("Enter video URL: ").strip()
        if video_url:
            self.download_video(video_url)
        else:
            print("Invalid URL. Please enter a valid video link.")


if __name__ == "__main__":
    downloader = VideoDownloader()
    downloader.run()
