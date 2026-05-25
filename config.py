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

    # --- Claude ---
    CLAUDE_API_KEY: str = os.environ.get("CLAUDE_API_KEY", "")
    CLAUDE_MODEL: str = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

    # --- Tarification Pro ---
    PRICE_PRO_MINOR: int = int(os.environ.get("PRICE_PRO_MINOR", "49"))
    PRICE_PRO_MEDIUM: int = int(os.environ.get("PRICE_PRO_MEDIUM", "99"))
    PRICE_PRO_MAJOR: int = int(os.environ.get("PRICE_PRO_MAJOR", "149"))
    PRICE_PRO_EXCEPTIONAL: int = int(os.environ.get("PRICE_PRO_EXCEPTIONAL", "299"))

    # --- Tarification Amateur ---
    PRICE_AMATEUR_MINOR: int = int(os.environ.get("PRICE_AMATEUR_MINOR", "29"))
    PRICE_AMATEUR_MEDIUM: int = int(os.environ.get("PRICE_AMATEUR_MEDIUM", "59"))
    PRICE_AMATEUR_MAJOR: int = int(os.environ.get("PRICE_AMATEUR_MAJOR", "89"))
    PRICE_AMATEUR_EXCEPTIONAL: int = int(os.environ.get("PRICE_AMATEUR_EXCEPTIONAL", "129"))

    # --- Search APIs ---
    YOUTUBE_API_KEY: str = os.environ.get("YOUTUBE_API_KEY", "")
    GOOGLE_SEARCH_API_KEY: str = os.environ.get("GOOGLE_SEARCH_API_KEY", "")
    GOOGLE_SEARCH_ENGINE_ID: str = os.environ.get("GOOGLE_SEARCH_ENGINE_ID", "")
