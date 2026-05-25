"""Moteur de recherche agent pour ELITE.
Recherche exhaustive de tout contenu disponible sur un boxeur.
Stratégie en 4 couches :
1. Recherche directe (nom, variantes)
2. Recherche contextuelle (club, pays, entraîneur)
3. Recherche par association (adversaires, compétitions)
4. Recherche cross-plateforme (YouTube, web, réseaux sociaux)
"""
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Optional
import httpx

log = logging.getLogger(__name__)

# Pondération par type de source
SOURCE_WEIGHTS = {
    "combat_officiel_complet": 1.0,
    "combat_officiel_extrait": 0.8,
    "combat_amateur_complet": 0.9,
    "combat_amateur_extrait": 0.7,
    "sparring": 0.6,
    "highlight": 0.5,
    "interview": 0.3,
    "conference_presse": 0.3,
    "entrainement": 0.4,
    "inconnu": 0.4,
}

YOUTUBE_PLATFORMS = ["youtube.com", "youtu.be"]
SOCIAL_PLATFORMS = ["instagram.com", "facebook.com", "tiktok.com", "twitter.com", "x.com"]
VIDEO_PLATFORMS = ["dailymotion.com", "vimeo.com", "twitch.tv"]


@dataclass
class Source:
    url: str
    title: str
    platform: str
    source_type: str
    weight: float
    description: str = ""
    duration: Optional[str] = None
    published_at: Optional[str] = None
    thumbnail: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _detect_platform(url: str) -> str:
    for p in YOUTUBE_PLATFORMS + SOCIAL_PLATFORMS + VIDEO_PLATFORMS:
        if p in url:
            return p.split(".")[0]
    return "web"


def _classify_source(title: str, description: str = "") -> tuple[str, float]:
    """Classifie le type de source et retourne (type, poids)."""
    text = (title + " " + description).lower()
    if any(w in text for w in ["full fight", "combat complet", "full match", "ko", "tko", "stoppage"]):
        if any(w in text for w in ["amateur", "aiba", "olympic", "youth", "junior"]):
            return "combat_amateur_complet", SOURCE_WEIGHTS["combat_amateur_complet"]
        return "combat_officiel_complet", SOURCE_WEIGHTS["combat_officiel_complet"]
    if any(w in text for w in ["highlights", "best moments", "knockdown", "round"]):
        return "combat_officiel_extrait", SOURCE_WEIGHTS["combat_officiel_extrait"]
    if any(w in text for w in ["sparring", "spar", "entraînement training"]):
        return "sparring", SOURCE_WEIGHTS["sparring"]
    if any(w in text for w in ["interview", "press conference", "conférence"]):
        return "interview", SOURCE_WEIGHTS["interview"]
    if any(w in text for w in ["workout", "training", "pad work", "bag work"]):
        return "entrainement", SOURCE_WEIGHTS["entrainement"]
    return "inconnu", SOURCE_WEIGHTS["inconnu"]


