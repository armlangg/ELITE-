"""Synthèse finale via Claude API (prompt 3 — game plan)."""
import json
import logging
import re

import anthropic

from .prompt3 import PROMPT_GAME_PLAN

log = logging.getLogger(__name__)


class ClaudeClient:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate_game_plan(self, opponent_name: str, gemini_analysis: str) -> dict:
        prompt = PROMPT_GAME_PLAN.format(
            opponent_name=opponent_name,
            gemini_analysis=gemini_analysis,
        )

        log.info("claude.game_plan.start opponent=%s", opponent_name)
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text
        log.info("claude.game_plan.done tokens_used=%d", message.usage.output_tokens)

        # Parser le JSON — nettoyer les éventuelles balises markdown
        clean = re.sub(r"```json\s*|\s*```", "", raw).strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            log.error("claude.json_parse_failed error=%s raw_start=%s", e, clean[:200])
            raise RuntimeError(f"Claude returned invalid JSON: {e}") from e
