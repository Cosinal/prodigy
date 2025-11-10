import os
import json
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI

# 1. Load environment variables (API key, model name)
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in your .env file")

client = OpenAI(api_key=OPENAI_API_KEY)


MARKET_SYSTEM_PROMPT = """
You are the **Market Analyst (VP of Market & Strategy)** in an AI product advisory organization called Prodigy.

Your job is to evaluate startup ideas strictly from the **market perspective**.

For each idea you receive, you MUST:
1. Analyze it using FOUR lenses:
   - TAM/SAM/SOM (market size and focus)
   - Competitive landscape
   - Trends & timing
   - Target customer & key pain points

2. Assign a **market attractiveness score** from 0 to 10 (higher is better).

3. Identify the main **market-related risks** and **assumptions**.

You MUST respond with a **single JSON object** that matches this structure exactly:

{
  "agent": string,  // e.g. "Market Analyst (VP of Market & Strategy)"
  "score": number,  // 0–10
  "summary": string,  // 2–4 sentence overview of the market situation
  "details": {
    "tam_sam_som": {
      "tam_description": string,
      "sam_description": string,
      "som_focus": string
    },
    "competitive_landscape": {
      "notable_competitors": [string],
      "differentiation": string
    },
    "trend_insights": [string],
    "target_user_profile": {
      "persona": string,
      "key_pain_points": [string]
    }
  },
  "risks": [string],
  "assumptions": [string]
}

Rules:
- Think through each of the four lenses internally, but DO NOT include your reasoning steps.
- Only output valid JSON that conforms to the structure above.
- Do not include any additional fields, comments, or explanation outside of the JSON.
"""


class MarketVP:
    """
    Market Analyst (VP of Market & Strategy).

    This class:
    - Builds the user prompt from a project brief
    - Calls the LLM to get structured JSON
    - Provides a helper to summarize that JSON into a simple decision
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model = model_name or OPENAI_MODEL

    def _build_user_prompt(self, project_brief: Dict[str, Any]) -> str:
        """
        Turn a project brief dict into a natural language prompt for the Market VP.
        """
        return (
            "Here is a startup idea to analyze from a MARKET perspective only.\n\n"
            f"Idea name: {project_brief.get('idea_name')}\n"
            f"Description: {project_brief.get('description')}\n"
            f"Target user: {project_brief.get('target_user')}\n"
            f"Constraints: {project_brief.get('constraints')}\n"
            f"Goals: {project_brief.get('goals')}\n\n"
            "Evaluate this idea from the market perspective using the four lenses "
            "(TAM/SAM/SOM, competitive landscape, trends & timing, target customer & pain points) "
            "and fill in the JSON structure described in your system instructions."
        )

    def analyze(self, project_brief: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the LLM with the Market VP system prompt + user prompt,
        and parse the JSON response.
        """
        user_prompt = self._build_user_prompt(project_brief)

        response = client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": MARKET_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # Make sure agent name is set
        result.setdefault("agent", "Market Analyst (VP of Market & Strategy)")
        return result

    def summarize(self, market_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Turn the raw Market VP report into a simple, human-friendly decision summary.
        This is like a baby Chief of Staff, but only for the market dimension.
        """
        score = float(market_report.get("score", 0.0))
        summary = market_report.get("summary", "")
        risks = market_report.get("risks", [])

        if score >= 8:
            decision = "Proceed with MVP (market looks strong)"
        elif score >= 6:
            decision = "Proceed with caution (market is okay but has notable risks)"
        else:
            decision = "Do not proceed in current form (market seems weak or risky)"

        return {
            "market_score": score,
            "market_decision": decision,
            "market_summary": summary,
            "top_risks": risks[:3],  # show just the top 3 for now
        }


def main() -> None:
    # Example project brief (same as before)
    project_brief = {
        "idea_name": "AutoApply AI",
        "description": (
            "An AI platform that automatically applies to freelance jobs on behalf of a user, "
            "using their portfolio, preferences, and work history to tailor applications."
        ),
        "target_user": "Freelancers on platforms like Upwork and Fiverr",
        "constraints": {
            "build_budget_usd": 1500,
            "build_time_weeks": 4,
        },
        "goals": {
            "objective": "Validate whether this idea is worth building and get an MVP plan",
            "time_horizon_months": 3,
        },
    }

    print("Calling Market VP for market analysis...\n")

    vp = MarketVP()
    market_report = vp.analyze(project_brief)

    print("=== Raw Market VP JSON ===")
    print(json.dumps(market_report, indent=2, ensure_ascii=False))

    interpreted = vp.summarize(market_report)

    print("\n=== Market Counsel Summary ===")
    print(json.dumps(interpreted, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
