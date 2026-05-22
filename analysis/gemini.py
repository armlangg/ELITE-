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
PROMPT_ANALYSE = """Tu es un analyste tactique expert en boxe anglaise professionnelle.
Analyse la vidéo de combat de {opponent_name} et produis une analyse tactique complete selon cette structure :

0. ANALYSE DE LA SOURCE ET FIABILITE DU MATERIEL
- Type de contenu identifie
- Coefficient de fiabilite applique (%)
- Risque d intox : oui / possible / non

1. PROFIL GENERAL
- Style de boxe, garde, distance preferee

2. ANALYSE SPATIALE
- Zones offensives, defensives, coups recus, deplacements

3. STATISTIQUES OFFENSIVES
- Frequence, efficacite, distance, signal avant-coureur par coup

4. COMBINAISONS FAVORITES
- Top 5 avec sequence, declencheur, frequence, efficacite

5. ANALYSE DEFENSIVE
C01 a C20 : defense principale, secondaire, contre, expositions, taux succes, vulnerabilite, confiance

6. FAIBLESSES STRUCTURELLES
Par priorite : description, situation, exploitation

7. CONDITIONNEMENT
Evolution par round, fatigue, fin de round, resistance

8. PSYCHOLOGIE
Pression, encaissement, difficulte, frustration

Reponds en francais. Precis, factuel, quantifie."""


class GeminiAnalyzer:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def analyze_video(self, video_path: Path, opponent_name: str) -> dict:
        log.info("gemini.upload.start path=%s", video_path)
        uploaded = self.client.files.upload(file=str(video_path))
        log.info("gemini.upload.done uri=%s", uploaded.uri)

        self._wait_until_active(uploaded.name)

        prompt = PROMPT_ANALYSE.format(opponent_name=opponent_name)
        log.info("gemini.generate.start")
        response = self.client.models.generate_content(
            model=self.model,
            contents=[uploaded, prompt],
        )
        log.info("gemini.generate.done")

        try:
            self.client.files.delete(name=uploaded.name)
        except Exception:
            pass

        return {
            "opponent": opponent_name,
            "analysis": response.text,
            "model": self.model,
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
