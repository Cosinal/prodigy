# Chief of Staff module - Enhanced with query_vp capability
from __future__ import annotations

import os
import json
from typing import Any, Callable, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in your .env file")

client = OpenAI(api_key=OPENAI_API_KEY)


CHIEF_SYSTEM_PROMPT = """
You are the **Chief of Staff for Prodigy**, an AI counsel organization for startup founders.

Your job is to synthesize reports from 5 VP-level agents (Market, Tech, Revenue, Ops, Product & UX) into clear, actionable, founder-facing guidance.

You DO NOT generate new analysis. Instead, you:
- Identify key patterns, tensions, and synergies across all dimensions
- Translate VP-speak into plain founder language
- Create a cohesive execution plan based on all VP insights
- Highlight the most critical risks and next steps

**Context: Bootstrap startup founders**
- Limited time and money
- Need actionable steps, not theory
- Want to know: "Should I build this? If yes, how?"

You MUST respond with valid JSON matching this structure:

{
  "agent": "Chief of Staff",
  "overall_headline": "string (one-sentence TL;DR)",
  "overall_verdict": "string (clear recommendation)",
  "overall_score": number,
  "dimension_summary": {
    "market": "string (1-2 sentences)",
    "tech": "string (1-2 sentences)",
    "revenue": "string (1-2 sentences)",
    "ops": "string (1-2 sentences)",
    "product": "string (1-2 sentences)"
  },
  "key_insights": ["string (3-7 insights synthesizing across VPs)"],
  "recommended_next_steps": ["string (3-7 specific actions, prioritized)"],
  "validation_tasks": ["string (2-5 assumptions to test in real world)"],
  "major_risks_to_watch": ["string (2-5 most critical risks)"]
}

**Synthesis Guidelines:**

1. **Find connections across VPs:**
   - Market says "target Reddit" + Revenue says "organic growth" + Ops says "5hrs/week support" → Execution plan
   - Tech says "CLI" + Product says "founders need web UI" → Tension to resolve
   - All VPs flag "OpenAI dependency" → Major risk requiring mitigation

2. **Translate to action:**
   - Bad: "Market conditions are favorable"
   - Good: "Launch on r/startups Week 3 with '$50 validation' offer"

3. **Prioritize ruthlessly:**
   - What must happen in Week 1-2? (Build MVP)
   - What must happen in Week 3-8? (Get first 10 customers)
   - What can wait until later? (Polish, scaling, automation)

4. **Be honest about tensions:**
   - If Tech says "2 weeks" but Ops says "30hrs/week needed" → Call out time commitment
   - If Product says "need web UI" but Tech says "CLI faster" → Suggest tradeoff

5. **Focus on validation:**
   - Founders need to prove this works, not build the perfect product
   - Emphasize getting to first 10 paying customers fast

Rules:
- Do NOT invent facts beyond what VPs reported
- Do NOT output reasoning or explanations outside JSON
- Be concise and actionable
- Founder should know exactly what to do next after reading this
"""

QUERY_DECISION_PROMPT = """
You are the Chief of Staff analyzing VP reports. You've noticed potential conflicts or unclear recommendations.

You have the ability to query a specific VP to clarify their recommendation.

Given the current synthesis and VP reports, should you query a VP for clarification?

Respond with JSON:
{{
  "should_query": boolean,
  "vp_name": "market|tech|revenue|ops|product" (if should_query is true),
  "question": "string (specific question to ask the VP)" (if should_query is true),
  "reason": "string (why you need this clarification)"
}}

**When to query:**
- Clear contradiction between VPs (e.g., Tech says CLI, Product says web UI needed)
- Unclear implementation path (e.g., Revenue suggests pricing but Tech doesn't specify payment system)
- Missing critical information (e.g., Market identifies target but Product doesn't address their needs)

**When NOT to query:**
- Minor differences in opinion (VPs can disagree slightly)
- Information that can be inferred from context
- Nice-to-have clarifications (only query what's critical)

**Limit: You can only make 2 queries total, so choose wisely.**

Current VP summaries:
{vp_summaries}

Current synthesis direction:
{current_thinking}

Should you query a VP? If yes, which one and what question?
"""


class ChiefOfStaff:
    """
    Chief of Staff for Prodigy - Synthesizes all VP reports into founder guidance.

    Takes:
    - project info (idea name, description)
    - overall score + decision from Orchestrator
    - dimension summaries (from all 5 VPs)
    - full reports (optional, for deeper synthesis)
    - query_vp_fn (optional, allows querying VPs for clarification)

    Returns:
    - Synthesized, founder-facing recommendation JSON
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model = model_name or OPENAI_MODEL

    def _build_user_prompt(
        self,
        project: Dict[str, Any],
        overall: Dict[str, Any],
        dimensions: Dict[str, Dict[str, Any]],
        full_reports: Dict[str, Dict[str, Any]] = None,
        has_query_tool: bool = False,
    ) -> str:
        """Build comprehensive prompt with all VP context."""
        
        idea_name = project.get("idea_name", "Unknown idea")
        description = project.get("description", "")

        overall_score = overall.get("score", 0.0)
        overall_decision = overall.get("decision", "")

        prompt = f"""You are synthesizing Prodigy counsel for:

