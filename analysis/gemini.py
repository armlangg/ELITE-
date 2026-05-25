"""Analyse vidéo via Gemini 2.5 Flash.
Deux modes : combat (analyse visuelle) et déclaratif (interviews/vlogs).
Supporte URL directe (YouTube) et fichier local.
"""
from pathlib import Path
from typing import Union
import logging
import time

from google import genai
from google.genai import types

from .prompts import PROMPT_GEMINI_COMBAT, PROMPT_GEMINI_DECLARATIF

log = logging.getLogger(__name__)

# Mots-clés pour détecter si une source est déclarative
DECLARATIF_KEYWORDS = [
    "interview", "podcast", "vlog", "chat", "talks", "parle",
    "q&a", "day in", "behind", "coulisses", "reaction", "react",
    "challenge", "influenceur", "influencer", "feat", "with",
    "explains", "reveals", "confie", "raconte"
]


def _detect_mode(title: str, description: str = "") -> str:
    """Détecte si la source est un combat ou du contenu déclaratif."""
    text = (title + " " + description).lower()
    if any(k in text for k in DECLARATIF_KEYWORDS):
        return "declaratif"
    return "combat"


class GeminiAnalyzer:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def analyze_video(
        self,
        source: Union[Path, str],
        opponent_name: str,
        mode: str = "auto",
        title: str = "",
        description: str = "",
    ) -> dict:
        """
        source : Path (fichier local) ou str (URL YouTube/web)
        mode : "combat" | "declaratif" | "auto" (détection automatique)
        """
        if mode == "auto":
            mode = _detect_mode(title, description)

        log.info("gemini.analyze mode=%s source=%s", mode, str(source)[:80])

        if isinstance(source, str):
            return self._analyze_url(source, opponent_name, mode, title)
        else:
            return self._analyze_file(source, opponent_name, mode)

    def _get_prompt(self, opponent_name: str, mode: str) -> str:
        if mode == "declaratif":
            return PROMPT_GEMINI_DECLARATIF.format(opponent_name=opponent_name)
        return PROMPT_GEMINI_COMBAT.format(opponent_name=opponent_name)

    def _analyze_url(self, url: str, opponent_name: str, mode: str, title: str = "") -> dict:
        log.info("gemini.url.start url=%s mode=%s", url, mode)
        prompt = self._get_prompt(opponent_name, mode)

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_uri(file_uri=url, mime_type="video/mp4"),
                prompt,
            ],
        )
        log.info("gemini.url.done mode=%s", mode)
        return {
            "opponent": opponent_name,
            "analysis": response.text,
            "model": self.model,
            "mode": mode,
            "source_type": "url",
            "source": url,
            "title": title,
        }

    def _analyze_file(self, video_path: Path, opponent_name: str, mode: str) -> dict:
        log.info("gemini.upload.start path=%s mode=%s", video_path, mode)
        uploaded = self.client.files.upload(file=str(video_path))
        log.info("gemini.upload.done uri=%s", uploaded.uri)

        self._wait_until_active(uploaded.name)

        prompt = self._get_prompt(opponent_name, mode)
        response = self.client.models.generate_content(
            model=self.model,
            contents=[uploaded, prompt],
        )
        log.info("gemini.file.done mode=%s", mode)

        try:
            self.client.files.delete(name=uploaded.name)
        except Exception:
            pass

        return {
            "opponent": opponent_name,
            "analysis": response.text,
            "model": self.model,
            "mode": mode,
            "source_type": "file",
        }

    def _wait_until_active(self, file_name: str, max_wait_sec: int = 120) -> None:
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
