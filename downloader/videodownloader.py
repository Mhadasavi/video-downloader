import yt_dlp


class VideoDownloader:

    def download_video(url, download_path=r"C:\Users\uchau\Downloads"):
        """Download a video using yt-dlp."""

        ffmpeg_path = r"J:\Repo\Resources\python\ffmpeg-master-latest-win64-gpl-shared\ffmpeg-master-latest-win64-gpl-shared\bin"

        ydl_opts = {
            'ffmpeg_location': ffmpeg_path,
            'outtmpl': f'{download_path}/%(title)s.%(ext)s',  # Save as title.ext
            'format': 'bestvideo+bestaudio/best',  # Choose best quality
            'merge_output_format': 'mp4'  # Ensure MP4 format
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            print("\nDownload complete!")
        except Exception as e:
            print(f"Error: {e}")

    if __name__ == "__main__":
        video_url = input("Enter video URL: ").strip()
        download_video(video_url)
