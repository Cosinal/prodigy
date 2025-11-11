# Chief of Staff module - Enhanced for 5 VPs
from __future__ import annotations

import os
import json
from typing import Any, Dict

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


class ChiefOfStaff:
    """
    Chief of Staff for Prodigy - Synthesizes all VP reports into founder guidance.

    Takes:
    - project info (idea name, description)
    - overall score + decision from Orchestrator
    - dimension summaries (from all 5 VPs)
    - full reports (optional, for deeper synthesis)

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

Respond with ONLY valid JSON matching your schema. No additional text.
"""

        return prompt

    def analyze(
        self,
        project: Dict[str, Any],
        overall: Dict[str, Any],
        dimensions: Dict[str, Dict[str, Any]],
        full_reports: Dict[str, Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Call the LLM with the CoS system prompt + user prompt,
        and parse the JSON response.
        """
        user_prompt = self._build_user_prompt(project, overall, dimensions, full_reports)

        response = client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": CHIEF_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,  # Balance creativity with consistency
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        result.setdefault("agent", "Chief of Staff")
        return result