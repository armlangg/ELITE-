"""Configuration centralisée. Tout passe par les variables d'environnement.
Aucune valeur secrète en dur, aucun chemin en dur ailleurs dans le code."""
import os
from pathlib import Path


class Config:
    # --- API keys ---
    GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]

    # --- Storage ---
    # En MVP : /tmp (perdu au restart Railway, acceptable).
    # Pour migrer vers Redis : remplacer FileJobStore par RedisJobStore dans app.py.
    JOBS_DIR: Path = Path(os.environ.get("JOBS_DIR", "/tmp/elite_jobs"))
    DOWNLOAD_DIR: Path = Path(os.environ.get("DOWNLOAD_DIR", "/tmp/elite_downloads"))

    # --- Gemini ---
    GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    # --- Logging ---
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

    # --- Timeouts ---
    DOWNLOAD_TIMEOUT_SEC: int = int(os.environ.get("DOWNLOAD_TIMEOUT_SEC", "600"))
