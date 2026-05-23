"""Téléchargement de vidéos via yt-dlp (API Python)."""
from pathlib import Path
import logging
import os
import shutil
import subprocess
import uuid

import yt_dlp

log = logging.getLogger(__name__)


class DownloadError(Exception):
    pass


def _find_binary(name: str) -> str | None:
    candidate = shutil.which(name)
    if candidate:
        return candidate
    try:
        result = subprocess.run(
            ["find", "/nix/store", "-name", name, "-type", "f"],
            capture_output=True, text=True, timeout=5
        )
        lines = [l for l in result.stdout.splitlines() if f"/bin/{name}" in l]
        if lines:
            return sorted(lines)[-1]  # version la plus récente
    except Exception:
        pass
    return None


def _patch_path_with_runtimes():
    """Ajoute les répertoires de deno/node/ffmpeg au PATH pour que yt-dlp les trouve."""
    extra_dirs = set()
    for binary in ["deno", "node", "nodejs", "ffmpeg"]:
        path = _find_binary(binary)
        if path:
            log.info("runtime.found %s=%s", binary, path)
            extra_dirs.add(str(Path(path).parent))
        else:
            log.warning("runtime.missing binary=%s", binary)

    if extra_dirs:
        current_path = os.environ.get("PATH", "")
        os.environ["PATH"] = ":".join(extra_dirs) + ":" + current_path
        log.info("PATH.patched added=%s", extra_dirs)


# Patch PATH une seule fois au chargement du module
_patch_path_with_runtimes()


class VideoDownloader:
    def __init__(self, download_dir: Path, cookies_file: Path = None, timeout_sec: int = 600):
        self.download_dir = download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_file = cookies_file
        self.timeout_sec = timeout_sec
        self.ffmpeg = shutil.which("ffmpeg")
        log.info("ffmpeg.which=%s", self.ffmpeg or "NOT FOUND")

    def download(self, url: str) -> Path:
        file_id = str(uuid.uuid4())
        outtmpl = str(self.download_dir / f"{file_id}.%(ext)s")

        ydl_opts = {
            "outtmpl": outtmpl,
            "quiet": False,
            "format": "best[vcodec!=none][acodec!=none]/worst[vcodec!=none][acodec!=none]",
            "extractor_args": {
                "youtube": {
                    "player_client": ["web"],
                    "player_skip": ["webpage", "configs"],
                }
            },
        }

        if self.ffmpeg:
            ydl_opts["ffmpeg_location"] = self.ffmpeg

        # Cookies désactivés temporairement (SSAP experiment)
        # if self.cookies_file and self.cookies_file.exists():
            #     ydl_opts["cookiefile"] = str(self.cookies_file)
            #     log.info("download.using_cookies")

        log.info("download.start url=%s", url)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except yt_dlp.utils.DownloadError as e:
            raise DownloadError(f"yt-dlp failed: {e}") from e

        matches = list(self.download_dir.glob(f"{file_id}.*"))
        if not matches:
            raise DownloadError("yt-dlp returned OK but no file produced")

        raw = matches[0]
        log.info("download.raw path=%s size=%d ext=%s", raw, raw.stat().st_size, raw.suffix)

        if self.ffmpeg:
            return self._convert_to_h264(raw)
        return raw

    def _convert_to_h264(self, source: Path) -> Path:
        output = source.with_name(source.stem + "_h264.mp4")
        cmd = [
            self.ffmpeg, "-y", "-i", str(source),
            "-c:v", "libx264", "-preset", "fast", "-crf", "28",
            "-c:a", "aac", "-b:a", "128k",
            str(output)
        ]
        log.info("ffmpeg.convert.start %s -> %s", source.name, output.name)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            log.error("ffmpeg.convert.failed stderr=%s", result.stderr[-300:])
            return source
        source.unlink(missing_ok=True)
        log.info("ffmpeg.convert.done size=%d", output.stat().st_size)
        return output
