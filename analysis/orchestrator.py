"""Orchestrateur principal ELITE.
Flux : nom boxeur → recherche sources → analyse Gemini multi-vidéos → game plan Claude.
"""
import logging
from typing import Optional
from .search_engine import SearchEngine, Source
from .gemini import GeminiAnalyzer
from .claude_client import ClaudeClient

log = logging.getLogger(__name__)

# Nombre max de vidéos YouTube à analyser (Gemini)
MAX_VIDEO_SOURCES = 5
# Types de sources que Gemini peut visionner directement via URL
GEMINI_SUPPORTED_PLATFORMS = ["youtube"]


class Orchestrator:
    def __init__(
        self,
        search: SearchEngine,
        gemini: GeminiAnalyzer,
        claude: ClaudeClient,
    ):
        self.search = search
        self.gemini = gemini
        self.claude = claude

    def analyze_boxer(
        self,
        boxer_name: str,
        extra_urls: Optional[list[str]] = None,
    ) -> dict:
        """
        Pipeline complète :
        1. Recherche exhaustive des sources
        2. Sélection des meilleures sources analysables par Gemini
        3. Analyse Gemini de chaque source
        4. Synthèse et game plan Claude
        """
        log.info("orchestrator.start boxer=%s", boxer_name)

        # 1. Recherche
        sources = self.search.search_boxer(boxer_name, max_results=30)
        log.info("orchestrator.sources_found count=%d", len(sources))

        # Ajouter les URLs manuelles si fournies
        if extra_urls:
            for url in extra_urls:
                from .search_engine import Source, _detect_platform, _classify_source
                platform = _detect_platform(url)
                source_type, weight = _classify_source(url)
                sources.insert(0, Source(
                    url=url,
                    title=f"Source manuelle — {url}",
                    platform=platform,
                    source_type=source_type,
                    weight=weight + 0.1,  # Boost léger pour les sources manuelles
                ))

        # 2. Sélectionner les meilleures sources YouTube (Gemini peut les visionner)
        video_sources = [
            s for s in sources
            if s.platform in GEMINI_SUPPORTED_PLATFORMS
        ][:MAX_VIDEO_SOURCES]

        if not video_sources:
            raise ValueError(f"Aucune source vidéo trouvée pour {boxer_name}")

        log.info("orchestrator.analyzing videos=%d", len(video_sources))

        # 3. Analyse Gemini sur chaque vidéo
        analyses = []
        for i, source in enumerate(video_sources):
            try:
                log.info("orchestrator.gemini url=%s [%d/%d]", source.url, i+1, len(video_sources))
                result = self.gemini.analyze_video(source.url, boxer_name)
                analyses.append({
                    "source": source.to_dict(),
                    "analysis": result["analysis"],
                    "weight": source.weight,
                })
            except Exception as e:
                log.warning("orchestrator.gemini.skip url=%s error=%s", source.url, e)
                continue

        if not analyses:
            raise ValueError(f"Aucune analyse Gemini n'a abouti pour {boxer_name}")

        # 4. Synthèse Claude — fusionner toutes les analyses + game plan
        combined_analysis = self._combine_analyses(boxer_name, analyses)
        game_plan = self.claude.generate_game_plan(boxer_name, combined_analysis)

        return {
            "opponent": boxer_name,
            "sources_found": len(sources),
            "sources_analyzed": len(analyses),
            "sources": [s.to_dict() for s in sources[:10]],  # top 10 pour le dashboard
            "analyses": analyses,
            "combined_analysis": combined_analysis,
            "game_plan": game_plan,
        }

    def _combine_analyses(self, boxer_name: str, analyses: list[dict]) -> str:
        """Combine plusieurs analyses Gemini en un seul texte structuré pour Claude."""
        if len(analyses) == 1:
            return analyses[0]["analysis"]

        combined = f"# Analyses consolidées de {boxer_name} ({len(analyses)} sources)\n\n"
        for i, a in enumerate(analyses):
            source = a["source"]
            combined += f"## Source {i+1} — {source['title']} (poids: {source['weight']:.1f})\n"
            combined += f"URL: {source['url']}\n"
            combined += f"Type: {source['source_type']}\n\n"
            combined += a["analysis"]
            combined += "\n\n---\n\n"

        return combined
