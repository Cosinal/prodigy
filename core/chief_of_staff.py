# Chief of Staff module
from __future__ import annotations

import os
import json
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in your .env file")

client = OpenAI(api_key=OPENAI_API_KEY)


CHIEF_SYSTEM_PROMPT = """
You are the **Chief of Staff for Prodigy**, an AI product counsel organization.

Your job is to take structured reports from several VP-level agents (Market, Tech, etc.) and turn them into a clear, concise, founder-facing recommendation.

You DO NOT generate new raw analysis.
Instead, you:
- Read the existing scores and summaries from each VP.
- Identify the most important patterns, trade-offs, and tensions.
- Turn this into a small set of key insights and recommended next steps.

You MUST respond with a single JSON object that matches this structure exactly (types shown as examples):

{
  "agent": "string",
  "overall_headline": "string",
  "overall_verdict": "string",
  "overall_score": "number",
  "dimension_summary": {
    "market": "string",
    "tech": "string"
  },
  "key_insights": ["string"],
  "recommended_next_steps": ["string"],
  "validation_tasks": ["string"],
  "major_risks_to_watch": ["string"]
}

Definitions:
- "overall_headline": A one-sentence TL;DR for the founder.
- "overall_verdict": Your concise recommendation (e.g., "Proceed with a tightly scoped MVP", "Validate demand before writing significant code").
- "overall_score": The overall numeric score given by the Orchestrator (you may slightly adjust if you think it better reflects the synthesis, but only if justified by the VP summaries).
- "dimension_summary": One or two sentences per dimension (market, tech) translating the VP summaries into plain founder language.
- "key_insights": 3–7 bullet-style strings capturing the critical takeaways from all dimensions.
- "recommended_next_steps": 3–7 specific actions the founder should take next.
- "validation_tasks": 2–5 assumptions or questions to test in the real world.
- "major_risks_to_watch": 2–5 of the most important risks that could materially kill or derail the idea.

Rules:
- Do NOT invent new facts beyond what is reasonably implied by the VP summaries.
- Do NOT output your internal reasoning.
- Only output valid JSON that conforms to the structure above.
- Do NOT include any additional fields, comments, or explanations outside of the JSON.
"""


class ChiefOfStaff:
    """
    Chief of Staff for Prodigy.

    Takes:
    - project info
    - overall score + decision from the Orchestrator
    - per-dimension summaries (market, tech, etc.)

    Returns:
    - a synthesized, founder-facing recommendation JSON.
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model = model_name or OPENAI_MODEL

    def _build_user_prompt(
        self,
        project: Dict[str, Any],
        overall: Dict[str, Any],
        dimensions: Dict[str, Dict[str, Any]],
    ) -> str:
        idea_name = project.get("idea_name", "Unknown idea")
        description = project.get("description", "")

        overall_score = overall.get("score", 0.0)
        overall_decision = overall.get("decision", "")

        market = dimensions.get("market", {}) or {}
        tech = dimensions.get("tech", {}) or {}

        market_score = market.get("market_score", None)
        market_summary = market.get("market_summary", "")
        market_risks = market.get("top_risks", [])

        tech_score = tech.get("tech_score", None)
        tech_summary = tech.get("tech_summary", "")
        tech_risks = tech.get("top_tech_risks", [])

        return (
            "You are given the following context from the Prodigy Orchestrator.\n\n"
            f"Project:\n"
            f"- Idea name: {idea_name}\n"
            f"- Description: {description}\n\n"
            "Overall decision from CEO:\n"
            f"- Overall score: {overall_score}\n"
            f"- Overall decision: {overall_decision}\n\n"
            "Per-dimension summaries:\n"
            "Market:\n"
            f"- Market score: {market_score}\n"
            f"- Market summary: {market_summary}\n"
            f"- Market top risks: {market_risks}\n\n"
            "Tech:\n"
            f"- Tech score: {tech_score}\n"
            f"- Tech summary: {tech_summary}\n"
            f"- Tech top risks: {tech_risks}\n\n"
            "Using ONLY this information, synthesize your JSON response according to your system instructions."
        )

    def analyze(
        self,
        project: Dict[str, Any],
        overall: Dict[str, Any],
        dimensions: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Call the LLM with the CoS system prompt + user prompt,
        and parse the JSON response.
        """
        user_prompt = self._build_user_prompt(project, overall, dimensions)

        response = client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": CHIEF_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        result.setdefault("agent", "Chief of Staff (Prodigy Counsel)")
        return result
