"""Configuration centralisée. Tout passe par les variables d'environnement.
Aucune valeur secrète en dur, aucun chemin en dur ailleurs dans le code."""
import os
from pathlib import Path


class Config:
    # --- API keys ---
    GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]

    # --- Storage ---
    JOBS_DIR: Path = Path(os.environ.get("JOBS_DIR", "/tmp/elite_jobs"))
    DOWNLOAD_DIR: Path = Path(os.environ.get("DOWNLOAD_DIR", "/tmp/elite_downloads"))

    # --- Cookies YouTube ---
    # Colle le contenu de ton cookies.txt dans cette variable d'environnement Railway.
    # Si absente, yt-dlp tente sans cookies (peut être bloqué par YouTube).
    YOUTUBE_COOKIES: str = os.environ.get("YOUTUBE_COOKIES", "")
    COOKIES_FILE: Path = Path("/tmp/elite_youtube_cookies.txt")

    # --- Gemini ---
    GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # --- Logging ---
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

    # --- Timeouts ---
    DOWNLOAD_TIMEOUT_SEC: int = int(os.environ.get("DOWNLOAD_TIMEOUT_SEC", "600"))
