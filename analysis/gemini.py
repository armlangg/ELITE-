"""Analyse vidéo via Gemini 2.0 Flash (Google Gen AI SDK).
Module pur : pas de Flask, pas de Job. Entrée = fichier + nom adversaire. Sortie = dict."""
from pathlib import Path
import logging
import time

from google import genai

log = logging.getLogger(__name__)


# ============================================================================
# PROMPT 1 — Analyse vidéo boxe par Gemini
# ============================================================================
# REMPLACE ce placeholder par ton vrai prompt 1 (celui déjà dans app.py actuellement).
# Garde le placeholder {opponent_name} si tu veux injecter dynamiquement le nom.
PROMPT_BOXING_ANALYSIS = """Tu es un analyste technique de boxe professionnelle.
Analyse la vidéo de combat de {opponent_name} et produis une analyse tactique
quantitative et qualitative (à compléter avec le vrai prompt).
"""


class GeminiAnalyzer:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def analyze_video(self, video_path: Path, opponent_name: str) -> dict:
        # 1. Upload du fichier vers Gemini Files API
        log.info("gemini.upload.start path=%s", video_path)
        uploaded = self.client.files.upload(file=str(video_path))
        log.info("gemini.upload.done uri=%s", uploaded.uri)

        # 2. Attendre que le fichier soit ACTIVE (Gemini doit le traiter avant analyse)
        self._wait_until_active(uploaded.name)

        # 3. Génération de l'analyse
        prompt = PROMPT_BOXING_ANALYSIS.format(opponent_name=opponent_name)
        log.info("gemini.generate.start")
        response = self.client.models.generate_content(
            model=self.model,
            contents=[uploaded, prompt],
        )
        log.info("gemini.generate.done")

        return {
            "opponent": opponent_name,
            "analysis": response.text,
            "model": self.model,
            "video_uri": uploaded.uri,
        }

    def _wait_until_active(self, file_name: str, max_wait_sec: int = 120) -> None:
        """Gemini doit pré-traiter la vidéo avant de pouvoir l'analyser.
        On poll jusqu'à ACTIVE ou timeout."""
        start = time.time()
        while time.time() - start < max_wait_sec:
            f = self.client.files.get(name=file_name)
            state = getattr(f.state, "name", str(f.state))
            if state == "ACTIVE":
                return
            if state == "FAILED":
                raise RuntimeError(f"Gemini file processing FAILED for {file_name}")
            time.sleep(2)
        raise RuntimeError(f"Gemini file did not become ACTIVE in {max_wait_sec}s")
