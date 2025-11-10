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


REVENUE_SYSTEM_PROMPT = """
You are the VP of Revenue & Growth at Prodigy, responsible for evaluating a startup’s monetization potential and growth scalability.

You oversee four specialized employees:
1. Business Model Designer – defines how the company makes money (revenue streams, cost structure, scalability).
2. Pricing Strategist – proposes pricing models, price points, and rationales for each.
3. Unit Economics Analyst – evaluates basic financial viability (LTV, CAC, ratio, breakeven period).
4. Growth Channel Planner – identifies the best acquisition channels and growth levers.

Your job is to synthesize their collective insights into a single report.

You MUST return valid JSON matching this schema exactly (types shown as examples):

{
  "agent": "string",
  "score": "number",
  "summary": "string",
  "details": {
    "business_model": {
      "description": "string",
      "revenue_streams": ["string"],
      "cost_structure": ["string"]
    },
    "pricing_strategy": {
      "suggested_model": "string",
      "price_points": ["string"],
      "rationale": "string"
    },
    "unit_economics": {
      "cac_estimate_usd": "number",
      "ltv_estimate_usd": "number",
      "ltv_to_cac_ratio": "number",
      "breakeven_point_months": "number"
    },
    "growth_channels": {
      "primary_channels": ["string"],
      "secondary_channels": ["string"],
      "channel_notes": "string"
    }
  },
  "top_risks": ["string"],
  "assumptions": ["string"]
}

Scoring Guide:
- 9–10: Strong revenue model, scalable growth engine.
- 7–8: Healthy fundamentals, some execution risk.
- 5–6: Unclear path to sustainable revenue.
- 3–4: Unviable monetization or growth limitations.
- <3: Fundamentally flawed revenue logic.

Rules:
- Think like a CFO and CMO combined.
- Be conservative — prioritize cash flow realism and growth bottlenecks.
- Only use information implied by the startup’s brief and market context.
- Do NOT output extra commentary, reasoning, or formatting.
- Output strictly valid JSON.
"""


class RevenueVP:
    """
    VP of Revenue & Growth.

    - Builds a user prompt from the project brief
    - Calls the LLM to get structured JSON (revenue & growth report)
    - Summarizes that report into a concise counsel-style view
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model = model_name or OPENAI_MODEL

    def _build_user_prompt(self, project_brief: Dict[str, Any]) -> str:
        """
        Turn a project brief dict into a natural language prompt for the Revenue VP.
        """
        return (
            "Here is a startup idea to analyze from a REVENUE & GROWTH perspective only.\n\n"
            f"Idea name: {project_brief.get('idea_name')}\n"
            f"Description: {project_brief.get('description')}\n"
            f"Target user: {project_brief.get('target_user')}\n"
            f"Constraints: {project_brief.get('constraints')}\n"
            f"Goals: {project_brief.get('goals')}\n\n"
            "Evaluate this idea from the revenue and growth perspective using the four lenses "
            "(business model, pricing strategy, unit economics, growth channels) "
            "and fill in the JSON structure described in your system instructions."
        )

    def analyze(self, project_brief: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the LLM with the Revenue VP system prompt + user prompt,
        and parse the JSON response.
        """
        user_prompt = self._build_user_prompt(project_brief)

        response = client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": REVENUE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # Ensure agent name is set consistently
        result.setdefault("agent", "VP of Revenue & Growth")
        return result

    def summarize(self, revenue_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Turn the raw Revenue VP report into a simple, human-friendly decision summary.

        Focus on:
        - revenue potential score
        - monetization model summary
        - suggested plans & price points
        - key growth channels
        - top revenue/growth risks
        """
        score = float(revenue_report.get("score", 0.0))
        summary = revenue_report.get("summary", "")

        details = revenue_report.get("details", {}) or {}
        business_model = details.get("business_model", {}) or {}
        pricing = details.get("pricing_strategy", {}) or {}
        growth = details.get("growth_channels", {}) or {}

        monetization_summary = business_model.get("description", "")
        price_points = pricing.get("price_points", []) or []
        suggested_model = pricing.get("suggested_model", "")
        primary_channels = growth.get("primary_channels", []) or []
        secondary_channels = growth.get("secondary_channels", []) or []

        top_risks = revenue_report.get("top_risks", []) or []

        # Simple decision text based on score
        if score >= 8:
            decision = "Strong revenue potential with scalable growth engine."
        elif score >= 6:
            decision = "Promising revenue potential with notable execution or churn risks."
        elif score >= 4:
            decision = "Unclear or fragile revenue model; proceed only after further validation."
        else:
            decision = "Fundamentally weak monetization or growth model for now."

        return {
            "revenue_score": score,
            "revenue_decision": decision,
            "monetization_summary": monetization_summary or summary,
            "suggested_pricing": {
                "model": suggested_model,
                "price_points": price_points,
            },
            "key_growth_channels": {
                "primary": primary_channels,
                "secondary": secondary_channels,
            },
            "top_revenue_risks": top_risks[:3],
        }


def main() -> None:
    """
    Standalone test runner for the Revenue VP,
    using the same example project brief as the other VPs.
    """
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

    print("Calling Revenue & Growth VP for analysis...\n")

    vp = RevenueVP()
    revenue_report = vp.analyze(project_brief)

    print("=== Raw Revenue VP JSON ===")
    print(json.dumps(revenue_report, indent=2, ensure_ascii=False))

    summarized = vp.summarize(revenue_report)

    print("\n=== Revenue & Growth Counsel Summary ===")
    print(json.dumps(summarized, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
