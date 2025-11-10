# Tech VP Agent
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


TECH_SYSTEM_PROMPT = """
You are the **Tech Architect (VP of Engineering)** in an AI product advisory organization called Prodigy.

Your job is to evaluate startup ideas strictly from the **technical perspective**.

For each idea you receive, you MUST analyze it through FOUR lenses:
1) Feasibility (how hard is it to build, roughly how long, and infra cost?)
2) Architecture (high-level components, models, and services)
3) Data pipeline (what data is needed, how to get it, and how to store it)
4) Reliability & risk (scalability, security/privacy, and failure modes)

You MUST assign a **technical feasibility score** from 0 to 10 (higher = easier / safer to build with current tools and within constraints).

You MUST respond with a single JSON object that matches this structure exactly, using the types shown:

{
  "agent": "string", 
  "score": "number", 
  "summary": "string",
  "details": {
    "feasibility": {
      "complexity_level": "string", 
      "estimated_build_time_weeks": "number", 
      "estimated_monthly_infra_cost_usd": "number", 
      "key_technical_challenges": ["string"]
    },
    "architecture": {
      "high_level_components": ["string"], 
      "models_and_services": ["string"], 
      "data_flow_summary": "string"
    },
    "data_pipeline": {
      "required_data_sources": ["string"], 
      "collection_method": "string", 
      "storage_strategy": "string", 
      "data_quality_risks": ["string"]
    },
    "reliability_and_risk": {
      "scalability_concerns": ["string"], 
      "security_privacy_concerns": ["string"], 
      "operational_failure_modes": ["string"]
    }
  },
  "top_risks": ["string"],
  "assumptions": ["string"]
}

Rules:
- Think through each of the four lenses internally, but DO NOT include your reasoning steps.
- Only output valid JSON that conforms to the structure above.
- Do not include any additional fields, comments, or explanation outside of the JSON.
"""


class TechVP:
    """
    Tech Architect (VP of Engineering).

    This class:
    - Builds the user prompt from a project brief
    - Calls the LLM to get structured JSON
    - Provides a helper to summarize that JSON into a simple tech decision
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model = model_name or OPENAI_MODEL

    def _build_user_prompt(self, project_brief: Dict[str, Any]) -> str:
        """
        Turn a project brief dict into a natural language prompt for the Tech VP.
        """
        return (
            "Here is a startup idea to analyze from a TECHNICAL perspective only.\n\n"
            f"Idea name: {project_brief.get('idea_name')}\n"
            f"Description: {project_brief.get('description')}\n"
            f"Target user: {project_brief.get('target_user')}\n"
            f"Constraints: {project_brief.get('constraints')}\n"
            f"Goals: {project_brief.get('goals')}\n\n"
            "Evaluate this idea from the technical perspective using the four lenses "
            "(feasibility, architecture, data pipeline, reliability & risk) "
            "and fill in the JSON structure described in your system instructions."
        )

    def analyze(self, project_brief: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the LLM with the Tech VP system prompt + user prompt,
        and parse the JSON response.
        """
        user_prompt = self._build_user_prompt(project_brief)

        response = client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": TECH_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # Make sure agent name is set
        result.setdefault("agent", "Tech Architect (VP of Engineering)")
        return result

    def summarize(self, tech_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Turn the raw Tech VP report into a simple, human-friendly decision summary.

        Focus on:
        - tech feasibility score
        - suggested architecture (high-level components)
        - main dependencies (models & services)
        - top 3 tech risks
        """
        score = float(tech_report.get("score", 0.0))
        summary = tech_report.get("summary", "")

        details = tech_report.get("details", {}) or {}
        architecture = details.get("architecture", {}) or {}
        high_level_components = architecture.get("high_level_components", []) or []
        models_and_services = architecture.get("models_and_services", []) or []

        top_risks = tech_report.get("top_risks", []) or []

        if score >= 8:
            decision = "Technically strong and feasible within typical startup constraints."
        elif score >= 6:
            decision = "Technically feasible but with notable complexity or risks."
        else:
            decision = "Technically challenging or risky for an early-stage build."

        return {
            "tech_score": score,
            "tech_decision": decision,
            "tech_summary": summary,
            "suggested_architecture": {
                "high_level_components": high_level_components,
                "main_dependencies": models_and_services,
            },
            "top_tech_risks": top_risks[:3],
        }


def main() -> None:
    # Example project brief (same idea we used for Market VP)
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

    print("Calling Tech VP for technical analysis...\n")

    vp = TechVP()
    tech_report = vp.analyze(project_brief)

    print("=== Raw Tech VP JSON ===")
    print(json.dumps(tech_report, indent=2, ensure_ascii=False))

    interpreted = vp.summarize(tech_report)

    print("\n=== Tech Counsel Summary ===")
    print(json.dumps(interpreted, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
