"""
Orchestrator module - Hierarchical execution with context passing and VP querying.

Architecture:
    Round 1: Market VP (foundation - market reality)
    Round 2: Product VP (reads Market - what users want)
    Round 3: Tech VP + Revenue VP (read Market + Product - parallel execution)
    Round 4: Ops VP (reads everything - feasibility check)
    Round 5: Chief of Staff (synthesizes with query_vp tool)
    Round 6: Devil's Advocate (challenges weak assumptions, optional)
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, Optional

from agents.market_vp import MarketVP
from agents.tech_vp import TechVP
from agents.revenue_vp import RevenueVP
from agents.ops_vp import OperationsVP
from agents.product_vp import ProductUXVP
from core.chief_of_staff import ChiefOfStaff
from core.devils_advocate import DevilsAdvocate


class Orchestrator:
    """
    CEO - Orchestrates hierarchical VP analysis with context passing.

    Key improvements over v1:
    1. Sequential execution with information flow (VPs see previous analysis)
    2. Chief of Staff can query VPs for clarification
    3. Devil's Advocate challenges weak assumptions
    4. Better conflict resolution between VPs
    """

    def __init__(self) -> None:
        self.market_vp = MarketVP()
        self.tech_vp = TechVP()
        self.revenue_vp = RevenueVP()
        self.ops_vp = OperationsVP()
        self.product_vp = ProductUXVP()
        self.chief_of_staff = ChiefOfStaff()
        self.devils_advocate = DevilsAdvocate()

    def run(self, project_brief: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute hierarchical VP analysis with context passing.

        Returns:
            Complete counsel report with all VP analyses and synthesis
        """

        # ============================================================
        # ROUND 1: Market VP (Foundation)
        # ============================================================
        print("🔍 Round 1: Market VP analysis...")
        market_report = self.market_vp.analyze(project_brief, context=None)
        market_summary = self.market_vp.summarize(market_report)

        # ============================================================
        # ROUND 2: Product VP (reads Market)
        # ============================================================
        print("🎨 Round 2: Product VP analysis (informed by Market)...")
        product_context = {
            "market_summary": market_summary,
            "market_details": market_report.get("details", {}),
        }
        product_report = self.product_vp.analyze(project_brief, context=product_context)
        product_summary = self.product_vp.summarize(product_report)

        # ============================================================
        # ROUND 3: Tech + Revenue VPs (read Market + Product, parallel)
        # ============================================================
        print("⚙️  Round 3: Tech & Revenue VP analysis (informed by Market + Product)...")
        
        tech_revenue_context = {
            "market_summary": market_summary,
            "market_details": market_report.get("details", {}),
            "product_summary": product_summary,
            "product_details": product_report.get("details", {}),
        }
        
        # These run in parallel conceptually (both have same inputs)
        tech_report = self.tech_vp.analyze(project_brief, context=tech_revenue_context)
        tech_summary = self.tech_vp.summarize(tech_report)
        
        revenue_report = self.revenue_vp.analyze(project_brief, context=tech_revenue_context)
        revenue_summary = self.revenue_vp.summarize(revenue_report)

        # ============================================================
        # ROUND 4: Ops VP (reads everything)
        # ============================================================
        print("📋 Round 4: Operations VP analysis (informed by all previous)...")
        ops_context = {
            "market_summary": market_summary,
            "product_summary": product_summary,
            "tech_summary": tech_summary,
            "revenue_summary": revenue_summary,
            "tech_details": tech_report.get("details", {}),
            "revenue_details": revenue_report.get("details", {}),
        }
        ops_report = self.ops_vp.analyze(project_brief, context=ops_context)
        ops_summary = self.ops_vp.summarize(ops_report)

        # ============================================================
        # Aggregate scores
        # ============================================================
        market_score = float(market_summary.get("market_score", 0.0))
        tech_score = float(tech_summary.get("tech_score", 0.0))
        revenue_score = float(revenue_summary.get("revenue_score", 0.0))
        ops_score = float(ops_summary.get("ops_score", 0.0))
        product_score = float(product_summary.get("product_score", 0.0))

        overall_score = round(
            (market_score + tech_score + revenue_score + ops_score + product_score) / 5.0,
            2,
        )

        # Score variance (for Devil's Advocate trigger)
        scores = [market_score, tech_score, revenue_score, ops_score, product_score]
        score_variance = max(scores) - min(scores)

        # Decision logic
        if overall_score >= 8:
            overall_decision = "Proceed with MVP (strong across all dimensions)"
        elif overall_score >= 6:
            overall_decision = "Proceed with focused execution (solid opportunity with manageable risks)"
        elif overall_score >= 4:
            overall_decision = "Proceed with caution (significant challenges, consider pivots)"
        else:
            overall_decision = "Do not proceed in current form (major risks across multiple dimensions)"

        # Collect all reports
        all_reports = {
            "market": market_report,
            "tech": tech_report,
            "revenue": revenue_report,
            "ops": ops_report,
            "product": product_report,
        }

        all_summaries = {
            "market": market_summary,
            "tech": tech_summary,
            "revenue": revenue_summary,
            "ops": ops_summary,
            "product": product_summary,
        }

        # ============================================================
        # ROUND 5: Chief of Staff (with query_vp tool)
        # ============================================================
        print("🎯 Round 5: Chief of Staff synthesis...")
        
        project_info = {
            "idea_name": project_brief.get("idea_name"),
            "description": project_brief.get("description"),
        }
        
        overall_info = {
            "score": overall_score,
            "decision": overall_decision,
        }

        # Create query_vp function for Chief of Staff
        query_vp_fn = self._create_query_vp_function(project_brief, all_reports)

        cos_report = self.chief_of_staff.synthesize(
            project=project_info,
            overall=overall_info,
            dimensions=all_summaries,
            full_reports=all_reports,
            query_vp_fn=query_vp_fn,
        )

        # ============================================================
        # ROUND 6: Devil's Advocate (if needed)
        # ============================================================
        devils_advocate_result = None
        
        if self._should_run_devils_advocate(overall_score, score_variance, cos_report):
            print("😈 Round 6: Devil's Advocate challenge...")
            
            devils_advocate_result = self.devils_advocate.challenge(
                project_brief=project_brief,
                all_reports=all_reports,
                all_summaries=all_summaries,
                counsel_summary=cos_report,
                overall_score=overall_score,
            )
            
            # If Devil's Advocate flags critical issues requiring re-analysis
            if devils_advocate_result.get("requires_re_analysis"):
                print("🔄 Re-analyzing based on Devil's Advocate feedback...")
                
                vps_to_rerun_raw = devils_advocate_result.get("vps_to_rerun", [])
                updated_reports = self._re_analyze_vps(
                    project_brief, 
                    all_reports, 
                    vps_to_rerun_raw,
                    devils_advocate_result.get("guidance", "")
                )
                
                # Update reports and summaries (updated_reports already has normalized keys)
                all_reports.update(updated_reports)
                for vp_name, report in updated_reports.items():
                    vp_agent = getattr(self, f"{vp_name}_vp")
                    all_summaries[vp_name] = vp_agent.summarize(report)
                
                # Recalculate overall score using all VPs (since some were updated)
                overall_score = round(
                    sum([
                        all_summaries["market"].get("market_score", 0.0),
                        all_summaries["tech"].get("tech_score", 0.0),
                        all_summaries["revenue"].get("revenue_score", 0.0),
                        all_summaries["ops"].get("ops_score", 0.0),
                        all_summaries["product"].get("product_score", 0.0),
                    ]) / 5.0,
                    2,
                )
                
                # Re-synthesize with Chief of Staff (no query tool second time)
                print("🎯 Re-synthesizing with Chief of Staff...")
                cos_report = self.chief_of_staff.synthesize(
                    project=project_info,
                    overall={"score": overall_score, "decision": overall_decision},
                    dimensions=all_summaries,
                    full_reports=all_reports,
                    query_vp_fn=None,  # No second round of queries
                )

        # ============================================================
        # Build final result
        # ============================================================
        result: Dict[str, Any] = {
            "project": project_info,
            "reports": all_reports,
            "counsel_summary": {
                "overall_score": overall_score,
                "overall_decision": overall_decision,
                "by_dimension": all_summaries,
                "chief_of_staff": cos_report,
            },
        }
        
        # Include Devil's Advocate result if it ran
        if devils_advocate_result:
            result["devils_advocate"] = devils_advocate_result

        return result

    def _create_query_vp_function(
        self, 
        project_brief: Dict[str, Any],
        all_reports: Dict[str, Any],
    ) -> Callable:
        """
        Create a function that allows Chief of Staff to query specific VPs.

        Args:
            project_brief: Original project brief
            all_reports: All VP reports (for context)

        Returns:
            Function that queries a VP with a specific question
        """
        def query_vp(vp_name: str, question: str) -> Dict[str, Any]:
            """
            Query a specific VP with a clarification question.

            Args:
                vp_name: Name of VP to query (market, tech, revenue, ops, product)
                question: Specific question to ask

            Returns:
                VP's response to the question
            """
            vp_map = {
                "market": self.market_vp,
                "tech": self.tech_vp,
                "revenue": self.revenue_vp,
                "ops": self.ops_vp,
                "product": self.product_vp,
            }

            vp = vp_map.get(vp_name)
            if not vp:
                return {"error": f"Unknown VP: {vp_name}"}

            # Build lightweight clarification prompt
            clarification_context = {
                "original_report": all_reports.get(vp_name, {}),
                "question": question,
                "is_clarification": True,
            }

            # Use VP's existing analyze method but with clarification context
            try:
                response = vp.analyze(project_brief, context=clarification_context)
                return response
            except Exception as e:
                return {"error": f"Failed to query {vp_name}: {str(e)}"}

        return query_vp

    def _should_run_devils_advocate(
        self,
        overall_score: float,
        score_variance: float,
        cos_report: Dict[str, Any],
    ) -> bool:
        """
        Determine if Devil's Advocate should run.

        Triggers:
        1. Overall score < 7.5 (borderline decision)
        2. High score variance (>3.0) between VPs (conflicting signals)
        3. COS flags "high uncertainty" or "requires validation"

        Args:
            overall_score: Aggregated score
            score_variance: Difference between max and min VP scores
            cos_report: Chief of Staff report

        Returns:
            True if Devil's Advocate should challenge assumptions
        """
        # Always run for borderline cases
        if overall_score < 7.5:
            return True

        # Run if VPs strongly disagree
        if score_variance > 3.0:
            return True

        # Run if COS flags uncertainty
        cos_verdict = cos_report.get("overall_verdict", "").lower()
        if any(word in cos_verdict for word in ["uncertain", "unclear", "validation needed", "needs testing"]):
            return True

        return False

    def _normalize_vp_name(self, vp_name: str) -> Optional[str]:
        """
        Normalize VP name from various formats to internal key format.
        
        Handles:
        - "Tech VP" -> "tech"
        - "tech VP" -> "tech"
        - "Tech" -> "tech"
        - "tech" -> "tech"
        - "Product & UX VP" -> "product"
        - "Operations VP" -> "ops"
        
        Args:
            vp_name: VP name in any format
            
        Returns:
            Normalized VP key (market, tech, revenue, ops, product) or None if not found
        """
        vp_name_lower = vp_name.lower().strip()
        
        # Remove "VP" suffix if present
        vp_name_lower = vp_name_lower.replace(" vp", "").replace("vp", "").strip()
        
        # Map various formats to internal keys
        vp_name_mapping = {
            "market": "market",
            "tech": "tech",
            "technology": "tech",
            "revenue": "revenue",
            "ops": "ops",
            "operations": "ops",
            "product": "product",
            "product & ux": "product",
            "product and ux": "product",
            "ux": "product",
        }
        
        return vp_name_mapping.get(vp_name_lower)

    def _re_analyze_vps(
        self,
        project_brief: Dict[str, Any],
        all_reports: Dict[str, Any],
        vps_to_rerun: list[str],
        guidance: str,
    ) -> Dict[str, Any]:
        """
        Re-run specific VPs with updated guidance from Devil's Advocate.

        Args:
            project_brief: Original project brief
            all_reports: Current VP reports
            vps_to_rerun: List of VP names to re-analyze (may be in various formats)
            guidance: Guidance from Devil's Advocate

        Returns:
            Updated reports for re-run VPs (keys are normalized to lowercase)
        """
        updated_reports = {}
        
        vp_map = {
            "market": self.market_vp,
            "tech": self.tech_vp,
            "revenue": self.revenue_vp,
            "ops": self.ops_vp,
            "product": self.product_vp,
        }

        for vp_name_raw in vps_to_rerun:
            # Normalize VP name to internal key format
            vp_name = self._normalize_vp_name(vp_name_raw)
            if not vp_name:
                print(f"  ⚠️  Unknown VP name: {vp_name_raw}, skipping...")
                continue
            
            vp_agent = vp_map.get(vp_name)
            if not vp_agent:
                print(f"  ⚠️  VP agent not found for: {vp_name}, skipping...")
                continue
            
            print(f"  🔄 Re-running {vp_name} VP with updated guidance...")

            # Add Devil's Advocate guidance to context
            re_analysis_context = {
                "devils_advocate_guidance": guidance,
                "previous_report": all_reports.get(vp_name, {}),
                "is_re_analysis": True,
            }

            try:
                updated_report = vp_agent.analyze(project_brief, context=re_analysis_context)
                updated_reports[vp_name] = updated_report  # Use normalized key
            except Exception as e:
                print(f"  ⚠️  Failed to re-run {vp_name}: {e}")

        return updated_reports


def main() -> None:
    """Run the Orchestrator with a project brief loaded from sample_inputs.json."""

    input_path = "data/sample_inputs.json"

    with open(input_path, "r", encoding="utf-8") as f:
        project_brief = json.load(f)

    print("="*60)
    print("🚀 PRODIGY AI COUNSEL - V2 (Hierarchical)")
    print("="*60)
    print(f"\nLoaded project brief from {input_path}:\n")
    print(json.dumps(project_brief, indent=2, ensure_ascii=False))
    print("\n" + "="*60)
    print("Running Hierarchical VP Advisory Board...")
    print("="*60 + "\n")

    ceo = Orchestrator()
    result = ceo.run(project_brief)

    print("\n" + "="*60)
    print("📊 COUNSEL SUMMARY")
    print("="*60)
    print(json.dumps(result["counsel_summary"], indent=2, ensure_ascii=False))

    if "devils_advocate" in result:
        print("\n" + "="*60)
        print("😈 DEVIL'S ADVOCATE CHALLENGE")
        print("="*60)
        print(json.dumps(result["devils_advocate"], indent=2, ensure_ascii=False))

    print("\n" + "="*60)
    print("🔍 FULL DETAILED REPORTS (Debug View)")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()