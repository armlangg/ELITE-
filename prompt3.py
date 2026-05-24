"""Prompt 3 — Game plan Claude (synthèse finale pour le boxeur)."""

PROMPT_GAME_PLAN = """Tu es un préparateur tactique expert en boxe professionnelle.

À partir de l'analyse ci-dessous de l'adversaire {opponent_name}, produis un game plan complet structuré en JSON strict.

---
ANALYSE GEMINI :
{gemini_analysis}
---

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après, sans balises markdown.

Structure JSON exacte à respecter :

{{
  "opponent": "{opponent_name}",
  "profile": {{
    "style": "description courte du style",
    "stance": "orthodox | southpaw",
    "preferred_distance": "courte | mi-distance | longue",
    "key_traits": ["trait1", "trait2", "trait3"]
  }},
  "heatmap_body": {{
    "offensive": {{
      "head": 0.0,
      "chin": 0.0,
      "body": 0.0,
      "liver": 0.0,
      "solar_plexus": 0.0
    }},
    "received": {{
      "head": 0.0,
      "chin": 0.0,
      "body": 0.0,
      "liver": 0.0,
      "solar_plexus": 0.0
    }},
    "note": "les valeurs sont des fréquences relatives entre 0 et 1, somme = 1"
  }},
  "heatmap_ring": {{
    "preferred_zones": {{
      "center": 0.0,
      "ropes": 0.0,
      "corner": 0.0,
      "open_space": 0.0
    }},
    "vulnerable_zones": ["zone1", "zone2"]
  }},
  "combinations_analysis": {{
    "top_combinations": [
      {{
        "rank": 1,
        "sequence": ["coup1", "coup2"],
        "frequency_pct": 0.0,
        "efficiency_pct": 0.0,
        "trigger": "situation qui déclenche cette combinaison",
        "counter": "comment la contrer"
      }}
    ],
    "note": "utilise les noms de coups standards : jab, direct, crochet_gauche, crochet_droit, uppercut_gauche, uppercut_droit, direct_corps_gauche, direct_corps_droit. Top 5 minimum, top 10 si données suffisantes."
  }},
  "defense_profile": {{
    "primary_defense": "description",
    "secondary_defense": "description",
    "main_weaknesses": [
      {{
        "weakness": "description",
        "priority": "haute | moyenne | basse",
        "how_to_exploit": "instruction tactique précise"
      }}
    ]
  }},
  "conditioning": {{
    "stamina_rating": 0,
    "fade_phase": "début | milieu | fin",
    "fade_round_estimate": 0,
    "notes": "observations sur la gestion de l'effort"
  }},
  "psychology": {{
    "under_pressure": "comportement sous pression",
    "frustration_triggers": ["trigger1", "trigger2"],
    "mental_strengths": ["force1"],
    "mental_weaknesses": ["faiblesse1"]
  }},
  "game_plan": {{
    "global_strategy": "phrase résumant la stratégie globale en 2-3 lignes",
    "phases": {{
      "opening": {{
        "label": "Rounds 1-3",
        "objective": "objectif de phase",
        "instructions": ["instruction1", "instruction2", "instruction3"]
      }},
      "middle": {{
        "label": "Rounds 4-8",
        "objective": "objectif de phase",
        "instructions": ["instruction1", "instruction2", "instruction3"]
      }},
      "closing": {{
        "label": "Rounds 9+",
        "objective": "objectif de phase",
        "instructions": ["instruction1", "instruction2", "instruction3"]
      }}
    }},
    "key_rules": [
      "règle absolue 1 à retenir",
      "règle absolue 2 à retenir",
      "règle absolue 3 à retenir"
    ]
  }},
  "pdf_summary": "Texte narratif d'une page (400-500 mots maximum) destiné à être lu la veille du combat. Ton direct, concis, pratique. Structure : stratégie globale → phases → 3 règles absolues → point mental. Pas de bullet points, prose fluide."
}}
"""
