import subprocess
import tempfile
import shutil
from pathlib import Path


class VideoProcessor:
    def __init__(self, work_dir: str = None):
        self.work_dir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="kalimba_"))
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def get_video_title(self, url: str) -> str:
        result = subprocess.run(
            ["yt-dlp", "--get-title", "--no-playlist", url],
            capture_output=True, text=True,
        )
        title = result.stdout.strip().splitlines()[0] if result.returncode == 0 else ""
        # Sanitize for use as a filename
        for ch in r'\/:*?"<>|':
            title = title.replace(ch, "_")
        return title or "kalimba"

    def download_video(self, url: str) -> Path:
        video_path = self.work_dir / "video.mp4"
        cmd = [
            "yt-dlp",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "-o", str(video_path),
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp failed: {result.stderr}")
        if not video_path.exists():
            matches = list(self.work_dir.glob("video.*"))
            if matches:
                video_path = matches[0]
            else:
                raise RuntimeError("Video download failed — no output file found")
        return video_path

    def extract_frames(self, video_path: Path, interval: float = 1.0) -> Path:
        frames_dir = self.work_dir / "frames"
        frames_dir.mkdir(exist_ok=True)
        cmd = [
            "ffmpeg", "-i", str(video_path),
            "-vf", f"fps=1/{interval}",
            "-q:v", "2",
            str(frames_dir / "frame_%05d.jpg"),
            "-y",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr}")
        return frames_dir

    def download_and_extract_frames(self, url: str, interval: float = 1.0) -> tuple[Path, Path]:
        video_path = self.download_video(url)
        frames_dir = self.extract_frames(video_path, interval)
        return video_path, frames_dir

    def cleanup(self):
        shutil.rmtree(self.work_dir, ignore_errors=True)
