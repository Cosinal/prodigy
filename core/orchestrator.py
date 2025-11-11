# Orchestrator module - Updated for 5 VPs
from __future__ import annotations

import json
from typing import Any, Dict

from agents.market_vp import MarketVP
from agents.tech_vp import TechVP
from agents.revenue_vp import RevenueVP
from agents.ops_vp import OperationsVP
from agents.product_vp import ProductUXVP
from core.chief_of_staff import ChiefOfStaff


class Orchestrator:
    """
    CEO - Runs all 5 VP agents and synthesizes their counsel.

    Flow:
    1. Market VP runs first (defines target user, willingness to pay)
    2. Tech VP runs second (uses market constraints)
    3. Revenue VP runs third (uses market + tech insights)
    4. Ops VP runs fourth (uses all previous insights)
    5. Product & UX VP runs last (uses full context from all VPs)
    6. Chief of Staff synthesizes everything into founder-facing guidance
    """

    def __init__(self) -> None:
        self.market_vp = MarketVP()
        self.tech_vp = TechVP()
        self.revenue_vp = RevenueVP()
        self.ops_vp = OperationsVP()
        self.product_vp = ProductUXVP()
        self.chief_of_staff = ChiefOfStaff()

    def run(self, project_brief: Dict[str, Any]) -> Dict[str, Any]:
        """Run all VP analyses and aggregate their insights."""

        print("🔍 Running Market VP analysis...")
        market_report = self.market_vp.analyze(project_brief)
        market_summary = self.market_vp.summarize(market_report)

        print("⚙️  Running Tech VP analysis...")
        tech_report = self.tech_vp.analyze(project_brief)
        tech_summary = self.tech_vp.summarize(tech_report)

        print("💰 Running Revenue VP analysis...")
        revenue_report = self.revenue_vp.analyze(project_brief)
        revenue_summary = self.revenue_vp.summarize(revenue_report)

        print("📋 Running Operations VP analysis...")
        ops_report = self.ops_vp.analyze(project_brief)
        ops_summary = self.ops_vp.summarize(ops_report)

        print("🎨 Running Product & UX VP analysis...")
        # Product VP gets context from other VPs
        context = {
            "market": market_report.get("details", {}),
            "tech": tech_report.get("details", {}),
            "revenue": revenue_report.get("details", {}),
            "ops": ops_report.get("details", {}),
        }
        product_report = self.product_vp.analyze(project_brief, context=context)
        product_summary = self.product_vp.summarize(product_report)

        # --- Aggregate scores (equal weighting for now) ---
        market_score = float(market_summary.get("market_score", 0.0))
        tech_score = float(tech_summary.get("tech_score", 0.0))
        revenue_score = float(revenue_summary.get("revenue_score", 0.0))
        ops_score = float(ops_summary.get("ops_score", 0.0))
        product_score = float(product_summary.get("product_score", 0.0))

        overall_score = round(
            (market_score + tech_score + revenue_score + ops_score + product_score) / 5.0,
            2,
        )

        # --- Decision logic ---
        if overall_score >= 8:
            overall_decision = "Proceed with MVP (strong across all dimensions)"
        elif overall_score >= 6:
            overall_decision = "Proceed with focused execution (solid opportunity with manageable risks)"
        elif overall_score >= 4:
            overall_decision = "Proceed with caution (significant challenges, consider pivots)"
        else:
            overall_decision = "Do not proceed in current form (major risks across multiple dimensions)"

        project_info = {
            "idea_name": project_brief.get("idea_name"),
            "description": project_brief.get("description"),
        }

        overall = {
            "score": overall_score,
            "decision": overall_decision,
        }

        # All dimension summaries for Chief of Staff
        dimensions = {
            "market": market_summary,
            "tech": tech_summary,
            "revenue": revenue_summary,
            "ops": ops_summary,
            "product": product_summary,
        }

        # Full reports for Chief of Staff (for deeper synthesis)
        full_reports = {
            "market": market_report,
            "tech": tech_report,
            "revenue": revenue_report,
            "ops": ops_report,
            "product": product_report,
        }

        print("🎯 Running Chief of Staff synthesis...")
        cos_report = self.chief_of_staff.analyze(
            project=project_info,
            overall=overall,
            dimensions=dimensions,
            full_reports=full_reports,  # Pass full reports for deeper synthesis
        )

        # --- Final result object ---
        result: Dict[str, Any] = {
            "project": project_info,
            "reports": full_reports,
            "counsel_summary": {
                "overall_score": overall_score,
                "overall_decision": overall_decision,
                "by_dimension": dimensions,
                "chief_of_staff": cos_report,
            },
        }

        return result


def main() -> None:
    """Run the Orchestrator with a project brief loaded from sample_inputs.json."""

    input_path = "data/sample_inputs.json"

    with open(input_path, "r", encoding="utf-8") as f:
        project_brief = json.load(f)

    print("="*60)
    print("🚀 PRODIGY AI COUNSEL")
    print("="*60)
    print(f"\nLoaded project brief from {input_path}:\n")
    print(json.dumps(project_brief, indent=2, ensure_ascii=False))
    print("\n" + "="*60)
    print("Running VP Advisory Board...")
    print("="*60 + "\n")

    ceo = Orchestrator()
    result = ceo.run(project_brief)

    print("\n" + "="*60)
    print("📊 COUNSEL SUMMARY (CEO View)")
    print("="*60)
    print(json.dumps(result["counsel_summary"], indent=2, ensure_ascii=False))

    print("\n" + "="*60)
    print("🔍 FULL DETAILED REPORTS (Debug View)")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()