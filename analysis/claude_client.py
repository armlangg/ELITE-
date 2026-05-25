"""Synthèse finale via Claude API — game plan + ATI + tarification."""
import json
import logging
import re

import anthropic

from .prompts import PROMPT_CLAUDE_GAMEPLAN

log = logging.getLogger(__name__)


class ClaudeClient:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate_game_plan(
        self,
        opponent_name: str,
        combined_analysis: str,
        nb_analyses: int = 1,
    ) -> dict:
        prompt = PROMPT_CLAUDE_GAMEPLAN.format(
            opponent_name=opponent_name,
            combined_analysis=combined_analysis,
            nb_analyses=nb_analyses,
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
