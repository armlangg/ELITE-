"""Moteur de recherche agent pour ELITE.
Recherche exhaustive de tout contenu disponible sur un boxeur.
Stratégie en 5 couches :
1. Recherche directe (nom + boxe)
2. Recherche par variantes et orthographes
3. Recherche contextuelle (club, ville, fédération extraits des premiers résultats)
4. Recherche cross-plateforme (Instagram, Facebook, TikTok, Dailymotion)
5. Recherche par association (compétitions, adversaires)
"""
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Optional
import httpx

log = logging.getLogger(__name__)

SOURCE_WEIGHTS = {
    "combat_officiel_complet": 1.0,
    "combat_officiel_extrait": 0.8,
    "combat_amateur_complet": 0.9,
    "combat_amateur_extrait": 0.7,
    "sparring": 0.65,
    "highlight": 0.5,
    "interview": 0.55,
    "interview_technique": 0.75,
    "shadow_entrainement": 0.6,
    "inconnu": 0.4,
}

BOXING_KEYWORDS = [
    "box", "boxi", "boxing", "combat", "fight", "ko", "knockout", "punch",
    "ring", "round", "champion", "titre", "poids", "sparring", "gant",
    "uppercut", "crochet", "jab", "direct", "shadow", "sac de frappe",
    "entrainement", "training", "mbc", "ffb", "ffboxe", "aiba", "wb",
    "amateur", "compétition", "tournoi", "gala"
]

CLUB_PATTERNS = [
    r'\b(bc|bm|mbc|abc|club|gym|boxe|boxing)\s+\w+',
    r'\b(marseille|paris|lyon|nice|toulouse|bordeaux|nantes|strasbourg|montpellier|lille)\b',
]

DECLARATIF_KEYWORDS = [
    "interview", "podcast", "vlog", "chat", "talks", "parle", "q&a",
    "day in", "behind", "coulisses", "reaction", "react", "challenge",
    "influenceur", "influencer", "feat", "with", "explains", "reveals",
    "confie", "raconte", "présentation", "portrait"
]


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
    for p in ["youtube", "instagram", "facebook", "tiktok", "twitter", "x.com",
              "dailymotion", "vimeo", "twitch"]:
        if p in url:
            return p
    return "web"


def _classify_source(title: str, description: str = "") -> tuple[str, float]:
    text = (title + " " + description).lower()
    if any(w in text for w in ["full fight", "combat complet", "full match"]):
        if any(w in text for w in ["amateur", "aiba", "olympic", "youth"]):
            return "combat_amateur_complet", SOURCE_WEIGHTS["combat_amateur_complet"]
        return "combat_officiel_complet", SOURCE_WEIGHTS["combat_officiel_complet"]
    if any(w in text for w in ["ko", "knockout", "highlights", "best moments", "knockdown"]):
        return "combat_officiel_extrait", SOURCE_WEIGHTS["combat_officiel_extrait"]
    if any(w in text for w in ["sparring", "spar"]):
        return "sparring", SOURCE_WEIGHTS["sparring"]
    if any(w in text for w in ["shadow", "shadowboxing", "sac de frappe", "pad work", "mitaines"]):
        return "shadow_entrainement", SOURCE_WEIGHTS["shadow_entrainement"]
    if any(w in text for w in DECLARATIF_KEYWORDS):
        if any(w in text for w in ["technique", "tactique", "stratégie", "préparation", "camp"]):
            return "interview_technique", SOURCE_WEIGHTS["interview_technique"]
        return "interview", SOURCE_WEIGHTS["interview"]
    if any(w in text for w in ["workout", "training", "entrainement"]):
        return "shadow_entrainement", SOURCE_WEIGHTS["shadow_entrainement"]
    return "inconnu", SOURCE_WEIGHTS["inconnu"]


def _is_boxing_related(title: str, description: str = "") -> bool:
    text = (title + " " + description).lower()
    return any(k in text for k in BOXING_KEYWORDS)


def _extract_context(sources: list) -> dict:
    """Extrait le club, la ville et les infos contextuelles des premiers résultats."""
    context = {"clubs": set(), "cities": set(), "competitions": set()}
    for s in sources[:10]:
        text = (s.title + " " + s.description).lower()
        # Clubs
        for pattern in CLUB_PATTERNS:
            matches = re.findall(pattern, text)
            for m in matches:
                if len(m) > 2:
                    context["clubs"].add(m.strip())
        # Compétitions
        for kw in ["championnat", "tournoi", "gala", "coupe", "open", "national", "régional"]:
            if kw in text:
                idx = text.find(kw)
                context["competitions"].add(text[max(0,idx-5):idx+25].strip())
    return {k: list(v)[:3] for k, v in context.items()}