**Project:** {idea_name}
**Description:** {description}

**CEO Overall Assessment:**
- Score: {overall_score}/10
- Decision: {overall_decision}

---

## VP Summaries

"""

        # Add all 5 VP summaries
        vp_names = {
            "market": "Market VP",
            "tech": "Tech VP", 
            "revenue": "Revenue VP",
            "ops": "Operations VP",
            "product": "Product & UX VP"
        }

        for key, name in vp_names.items():
            vp = dimensions.get(key, {})
            if not vp:
                continue
                
            prompt += f"### {name}\n"
            
            # Score
            score_key = f"{key}_score"
            if score_key in vp:
                prompt += f"- Score: {vp[score_key]}/10\n"
            
            # Decision
            decision_key = f"{key}_decision"
            if decision_key in vp:
                prompt += f"- Decision: {vp[decision_key]}\n"
            
            # Summary
            summary_key = f"{key}_summary"
            if summary_key in vp:
                prompt += f"- Summary: {vp[summary_key]}\n"
            
            # Top risks
            risk_key = f"top_{key}_risks" if key != "product" else "top_ux_risks"
            if risk_key in vp:
                risks = vp[risk_key][:2]  # Top 2 risks per VP
                if risks:
                    prompt += f"- Top Risks: {', '.join(risks)}\n"
            
            # Clarifications (if any were added from query_vp)
            if "clarification" in vp:
                clarification = vp['clarification']
                # Parse if it's a JSON string
                if isinstance(clarification, str):
                    try:
                        clarification = json.loads(clarification)
                        # Extract the summary from the clarification
                        clarification_summary = clarification.get('summary', clarification)
                    except:
                        clarification_summary = clarification
                else:
                    clarification_summary = clarification
                prompt += f"- **Clarification:** {clarification_summary}\n"
            
            prompt += "\n"

        # Add key details from full reports if available
        if full_reports:
            prompt += "---\n\n## Key Details from Full Reports\n\n"
            
            # Market details
            if "market" in full_reports:
                market = full_reports["market"].get("details", {})
                tam_sam = market.get("tam_sam_som", {})
                if tam_sam.get("som_focus"):
                    prompt += f"**Market - First Customers:** {tam_sam['som_focus']}\n\n"
            
            # Tech details
            if "tech" in full_reports:
                tech = full_reports["tech"].get("details", {})
                arch = tech.get("architecture", {})
                components = arch.get("high_level_components", [])
                if components:
                    prompt += f"**Tech - Architecture:** {components[0]}\n\n"
            
            # Revenue details
            if "revenue" in full_reports:
                revenue = full_reports["revenue"].get("details", {})
                pricing = revenue.get("pricing_strategy", {})
                if pricing.get("suggested_model"):
                    prompt += f"**Revenue - Pricing:** {pricing['suggested_model']}\n"
                if pricing.get("price_points"):
                    prompt += f"  Price points: {', '.join(pricing['price_points'][:2])}\n\n"
            
            # Ops details
            if "ops" in full_reports:
                ops = full_reports["ops"].get("details", {})
                exec_plan = ops.get("execution_plan", {})
                milestones = exec_plan.get("milestones", [])
                if milestones:
                    prompt += f"**Ops - Timeline:** {len(milestones)} phases planned\n"
                    if milestones[0]:
                        phase1 = milestones[0]
                        prompt += f"  Phase 1 ({phase1.get('phase', 'MVP')}): {phase1.get('timeline', 'TBD')}\n\n"
            
            # Product details
            if "product" in full_reports:
                product = full_reports["product"].get("details", {})
                pmf = product.get("pmf_readiness", {})
                if pmf.get("usability_score") and pmf.get("delight_score"):
                    prompt += f"**Product - PMF Readiness:** Usability {pmf['usability_score']}/10, Delight {pmf['delight_score']}/10\n\n"

        prompt += """---

Based on ALL of the above context, synthesize your Chief of Staff counsel.

