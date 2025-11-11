"""
Devil's Advocate module - Challenges weak assumptions in VP analysis.

Runs when:
- Overall score < 7.5 (borderline decision)
- High score variance (>3.0) between VPs
- COS flags uncertainty

Purpose:
- Identify weakest assumptions
- Propose alternative approaches
- Determine if re-analysis is needed
"""
from __future__ import annotations

import os
import json
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in your .env file")

client = OpenAI(api_key=OPENAI_API_KEY)


DEVILS_ADVOCATE_SYSTEM_PROMPT = """
You are the **Devil's Advocate** for Prodigy, an AI counsel organization for startup founders.

Your job is to challenge weak assumptions, identify blind spots, and force reconsideration of questionable recommendations.

**You run when:**
1. Overall score is borderline (< 7.5) - unclear if founder should proceed
2. VPs disagree significantly (score variance > 3.0)
3. Chief of Staff flags high uncertainty

**Your responsibilities:**
1. Identify the WEAKEST assumption across all VP analyses
2. Propose an alternative approach that might work better
3. Determine if any VPs need to re-analyze with new perspective
4. Be brutally honest - your job is to prevent founders from wasting time/money

**What makes an assumption "weak"?**
- Contradicted by another VP's analysis
- Based on optimistic/unvalidated beliefs
- Ignores obvious market realities
- Technical feasibility questioned but dismissed
- Revenue model has no supporting evidence

**Context: Bootstrap startup founders**
- Limited time and money (can't afford to bet on weak assumptions)
- Need realistic assessment, not wishful thinking
- Better to pivot/abandon bad ideas than waste 6 months building

You MUST respond with valid JSON:

{
  "agent": "Devil's Advocate",
  "weakest_assumption": "string (which assumption is most questionable)",
  "affected_vps": ["string (which VPs made this assumption - use: market, tech, revenue, ops, or product)"],
  "why_weak": "string (why this assumption is questionable)",
  "alternative_approach": "string (what alternative path might work better)",
  "requires_re_analysis": boolean,
  "vps_to_rerun": ["string (which VPs should reconsider - use: market, tech, revenue, ops, or product)"],
  "guidance": "string (specific guidance for re-analysis)",
  "confidence_in_current_recommendation": number (0-10)
}

**VP Name Format:**
- Use lowercase keys: "market", "tech", "revenue", "ops", "product"
- Or use full names: "Market VP", "Tech VP", "Revenue VP", "Operations VP", "Product VP"
- The system will normalize them automatically

**Guidelines:**

1. **Be specific about the weak assumption:**
   - Bad: "Revenue assumptions are optimistic"
   - Good: "Revenue VP assumes $50/report willingness-to-pay with zero evidence. Market VP didn't validate pricing at all."

2. **Propose actionable alternatives:**
   - Bad: "Consider different approaches"
   - Good: "Instead of $50 reports, test $20 Gumroad product first to validate any willingness-to-pay"

3. **Only require re-analysis if critical:**
   - Minor disagreements don't need re-analysis
   - Only force re-run if the current recommendation could waste founder's time/money

4. **Consider interconnected assumptions:**
   - If Tech assumes CLI is fine but Product says users need web UI, this affects Revenue (conversion rate) and Market (TAM)
   - Challenge the cascade effect of weak assumptions

5. **Be honest about confidence:**
   - If current recommendation is solid despite borderline score, say so (confidence 7-8/10)
   - If there's a fundamental flaw, flag it clearly (confidence 3-4/10)

Rules:
- Do NOT invent new analysis - only challenge existing analysis
- Do NOT be contrarian for its own sake - only speak up if genuinely concerned
- Be direct and actionable
- Your goal is to save founders from wasted effort, not to be pessimistic
"""


