import os
import sys
import json
import shutil
import queue
import threading
import time
import subprocess
import re
import logging
from pathlib import Path
from flask import Flask, render_template, jsonify, request, Response
import yt_dlp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("video-downloader")

LANGUAGE_NAMES = {
    'en': 'English',
    'en-US': 'English (US)',
    'en-GB': 'English (UK)',
    'hi': 'Hindi',
    'es': 'Spanish',
    'es-ES': 'Spanish (Spain)',
    'es-419': 'Spanish (Latin America)',
    'fr': 'French',
    'de': 'German',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh': 'Chinese',
    'zh-Hans': 'Chinese (Simplified)',
    'zh-Hant': 'Chinese (Traditional)',
    'ar': 'Arabic',
    'pt': 'Portuguese',
    'pt-BR': 'Portuguese (Brazil)',
    'ru': 'Russian',
    'it': 'Italian',
    'tr': 'Turkish',
    'vi': 'Vietnamese',
    'th': 'Thai',
    'id': 'Indonesian',
    'pl': 'Polish',
    'ml': 'Malayalam',
    'te': 'Telugu',
    'ta': 'Tamil',
    'bn': 'Bengali',
    'nl': 'Dutch',
    'sv': 'Swedish',
    'no': 'Norwegian',
    'da': 'Danish',
    'fi': 'Finnish',
}

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Settings file path
SETTINGS_FILE = Path(__file__).parent / "settings.json"

# Active download state
download_state = {
    'status': 'idle',          # idle, fetching, downloading, processing, trimming, completed, error
    'percent': 0,
    'speed': '',
    'eta': '',
    'title': '',
    'thumbnail': '',
    'uploader': '',
    'duration': '',
    'filepath': '',
    'error': None
}

# Lock for state access
state_lock = threading.Lock()

# Queue for SSE messages
sse_queues = []
sse_lock = threading.Lock()

def format_views(view_count):
    """Format numerical view count to a readable string (e.g., 1.5M views)."""
    if view_count is None:
        return "No views"
    try:
        views = int(view_count)
        if views >= 1000000000:
            return f"{views / 1000000000:.1f}B views"
        elif views >= 1000000:
            return f"{views / 1000000:.1f}M views"
        elif views >= 1000:
            return f"{views / 1000:.1f}K views"
        return f"{views} views"
    except Exception:
        return "N/A"

def validate_time_format(t_str):
    """Validate that a time string matches HH:MM:SS, MM:SS, or is a number of seconds."""
    if not t_str:
        return False
    return bool(re.match(r'^(\d{1,2}:)?\d{1,2}:\d{2}$|^\d+(\.\d+)?$', t_str))

def time_to_seconds(t_str):
    """Convert time string of format HH:MM:SS, MM:SS, or seconds to float seconds."""
    if not t_str:
        return 0.0
    if ':' in t_str:
        parts = t_str.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
    return float(t_str)

def resolve_bundled_ffmpeg():
    """Copy the imageio-ffmpeg binary to a local project directory with a standard name so yt-dlp can locate it."""
    bin_dir = Path(__file__).parent / "bin"
    os.makedirs(bin_dir, exist_ok=True)
    ffmpeg_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    ffmpeg_dest = bin_dir / ffmpeg_name
    
    if not ffmpeg_dest.exists():
        try:
            import imageio_ffmpeg
            src = imageio_ffmpeg.get_ffmpeg_exe()
            if os.path.exists(src):
                shutil.copy2(src, ffmpeg_dest)
                logger.info(f"Successfully copied bundled FFmpeg binary to {ffmpeg_dest}")
        except Exception as e:
            logger.warning(f"Could not copy bundled FFmpeg binary: {e}")
            
    if ffmpeg_dest.exists():
        return str(bin_dir)
    return ""

def load_settings():
    """Load settings from JSON, or set defaults."""
    is_docker = os.path.exists('/.dockerenv')
    
    if is_docker:
        default_download = "/root/Downloads"
        default_ffmpeg = "ffmpeg"
    else:
        default_download = os.path.expanduser(r"~\Downloads")
        default_ffmpeg = resolve_bundled_ffmpeg()
        if not default_ffmpeg:
            if shutil.which("ffmpeg"):
                default_ffmpeg = "ffmpeg"
        
    defaults = {
        "download_path": default_download,
        "ffmpeg_path": default_ffmpeg
    }
    
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
                if is_docker:
                    # Ignore Windows host paths in container environment
                    saved_download = saved.get('download_path', '')
                    if not saved_download or '\\' in saved_download or ':' in saved_download:
                        saved['download_path'] = default_download
                        
                    saved_ffmpeg = saved.get('ffmpeg_path', '')
                    if not saved_ffmpeg or '\\' in saved_ffmpeg or ':' in saved_ffmpeg:
                        saved['ffmpeg_path'] = default_ffmpeg
                defaults.update(saved)
        except Exception as e:
            logger.exception(f"Error loading settings: {e}")
            
    return defaults

