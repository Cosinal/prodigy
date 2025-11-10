# Orchestrator module
from __future__ import annotations

import json
from typing import Any, Dict

from agents.market_vp import MarketVP
from agents.tech_vp import TechVP
from agents.revenue_vp import RevenueVP
from core.chief_of_staff import ChiefOfStaff


class Orchestrator:
    """
    Baby CEO.

    - Takes a project brief (dict)
    - Calls VP agents (Market, Tech, Revenue) for detailed reports
    - Summarizes each into decision-level summaries
    - Aggregates results into a single "counsel summary"
    - Calls ChiefOfStaff to synthesize a founder-facing recommendation
    """

    def __init__(self) -> None:
        self.market_vp = MarketVP()
        self.tech_vp = TechVP()
        self.revenue_vp = RevenueVP()
        self.chief_of_staff = ChiefOfStaff()

    def run(self, project_brief: Dict[str, Any]) -> Dict[str, Any]:
        """Run all VP analyses and aggregate their insights."""

        # --- Market analysis ---
        market_report = self.market_vp.analyze(project_brief)
        market_summary = self.market_vp.summarize(market_report)

        # --- Tech analysis ---
        tech_report = self.tech_vp.analyze(project_brief)
        tech_summary = self.tech_vp.summarize(tech_report)

        # --- Revenue & Growth analysis ---
        revenue_report = self.revenue_vp.analyze(project_brief)
        revenue_summary = self.revenue_vp.summarize(revenue_report)

        # --- Simple aggregation logic for CEO ---
        market_score = float(market_summary.get("market_score", 0.0))
        tech_score = float(tech_summary.get("tech_score", 0.0))
        revenue_score = float(revenue_summary.get("revenue_score", 0.0))

        # Equal weighting for now
        overall_score = round(
            (market_score + tech_score + revenue_score) / 3.0,
            2,
        )

        if overall_score >= 8:
            overall_decision = "Proceed with MVP (strong across core dimensions)"
        elif overall_score >= 6:
            overall_decision = "Proceed with caution (moderate feasibility and risk)"
        else:
            overall_decision = "Do not proceed in current form (major risks or weaknesses)"

        project_info = {
            "idea_name": project_brief.get("idea_name"),
            "description": project_brief.get("description"),
        }

        overall = {
            "score": overall_score,
            "decision": overall_decision,
        }

        # Chief of Staff currently only explicitly reads market + tech,
        # but it's fine to pass revenue here for future use.
        dimensions = {
            "market": market_summary,
            "tech": tech_summary,
            "revenue": revenue_summary,
        }

        # --- Chief of Staff synthesis ---
        cos_report = self.chief_of_staff.analyze(
            project=project_info,
            overall=overall,
            dimensions=dimensions,
        )

        # --- Aggregate results for final output ---
        result: Dict[str, Any] = {
            "project": project_info,
            "reports": {
                "market": market_report,
                "tech": tech_report,
                "revenue": revenue_report,
            },
            "counsel_summary": {
                "overall_score": overall_score,
                "overall_decision": overall_decision,
                "by_dimension": {
                    "market": market_summary,
                    "tech": tech_summary,
                    "revenue": revenue_summary,
                },
                "chief_of_staff": cos_report,
            },
        }

        return result


def main() -> None:
    """Run the Orchestrator with a project brief loaded from sample_inputs.json."""

    input_path = "data/sample_inputs.json"

    with open(input_path, "r", encoding="utf-8") as f:
        project_brief = json.load(f)

    print(f"Loaded project brief from {input_path}:\n")
    print(json.dumps(project_brief, indent=2, ensure_ascii=False))

    ceo = Orchestrator()
    result = ceo.run(project_brief)

    print("\n=== Prodigy Counsel Summary (via CEO) ===")
    print(json.dumps(result["counsel_summary"], indent=2, ensure_ascii=False))

    print("\n=== Full Result Object (for debugging) ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
