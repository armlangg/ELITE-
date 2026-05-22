"""Téléchargement de vidéos via yt-dlp.
Pas de dépendance Flask/jobs : module pur, testable unitairement."""
from pathlib import Path
import logging
import subprocess
import uuid

log = logging.getLogger(__name__)


class DownloadError(Exception):
    pass


class VideoDownloader:
    def __init__(self, download_dir: Path, timeout_sec: int = 600):
        self.download_dir = download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_sec = timeout_sec

    def download(self, url: str) -> Path:
        filename = f"{uuid.uuid4()}.mp4"
        output = self.download_dir / filename

        cmd = [
            "yt-dlp",
            "-f", "best[ext=mp4]/best",
            "-o", str(output),
            "--no-playlist",
            url,
        ]
        log.info("download.start url=%s", url)
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout_sec
            )
        except subprocess.TimeoutExpired:
            raise DownloadError(f"yt-dlp timeout after {self.timeout_sec}s")

        if result.returncode != 0:
            stderr = result.stderr[:500] if result.stderr else "no stderr"
            raise DownloadError(f"yt-dlp failed (code {result.returncode}): {stderr}")

        if not output.exists():
            raise DownloadError("yt-dlp returned 0 but no file produced")

        log.info("download.done path=%s size=%d", output, output.stat().st_size)
        return output