def save_settings(settings):
    """Save settings to JSON."""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        logger.exception(f"Error saving settings: {e}")
        return False

# Initialize settings
settings = load_settings()

def update_state(**kwargs):
    """Update active download state and notify SSE clients."""
    with state_lock:
        download_state.update(kwargs)
        state_copy = download_state.copy()
        
    # Broadcast to all SSE listeners
    payload = json.dumps(state_copy)
    with sse_lock:
        for q in sse_queues:
            q.put(payload)

def progress_hook(d):
    """yt-dlp progress hook to capture status, speed, and ETA."""
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
        downloaded = d.get('downloaded_bytes', 0)
        percent = round((downloaded / total) * 100, 1) if total > 0 else 0
        
        speed = d.get('_speed_str', 'N/A')
        # Clean up speed string escape characters
        if speed:
            speed = speed.replace('\x1b[0;32m', '').replace('\x1b[0m', '')
            
        eta = d.get('_eta_str', 'N/A')
        if eta:
            eta = eta.replace('\x1b[0;33m', '').replace('\x1b[0m', '')
            
        update_state(
            status='downloading',
            percent=percent,
            speed=speed,
            eta=eta
        )
    elif d['status'] == 'finished':
        update_state(
            status='processing',
            percent=100,
            speed='Merging...',
            eta='0s'
        )