**Your synthesis should:**
1. Connect insights across VPs (e.g., Market's target + Revenue's pricing + Ops's timeline = execution plan)
2. Resolve tensions (e.g., if Tech says CLI but Product says web UI, recommend which for MVP)
3. Prioritize next steps (Week 1-2 actions vs Week 3-8 vs defer to V2)
4. Be actionable (founder should know exactly what to do after reading this)

"""

        if has_query_tool:
            prompt += """
**NOTE:** You have already queried VPs for clarification. Use their clarifications to resolve any tensions.

"""

        prompt += """
Respond with ONLY valid JSON matching your schema. No additional text.
"""

        return prompt

    def _detect_conflicts(self, dimensions: Dict[str, Dict[str, Any]]) -> str:
        """
        Analyze VP summaries to detect potential conflicts.
        
        Returns:
            Description of conflicts found, or empty string if none
        """
        conflicts = []
        
        # Check Tech vs Product conflict (CLI vs UI)
        tech_summary = dimensions.get("tech", {}).get("tech_summary", "").lower()
        product_summary = dimensions.get("product", {}).get("product_summary", "").lower()
        
        if "cli" in tech_summary and ("web" in product_summary or "ui" in product_summary):
            conflicts.append("Tech VP suggests CLI, but Product VP may prefer web UI")
        
        # Check score variance
        scores = []
        for key in ["market", "tech", "revenue", "ops", "product"]:
            score_key = f"{key}_score"
            score = dimensions.get(key, {}).get(score_key, 0.0)
            if score:
                scores.append((key, score))
        
        if scores:
            max_vp, max_score = max(scores, key=lambda x: x[1])
            min_vp, min_score = min(scores, key=lambda x: x[1])
            
            if max_score - min_score > 3.0:
                conflicts.append(f"{max_vp.title()} scored {max_score} while {min_vp.title()} scored {min_score} - significant disagreement")
        
        return "; ".join(conflicts) if conflicts else ""

    def _ask_for_query(
        self,
        current_synthesis: Dict[str, Any],
        dimensions: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Ask COS if it wants to query a VP for clarification.
        
        Args:
            current_synthesis: Current synthesis result
            dimensions: All VP summaries
            
        Returns:
            Query decision with vp_name and question if should_query is True
        """
        conflicts = self._detect_conflicts(dimensions)
        
        # If no conflicts detected, skip query
        if not conflicts:
            return {"should_query": False}
        
        prompt = QUERY_DECISION_PROMPT.format(
            vp_summaries=json.dumps(dimensions, indent=2),
            current_thinking=conflicts
        )
        
        response = client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are the Chief of Staff deciding whether to query a VP."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,  # Lower temperature for decision-making
        )
        
        content = response.choices[0].message.content
        return json.loads(content)

    def synthesize(
        self,
        project: Dict[str, Any],
        overall: Dict[str, Any],
        dimensions: Dict[str, Dict[str, Any]],
        full_reports: Dict[str, Dict[str, Any]] = None,
        query_vp_fn: Optional[Callable[[str, str], Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize VP reports with optional VP querying capability.
        
        Args:
            project: Project info
            overall: Overall score and decision
            dimensions: VP summaries
            full_reports: Full VP reports
            query_vp_fn: Optional function to query VPs (vp_name, question) -> response
            
        Returns:
            Chief of Staff synthesis
        """
        # First pass synthesis
        user_prompt = self._build_user_prompt(
            project, overall, dimensions, full_reports, has_query_tool=False
        )
        
        initial_synthesis = self._call_llm(user_prompt)
        
        # If we have query tool and detect conflicts, allow queries
        if query_vp_fn:
            queries_made = 0
            max_queries = 2
            
            while queries_made < max_queries:
                # Ask COS if it wants to query a VP
                query_decision = self._ask_for_query(initial_synthesis, dimensions)
                
                if not query_decision.get("should_query"):
                    break
                
                vp_name = query_decision.get("vp_name")
                question = query_decision.get("question")
                reason = query_decision.get("reason", "")
                
                if not vp_name or not question:
                    break
                
                print(f"  🤔 COS querying {vp_name.upper()} VP: {reason}")
                print(f"     Question: {question[:80]}...")
                
                # Execute query
                clarification = query_vp_fn(vp_name, question)
                
                # Add clarification to dimensions
                if vp_name in dimensions:
                    dimensions[vp_name]["clarification"] = clarification  # Store as object, not JSON string
                
                # Re-synthesize with new information
                user_prompt = self._build_user_prompt(
                    project, overall, dimensions, full_reports, has_query_tool=True
                )
                initial_synthesis = self._call_llm(user_prompt)
                
                queries_made += 1
                print(f"  ✓ Query {queries_made}/{max_queries} complete")
        
        return initial_synthesis

    def _call_llm(self, user_prompt: str) -> Dict[str, Any]:
        """Call LLM and parse JSON response."""
        response = client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": CHIEF_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )

        content = response.choices[0].message.content
        result = json.loads(content)
        result.setdefault("agent", "Chief of Staff")
        return result

    # Legacy method for backward compatibility
    def analyze(
        self,
        project: Dict[str, Any],
        overall: Dict[str, Any],
        dimensions: Dict[str, Dict[str, Any]],
        full_reports: Dict[str, Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Legacy method - calls synthesize without query_vp_fn."""
        return self.synthesize(project, overall, dimensions, full_reports, query_vp_fn=None)