class SearchEngine:
    def __init__(self, youtube_api_key: str, google_api_key: str, google_cx: str):
        self.youtube_key = youtube_api_key
        self.google_key = google_api_key
        self.google_cx = google_cx
        self.client = httpx.Client(timeout=15)

    def search_boxer(self, boxer_name: str, max_results: int = 20) -> list[Source]:
        """Point d'entrée principal. Recherche exhaustive en 4 couches."""
        log.info("search.start boxer=%s", boxer_name)
        all_sources: dict[str, Source] = {}

        # Couche 1 — Recherche directe YouTube
        youtube_results = self._search_youtube(boxer_name, max_results=15)
        for s in youtube_results:
            all_sources[s.url] = s

        # Couche 2 — Recherche YouTube avec variantes
        variants = self._generate_variants(boxer_name)
        for variant in variants[:3]:
            results = self._search_youtube(variant, max_results=8)
            for s in results:
                if s.url not in all_sources:
                    all_sources[s.url] = s

        # Couche 3 — Recherche web générale (articles, stats, réseaux sociaux)
        web_results = self._search_web(boxer_name, max_results=10)
        for s in web_results:
            if s.url not in all_sources:
                all_sources[s.url] = s

        # Couche 4 — Recherche YouTube combinée (boxeur + combat/fight/vs)
        for suffix in ["full fight", "combat", "knockout", "highlights"]:
            results = self._search_youtube(f"{boxer_name} {suffix}", max_results=5)
            for s in results:
                if s.url not in all_sources:
                    all_sources[s.url] = s

        sources = list(all_sources.values())

        # Trier par poids décroissant
        sources.sort(key=lambda x: x.weight, reverse=True)

        log.info("search.done boxer=%s total=%d", boxer_name, len(sources))
        return sources[:max_results]

    def _generate_variants(self, name: str) -> list[str]:
        """Génère des variantes de recherche : initiales, orthographe, surnom."""
        variants = [name]
        parts = name.strip().split()
        if len(parts) >= 2:
            # Prénom + Nom inversé
            variants.append(f"{parts[-1]} {parts[0]}")
            # Initiale prénom + Nom
            variants.append(f"{parts[0][0]}. {' '.join(parts[1:])}")
            # Juste le nom de famille
            variants.append(parts[-1])
            # Avec "boxer" ou "boxeur"
            variants.append(f"{name} boxer")
            variants.append(f"{name} boxeur")
        return variants

    def _search_youtube(self, query: str, max_results: int = 10) -> list[Source]:
        """Recherche YouTube Data API v3."""
        try:
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": max_results,
                "key": self.youtube_key,
                "relevanceLanguage": "fr",
                "safeSearch": "none",
            }
            res = self.client.get("https://www.googleapis.com/youtube/v3/search", params=params)
            res.raise_for_status()
            data = res.json()

            sources = []
            for item in data.get("items", []):
                vid_id = item["id"].get("videoId")
                if not vid_id:
                    continue
                snippet = item["snippet"]
                title = snippet.get("title", "")
                description = snippet.get("description", "")
                source_type, weight = _classify_source(title, description)
                sources.append(Source(
                    url=f"https://www.youtube.com/watch?v={vid_id}",
                    title=title,
                    platform="youtube",
                    source_type=source_type,
                    weight=weight,
                    description=description[:200],
                    published_at=snippet.get("publishedAt"),
                    thumbnail=snippet.get("thumbnails", {}).get("medium", {}).get("url"),
                ))
            log.info("youtube.search query=%s results=%d", query, len(sources))
            return sources
        except Exception as e:
            log.error("youtube.search.error query=%s error=%s", query, e)
            return []

    def _search_web(self, query: str, max_results: int = 10) -> list[Source]:
        """Google Custom Search API pour web + réseaux sociaux."""
        try:
            sources = []
            # Recherche vidéos sur réseaux sociaux
            for platform_query in [
                f"{query} site:instagram.com",
                f"{query} site:facebook.com",
                f"{query} site:tiktok.com",
                f"{query} boxe combat",
            ]:
                params = {
                    "key": self.google_key,
                    "cx": self.google_cx,
                    "q": platform_query,
                    "num": 5,
                }
                res = self.client.get("https://www.googleapis.com/customsearch/v1", params=params)
                res.raise_for_status()
                data = res.json()

                for item in data.get("items", []):
                    url = item.get("link", "")
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")
                    platform = _detect_platform(url)
                    source_type, weight = _classify_source(title, snippet)
                    sources.append(Source(
                        url=url,
                        title=title,
                        platform=platform,
                        source_type=source_type,
                        weight=weight,
                        description=snippet[:200],
                    ))

            log.info("web.search query=%s results=%d", query, len(sources))
            return sources[:max_results]
        except Exception as e:
            log.error("web.search.error query=%s error=%s", query, e)
            return []

    def close(self):
        self.client.close()