def run_download_thread(url, download_format, video_quality, trim_start, trim_end, custom_download_path=None, language=None):
    """Perform download and optional trimming in a background thread."""
    current_settings = load_settings()
    download_path = custom_download_path if custom_download_path else current_settings['download_path']
    ffmpeg_path = current_settings['ffmpeg_path']
    
    # Ensure download path exists
    os.makedirs(download_path, exist_ok=True)
    
    ydl_opts = {
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
        'quiet': True,
        'js_runtimes': {'deno': {}, 'node': {}},
        'socket_timeout': 20
    }
    
    if ffmpeg_path and ffmpeg_path != "ffmpeg":
        if os.path.isfile(ffmpeg_path):
            ydl_opts['ffmpeg_location'] = os.path.dirname(ffmpeg_path)
        else:
            ydl_opts['ffmpeg_location'] = ffmpeg_path
        
    if download_format == 'mp4':
        if language:
            height_limit = ""
            if "height<=" in video_quality:
                match = re.search(r"height<=(\d+)", video_quality)
                if match:
                    height_limit = match.group(1)
            
            if height_limit:
                h = height_limit
                ydl_opts['format'] = f"bestvideo[height<={h}]+bestaudio[language^={language}]/best[language^={language}][height<={h}]/bestvideo[height<={h}]+bestaudio/best[height<={h}]"
            else:
                ydl_opts['format'] = f"bestvideo+bestaudio[language^={language}]/best[language^={language}]/bestvideo+bestaudio/best"
        else:
            ydl_opts['format'] = video_quality
        ydl_opts['merge_output_format'] = 'mp4'
    else:
        if language:
            ydl_opts['format'] = f"bestaudio[language^={language}]/best[language^={language}]/bestaudio/best"
        else:
            ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }]
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Re-fetch info to make sure we have the details
            info_dict = ydl.extract_info(url, download=True)
            
            # Resolve final filename
            prep_filename = ydl.prepare_filename(info_dict)
            downloaded_file = Path(prep_filename)
            
            if download_format == "mp4":
                downloaded_file = downloaded_file.with_suffix('.mp4')
            elif download_format == "mp3":
                downloaded_file = downloaded_file.with_suffix('.mp3')
                
            if not downloaded_file.exists() and 'requested_downloads' in info_dict:
                req_dl = info_dict['requested_downloads']
                if req_dl:
                    downloaded_file = Path(req_dl[0].get('filepath', downloaded_file))
                    
        if not downloaded_file.exists():
            raise FileNotFoundError("Could not find the downloaded video file on disk.")
            
        final_filepath = downloaded_file
        
        # Check if trimming is needed
        if download_format == 'mp4' and trim_start and trim_end:
            update_state(status='trimming', percent=100, speed='Trimming video...', eta='')
            trimmed_file = downloaded_file.with_name(downloaded_file.stem + "_trimmed" + downloaded_file.suffix)
            
            ffmpeg_bin = "ffmpeg"
            if ffmpeg_path:
                if os.path.isfile(ffmpeg_path):
                    ffmpeg_bin = ffmpeg_path
                elif os.path.isdir(ffmpeg_path):
                    ffmpeg_bin = os.path.join(ffmpeg_path, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
                else:
                    ffmpeg_bin = ffmpeg_path
                
            # Check if ffmpeg binary exists or is in PATH
            if not shutil.which(ffmpeg_bin) and not os.path.exists(ffmpeg_bin):
                raise FileNotFoundError(f"FFmpeg binary not found at '{ffmpeg_bin}'. Please install FFmpeg or check Settings.")
                
            command = [
                ffmpeg_bin,
                "-ss", trim_start,
                "-to", trim_end,
                "-i", str(downloaded_file),
                "-c", "copy",
                "-y",
                str(trimmed_file)
            ]
            
            try:
                logger.info(f"Executing FFmpeg trim: {' '.join(command)}")
                subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                final_filepath = trimmed_file
                # Delete original file to save space
                try:
                    downloaded_file.unlink()
                    logger.info(f"Successfully deleted original untrimmed file: {downloaded_file}")
                except Exception as del_err:
                    logger.warning(f"Could not delete original untrimmed file: {del_err}")
            except Exception as trim_err:
                # Clean up failed trimmed file
                if trimmed_file.exists():
                    try:
                        trimmed_file.unlink()
                    except Exception:
                        pass
                raise RuntimeError(f"FFmpeg trimming failed: {trim_err}")
            
        update_state(
            status='completed',
            percent=100,
            speed='Done',
            eta='',
            filepath=str(final_filepath)
        )
        
    except Exception as e:
        logger.exception(f"Exception in download thread: {e}")
        update_state(
            status='error',
            error=str(e),
            percent=0,
            speed='',
            eta=''
        )

@app.route('/')
def index():
    return render_template('index.html')

def get_ytdlp_version():
    """Helper to retrieve the installed yt-dlp version."""
    try:
        import yt_dlp
        return yt_dlp.version.__version__
    except Exception as e:
        logger.warning(f"Could not retrieve yt-dlp version: {e}")
        return "Unknown"

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    global settings
    if request.method == 'POST':
        data = request.json
        settings['download_path'] = data.get('download_path', settings['download_path'])
        settings['ffmpeg_path'] = data.get('ffmpeg_path', settings['ffmpeg_path'])
        save_settings(settings)
        return jsonify({"success": True, "settings": settings})
    
    # Return settings along with the current version
    response_data = settings.copy()
    response_data['ytdlp_version'] = get_ytdlp_version()
    return jsonify(response_data)

@app.route('/api/update-ytdlp', methods=['POST'])
def api_update_ytdlp():
    """Upgrade yt-dlp to the latest version via pip."""
    try:
        old_version = get_ytdlp_version()
        logger.info(f"Upgrading yt-dlp via UI request. Current version: {old_version}")
        
        # Run pip install -U yt-dlp using sys.executable to target the active environment
        command = [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Force reload of the cached module to reflect the version change
            try:
                import importlib
                import yt_dlp
                importlib.reload(yt_dlp)
            except Exception as reload_err:
                logger.warning(f"Could not reload yt_dlp module: {reload_err}")
                
            new_version = get_ytdlp_version()
            logger.info(f"Successfully upgraded yt-dlp to version {new_version}")
            return jsonify({
                "success": True,
                "message": f"Successfully upgraded yt-dlp from {old_version} to {new_version}.",
                "old_version": old_version,
                "new_version": new_version
            })
        else:
            logger.error(f"Failed to upgrade yt-dlp: {result.stderr}")
            return jsonify({
                "success": False,
                "error": f"Upgrade failed: {result.stderr or result.stdout}"
            }), 500
            
    except Exception as e:
        logger.exception(f"Exception during yt-dlp upgrade: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/select-folder', methods=['POST'])
def api_select_folder():
    """Trigger a native folder selection dialog using Tkinter in a separate process to avoid thread conflicts."""
    if os.path.exists('/.dockerenv'):
        return jsonify({"error": "Folder selection dialog is not supported inside container environments. Please enter the path manually."}), 400
    try:
        # Run a standalone Python one-liner in a subprocess. This prevents thread deadlock on Windows/Flask.
        initial_dir = settings.get('download_path', '')
        # Escape backslashes for python script argument
        initial_dir_escaped = initial_dir.replace('\\', '\\\\')
        
        script = (
            "import tkinter as tk; "
            "from tkinter import filedialog; "
            "root = tk.Tk(); "
            "root.withdraw(); "
            "root.attributes('-topmost', True); "
            f"print(filedialog.askdirectory(initialdir='{initial_dir_escaped}'), end='')"
        )
        
        logger.info(f"Opening folder picker subprocess with initialdir: {initial_dir}")
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            selected_path = result.stdout.strip()
            if selected_path:
                logger.info(f"User selected folder: {selected_path}")
                return jsonify({"selected": selected_path})
            logger.info("User cancelled folder picker.")
            return jsonify({"selected": None})
        else:
            raise RuntimeError(result.stderr or "Subprocess failed to run.")
            
    except Exception as e:
        logger.exception(f"Error in api_select_folder: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/info', methods=['POST'])
def api_info():
    """Extract metadata of a video without downloading."""
    data = request.json
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
        
    current_settings = load_settings()
    ffmpeg_path = current_settings['ffmpeg_path']
    
    ydl_opts = {
            'quiet': True,
            'js_runtimes': {'deno': {}, 'node': {}},
            'socket_timeout': 20
        }
    if ffmpeg_path and ffmpeg_path != "ffmpeg":
        if os.path.isfile(ffmpeg_path):
            ydl_opts['ffmpeg_location'] = os.path.dirname(ffmpeg_path)
        else:
            ydl_opts['ffmpeg_location'] = ffmpeg_path
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            
            # Format duration
            duration_secs = info_dict.get('duration')
            duration_str = "N/A"
            if duration_secs:
                duration_str = time.strftime('%H:%M:%S', time.gmtime(duration_secs))
                # Strip leading 00: if present
                if duration_str.startswith("00:"):
                    duration_str = duration_str[3:]
                    
            thumbnail = info_dict.get('thumbnail', '')
            # If thumbnail is not direct, find it in thumbnails list
            if not thumbnail and info_dict.get('thumbnails'):
                thumbnail = info_dict['thumbnails'][-1].get('url', '')
                
            # Extract available languages from formats
            languages = {}
            for f in info_dict.get('formats', []):
                lang = f.get('language')
                if lang:
                    languages[lang] = True
            
            # Map to readable names
            lang_list = []
            for code in sorted(languages.keys()):
                name = LANGUAGE_NAMES.get(code, code.upper())
                lang_list.append({
                    'code': code,
                    'name': name
                })
                
            metadata = {
                'id': info_dict.get('id', ''),
                'title': info_dict.get('title', 'Unknown Title'),
                'thumbnail': thumbnail,
                'uploader': info_dict.get('uploader', 'Unknown Channel'),
                'duration': duration_str,
                'views': format_views(info_dict.get('view_count')),
                'languages': lang_list,
                'status': 'idle'
            }
            
            return jsonify(metadata)
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download', methods=['POST'])
def api_download():
    """Start a download background thread."""
    global download_state
    
    with state_lock:
        if download_state['status'] in ['fetching', 'downloading', 'processing', 'trimming']:
            return jsonify({"error": "A download is already in progress."}), 400
            
    data = request.json
    url = data.get('url', '')
    if url:
        url = url.strip()
    download_format = data.get('format', 'mp4') # mp4 or mp3
    video_quality = data.get('quality', 'bestvideo+bestaudio/best')
    
    custom_download_path = data.get('download_path')
    if custom_download_path:
        custom_download_path = custom_download_path.strip()
    else:
        custom_download_path = None
        
    language = data.get('language')
    if language:
        language = language.strip()
    else:
        language = None
    
    trim_enabled = data.get('trim_enabled', False)
    trim_start = data.get('trim_start')
    if trim_start and trim_enabled:
        trim_start = trim_start.strip()
    else:
        trim_start = None
        
    trim_end = data.get('trim_end')
    if trim_end and trim_enabled:
        trim_end = trim_end.strip()
    else:
        trim_end = None
    
    if trim_enabled:
        if not trim_start or not trim_end:
            return jsonify({"error": "Start and End times are required when trimming is enabled."}), 400
        if not validate_time_format(trim_start) or not validate_time_format(trim_end):
            return jsonify({"error": "Invalid time format for trimming. Use HH:MM:SS, MM:SS, or seconds (e.g. 00:01:30 or 90)."}), 400
        try:
            start_sec = time_to_seconds(trim_start)
            end_sec = time_to_seconds(trim_end)
            if start_sec >= end_sec:
                return jsonify({"error": "Start time must be less than end time."}), 400
        except Exception:
            return jsonify({"error": "Failed to parse trim times."}), 400

    if not url:
        return jsonify({"error": "URL is required"}), 400
        
    # Reset download state
    update_state(
        status='downloading',
        percent=0,
        speed='Starting...',
        eta='',
        error=None,
        filepath=''
    )
    
    # Start download thread
    t = threading.Thread(
        target=run_download_thread,
        args=(url, download_format, video_quality, trim_start, trim_end, custom_download_path, language)
    )
    t.daemon = True
    t.start()
    
    return jsonify({"success": True, "message": "Download started"})

@app.route('/api/progress')
def api_progress():
    """SSE endpoint to stream downloader state changes to frontend."""
    def event_stream():
        # Create a queue for this SSE listener
        q = queue.Queue()
        with sse_lock:
            sse_queues.append(q)
            
        # Send initial state
        with state_lock:
            initial = json.dumps(download_state)
        yield f"data: {initial}\n\n"
        
        try:
            while True:
                # Block until state changes
                try:
                    data = q.get(timeout=10) # 10 seconds heartbeat
                    yield f"data: {data}\n\n"
                except queue.Empty:
                    # Heartbeat
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            with sse_lock:
                sse_queues.remove(q)
                
    resp = Response(event_stream(), mimetype="text/event-stream")
    resp.headers['X-Accel-Buffering'] = 'no'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp

@app.route('/api/reveal', methods=['POST'])
def api_reveal():
    """Reveal the downloaded file in Windows Explorer."""
    data = request.json
    file_path = data.get('path', '')
    if not file_path:
        return jsonify({"error": "Path is required"}), 400
        
    try:
        clean_path = os.path.normpath(file_path)
        if os.path.exists(clean_path):
            # Using explorer.exe /select,path opens the directory and highlights the file
            subprocess.run(["explorer", f"/select,{clean_path}"])
            return jsonify({"success": True})
        else:
            # If the file doesn't exist (maybe deleted), check its parent directory
            parent = os.path.dirname(clean_path)
            if os.path.exists(parent):
                subprocess.run(["explorer", parent])
                return jsonify({"success": True})
            return jsonify({"error": "File or folder not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/related', methods=['POST'])
def api_related():
    """Fetch related videos by searching for the title/uploader."""
    data = request.json
    title = data.get('title', '').strip()
    uploader = data.get('uploader', '').strip()
    current_id = data.get('id', '').strip()
    
    if not title:
        return jsonify({"error": "Title is required"}), 400
        
    query = f"ytsearch8:{title} {uploader}"
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'js_runtimes': {'deno': {}, 'node': {}},
        'socket_timeout': 20
    }
    
    current_settings = load_settings()
    ffmpeg_path = current_settings['ffmpeg_path']
    if ffmpeg_path and ffmpeg_path != "ffmpeg":
        if os.path.isfile(ffmpeg_path):
            ydl_opts['ffmpeg_location'] = os.path.dirname(ffmpeg_path)
        else:
            ydl_opts['ffmpeg_location'] = ffmpeg_path
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            results = ydl.extract_info(query, download=False)
            entries = results.get('entries', [])
            related = []
            count = 0
            for entry in entries:
                entry_id = entry.get('id', '')
                if current_id and entry_id == current_id:
                    continue  # Filter out duplicate source video
                    
                duration_secs = entry.get('duration')
                duration_str = "N/A"
                if duration_secs:
                    duration_str = time.strftime('%M:%S', time.gmtime(duration_secs))
                    if duration_str.startswith("00:"):
                        duration_str = duration_str[3:]
                    
                thumbnail = ""
                if entry.get('thumbnails'):
                    thumbnail = entry['thumbnails'][-1].get('url', '')
                elif entry_id:
                    thumbnail = f"https://i.ytimg.com/vi/{entry_id}/hqdefault.jpg"
                    
                related.append({
                    'id': entry_id,
                    'title': entry.get('title', 'Unknown Title'),
                    'url': f"https://www.youtube.com/watch?v={entry_id}" if entry_id else entry.get('url', ''),
                    'uploader': entry.get('uploader') or entry.get('channel') or 'Unknown Channel',
                    'duration': duration_str,
                    'thumbnail': thumbnail,
                    'views': format_views(entry.get('view_count'))
                })
                count += 1
                if count >= 5:
                    break
            return jsonify(related)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Make sure templates folder exists
    os.makedirs(Path(__file__).parent / "templates", exist_ok=True)
    
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    
    # Auto-open browser in a separate thread
    def open_browser():
        time.sleep(1.5)
        import webbrowser
        webbrowser.open(f"http://{host}:{port}")
        
    threading.Thread(target=open_browser, daemon=True).start()
    
    logger.info(f"Starting NexStream Server on http://{host}:{port} (debug={debug})")
    app.run(host=host, port=port, debug=debug)