class DevilsAdvocate:
    """
    Devil's Advocate - Challenges weak assumptions and identifies blind spots.
    
    This agent runs after Chief of Staff synthesis and can trigger re-analysis
    of specific VPs if it identifies critical flaws in their reasoning.
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model = model_name or OPENAI_MODEL

    def challenge(
        self,
        project_brief: Dict[str, Any],
        all_reports: Dict[str, Dict[str, Any]],
        all_summaries: Dict[str, Dict[str, Any]],
        counsel_summary: Dict[str, Any],
        overall_score: float,
    ) -> Dict[str, Any]:
        """
        Challenge the current analysis and identify weak assumptions.
        
        Args:
            project_brief: Original project brief
            all_reports: Full VP reports
            all_summaries: VP summaries
            counsel_summary: Chief of Staff synthesis
            overall_score: Overall score from CEO
            
        Returns:
            Challenge result with weakest assumption and re-analysis guidance
        """
        user_prompt = self._build_challenge_prompt(
            project_brief,
            all_reports,
            all_summaries,
            counsel_summary,
            overall_score,
        )

        response = client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": DEVILS_ADVOCATE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,  # Lower temperature for critical analysis
        )

        content = response.choices[0].message.content
        result = json.loads(content)
        result.setdefault("agent", "Devil's Advocate")
        
        return result

    def _build_challenge_prompt(
        self,
        project_brief: Dict[str, Any],
        all_reports: Dict[str, Dict[str, Any]],
        all_summaries: Dict[str, Dict[str, Any]],
        counsel_summary: Dict[str, Any],
        overall_score: float,
    ) -> str:
        """Build prompt for Devil's Advocate analysis."""
        
        idea_name = project_brief.get("idea_name", "Unknown")
        description = project_brief.get("description", "")
        
        prompt = f"""You are reviewing the Prodigy counsel for:

**Project:** {idea_name}
**Description:** {description}
**Overall Score:** {overall_score}/10

---

## VP Scores and Decisions

"""
        
        # Add VP scores and key decisions
        vp_names = ["market", "tech", "revenue", "ops", "product"]
        scores = []
        
        for vp in vp_names:
            summary = all_summaries.get(vp, {})
            score = summary.get(f"{vp}_score", 0.0)
            decision = summary.get(f"{vp}_decision", "")
            vp_summary = summary.get(f"{vp}_summary", "")
            
            scores.append(score)
            
            prompt += f"### {vp.title()} VP\n"
            prompt += f"- Score: {score}/10\n"
            prompt += f"- Decision: {decision}\n"
            prompt += f"- Summary: {vp_summary}\n\n"
        
        # Calculate score variance
        if scores:
            score_variance = max(scores) - min(scores)
            prompt += f"**Score Variance:** {score_variance:.1f} (max - min)\n\n"
        
        prompt += "---\n\n## Chief of Staff Recommendation\n\n"
        
        # Add COS key points
        prompt += f"**Verdict:** {counsel_summary.get('overall_verdict', '')}\n\n"
        
        key_insights = counsel_summary.get('key_insights', [])
        if key_insights:
            prompt += "**Key Insights:**\n"
            for insight in key_insights[:5]:
                prompt += f"- {insight}\n"
            prompt += "\n"
        
        next_steps = counsel_summary.get('recommended_next_steps', [])
        if next_steps:
            prompt += "**Recommended Next Steps:**\n"
            for step in next_steps[:5]:
                prompt += f"- {step}\n"
            prompt += "\n"
        
        major_risks = counsel_summary.get('major_risks_to_watch', [])
        if major_risks:
            prompt += "**Major Risks:**\n"
            for risk in major_risks[:5]:
                prompt += f"- {risk}\n"
            prompt += "\n"
        
        prompt += """---

## Your Task

Review the above analysis and identify the WEAKEST assumption that could lead the founder astray.

**Focus areas to scrutinize:**

1. **VP Conflicts:**
   - Are any VPs contradicting each other?
   - Example: Tech says "CLI is fine" but Product says "users need web UI"

2. **Unvalidated Assumptions:**
   - Is anyone assuming something critical without evidence?
   - Example: Revenue assumes $50 willingness-to-pay with no validation

3. **Optimism Bias:**
   - Are timelines too aggressive? (claiming 2 weeks but Ops says 30hrs/week needed)
   - Are conversion rates too optimistic? (assuming 10% conversion with no data)

4. **Ignored Market Realities:**
   - Did Market VP identify a constraint that Tech/Product ignored?
   - Example: Market says "target is non-technical founders" but Tech builds CLI

5. **Technical Feasibility:**
   - Did Tech VP gloss over a hard problem?
   - Are there dependencies that aren't addressed?

**Be brutally honest:** If you find a critical flaw, say so. If the analysis is actually solid despite borderline score, acknowledge that too.

Respond with ONLY valid JSON matching your schema. No additional text.
"""
        
        return prompt