class SearchEngine:
    def __init__(self, youtube_api_key: str, google_api_key: str, google_cx: str):
        self.youtube_key = youtube_api_key
        self.google_key = google_api_key
        self.google_cx = google_cx
        self.client = httpx.Client(timeout=15)

    def search_boxer(self, boxer_name: str, max_results: int = 30) -> list[Source]:
        log.info("search.start boxer=%s", boxer_name)
        all_sources: dict[str, Source] = {}

        # ── Couche 1 : Recherche directe YouTube avec contexte boxe ──────────
        for query in [
            f"{boxer_name} boxe boxing",
            f"{boxer_name} combat fight",
            f"{boxer_name} boxeur knockout",
        ]:
            for s in self._search_youtube(query, max_results=10):
                if s.url not in all_sources:
                    all_sources[s.url] = s

        # ── Couche 2 : Variantes orthographiques ─────────────────────────────
        for variant in self._generate_variants(boxer_name)[:4]:
            for s in self._search_youtube(f"{variant} boxe", max_results=5):
                if s.url not in all_sources:
                    all_sources[s.url] = s

        # ── Couche 3 : Contexte extrait (club, compétitions) ─────────────────
        context = _extract_context(list(all_sources.values()))
        for club in context["clubs"]:
            for s in self._search_youtube(f"{boxer_name} {club}", max_results=5):
                if s.url not in all_sources:
                    all_sources[s.url] = s
            for s in self._search_web(f"{boxer_name} {club} boxe", max_results=3):
                if s.url not in all_sources:
                    all_sources[s.url] = s

        # ── Couche 4 : Multi-plateformes ─────────────────────────────────────
        platforms = [
            ("instagram.com", f"{boxer_name} boxe"),
            ("instagram.com", f"{boxer_name} boxing sparring"),
            ("facebook.com", f"{boxer_name} boxe combat"),
            ("tiktok.com", f"{boxer_name} boxing"),
            ("dailymotion.com", f"{boxer_name} boxe"),
        ]
        for site, query in platforms:
            for s in self._search_web(query, max_results=4, site=site):
                if s.url not in all_sources:
                    s.weight = max(s.weight, 0.55)
                    all_sources[s.url] = s

        # Recherche club sur Instagram (très utile pour amateurs)
        for club in context["clubs"]:
            for s in self._search_web(f"{club} boxe", max_results=3, site="instagram.com"):
                if s.url not in all_sources:
                    all_sources[s.url] = s

        # ── Couche 5 : Fédérations et compétitions ───────────────────────────
        for query in [
            f"{boxer_name} ffboxe fédération",
            f"{boxer_name} championnat régional national",
            f"{boxer_name} gala boxe",
        ]:
            for s in self._search_web(query, max_results=3):
                if s.url not in all_sources:
                    all_sources[s.url] = s

        sources = list(all_sources.values())

        # Filtrer hors sujet si on a assez de sources boxe
        boxing = [s for s in sources if _is_boxing_related(s.title, s.description)]
        if len(boxing) >= 3:
            sources = boxing

        sources.sort(key=lambda x: x.weight, reverse=True)
        log.info("search.done boxer=%s total=%d boxing=%d", boxer_name, len(sources), len(boxing))
        return sources[:max_results]

    def _generate_variants(self, name: str) -> list[str]:
        variants = [name]
        parts = name.strip().split()
        if len(parts) >= 2:
            variants.append(f"{parts[-1]} {parts[0]}")
            variants.append(f"{parts[0][0]}. {' '.join(parts[1:])}")
            variants.append(parts[-1])
            variants.append(parts[0])
        return variants

    def _search_youtube(self, query: str, max_results: int = 10) -> list[Source]:
        try:
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": max_results,
                "key": self.youtube_key,
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
            log.info("youtube.search query=%s results=%d", query[:50], len(sources))
            return sources
        except Exception as e:
            log.error("youtube.search.error query=%s error=%s", query[:50], e)
            return []

    def _search_web(self, query: str, max_results: int = 10, site: str = None) -> list[Source]:
        try:
            sources = []
            queries = [f"{query} site:{site}"] if site else [
                f"{query} site:instagram.com",
                f"{query} site:facebook.com",
                f"{query} site:tiktok.com",
                f"{query} boxe",
            ]
            per_query = max(2, max_results // len(queries))
            for q in queries:
                params = {
                    "key": self.google_key,
                    "cx": self.google_cx,
                    "q": q,
                    "num": min(per_query, 5),
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
            log.info("web.search query=%s results=%d", query[:50], len(sources))
            return sources[:max_results]
        except Exception as e:
            log.error("web.search.error query=%s error=%s", query[:50], e)
            return []

    def close(self):
        self.client.close()
