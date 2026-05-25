"""Synthèse finale via Claude API — game plan + ATI + tarification."""
import json
import logging
import re

import anthropic

from .prompts import PROMPT_CLAUDE_GAMEPLAN, PROMPT_CLAUDE_SYNTHESE

log = logging.getLogger(__name__)


class ClaudeClient:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        # Modèle rapide pour la synthèse passe 1
        self.fast_model = "claude-haiku-4-5-20251001"

    def synthesize_analyses(self, opponent_name: str, combined_analysis: str, nb_analyses: int) -> str:
        """Passe 1 — Synthèse rapide avec Haiku."""
        prompt = PROMPT_CLAUDE_SYNTHESE.format(
            opponent_name=opponent_name,
            combined_analysis=combined_analysis,
            nb_analyses=nb_analyses,
        )
        log.info("claude.synthesize.start opponent=%s", opponent_name)
        message = self.client.messages.create(
            model=self.fast_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        result = message.content[0].text
        log.info("claude.synthesize.done tokens=%d", message.usage.output_tokens)
        return result

    def generate_game_plan(
        self,
        opponent_name: str,
        combined_analysis: str,
        nb_analyses: int = 1,
        price_minor: int = 49,
        price_medium: int = 99,
        price_major: int = 149,
        price_exceptional: int = 299,
    ) -> dict:
        prompt = PROMPT_CLAUDE_GAMEPLAN.format(
            opponent_name=opponent_name,
            combined_analysis=combined_analysis,
            nb_analyses=nb_analyses,
            price_minor=price_minor,
            price_medium=price_medium,
            price_major=price_major,
            price_exceptional=price_exceptional,
        )

        log.info("claude.game_plan.start opponent=%s sources=%d", opponent_name, nb_analyses)
        message = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text
        log.info("claude.game_plan.done tokens=%d", message.usage.output_tokens)

        clean = re.sub(r"```json\s*|\s*```", "", raw).strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            log.error("claude.json_parse_failed error=%s", e)
            raise RuntimeError(f"Claude returned invalid JSON: {e}") from e
