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
        file_id = str(uuid.uuid4())
        # On laisse yt-dlp choisir l'extension via %(ext)s
        outtmpl = str(self.download_dir / f"{file_id}.%(ext)s")

        ydl_opts = {
            "format": "18/worst[vcodec!=none][acodec!=none]",
            "outtmpl": outtmpl,
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

        # Trouver le fichier téléchargé (extension inconnue à l'avance)
        matches = list(self.download_dir.glob(f"{file_id}.*"))
        if not matches:
            raise DownloadError("yt-dlp returned OK but no file produced")

        output = matches[0]
        log.info("download.done path=%s size=%d", output, output.stat().st_size)
        return output
