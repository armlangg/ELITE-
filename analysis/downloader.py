"""Téléchargement de vidéos via yt-dlp (API Python).
Pas de dépendance Flask/jobs : module pur, testable unitairement."""
from pathlib import Path
import logging
import uuid

import yt_dlp

log = logging.getLogger(__name__)


class DownloadError(Exception):
    pass


class VideoDownloader:
    def __init__(self, download_dir: Path, cookies_file: Path = None, timeout_sec: int = 600):
        self.download_dir = download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_file = cookies_file
        self.timeout_sec = timeout_sec

    def download(self, url: str) -> Path:
        filename = f"{uuid.uuid4()}.mp4"
        output = self.download_dir / filename

        ydl_opts = {
            "format": "best[height<=480][ext=mp4]/best[height<=480]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "outtmpl": str(output),
            "quiet": True,
            "no_warnings": False,
        }

        if self.cookies_file and self.cookies_file.exists():
            ydl_opts["cookiefile"] = str(self.cookies_file)
            log.info("download.using_cookies path=%s", self.cookies_file)

        log.info("download.start url=%s", url)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except yt_dlp.utils.DownloadError as e:
            raise DownloadError(f"yt-dlp failed: {e}") from e

        if not output.exists():
            raise DownloadError("yt-dlp returned OK but no file produced")

        log.info("download.done path=%s size=%d", output, output.stat().st_size)
        return output
