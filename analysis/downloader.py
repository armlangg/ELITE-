"""Téléchargement de vidéos via yt-dlp (API Python)."""
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
        outtmpl = str(self.download_dir / f"{file_id}.%(ext)s")

        ydl_opts = {
            "outtmpl": outtmpl,
            "quiet": False,
            "no_warnings": False,
        }

        if self.cookies_file and self.cookies_file.exists():
            ydl_opts["cookiefile"] = str(self.cookies_file)
            log.info("download.using_cookies path=%s", self.cookies_file)

        # --- Debug : lister les formats disponibles avant de télécharger ---
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "cookiefile": ydl_opts.get("cookiefile")}) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = info.get("formats", [])
                format_summary = [(f.get("format_id"), f.get("ext"), f.get("height"), f.get("vcodec"), f.get("acodec")) for f in formats]
                log.info("available_formats count=%d formats=%s", len(formats), format_summary[:10])
        except Exception as e:
            log.warning("format_debug failed: %s", e)

        log.info("download.start url=%s", url)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except yt_dlp.utils.DownloadError as e:
            raise DownloadError(f"yt-dlp failed: {e}") from e

        matches = list(self.download_dir.glob(f"{file_id}.*"))
        if not matches:
            raise DownloadError("yt-dlp returned OK but no file produced")

        output = matches[0]
        log.info("download.done path=%s size=%d", output, output.stat().st_size)
        return output
