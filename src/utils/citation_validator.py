"""
Citation Cross-Validation Utility

Validates that sources actually support the claims being made
"""

import logging
from typing import Dict, Optional

from src.api_clients import call_claude_api

logger = logging.getLogger(__name__)


def validate_citation(
    claim: str,
    source_text: str,
    source_url: str
) -> Dict:
    """
    Check if source actually supports the claim

    Returns:
        {
            "supports": "yes" | "partial" | "no",
            "confidence": 0.0-1.0,
            "reasoning": "..."
        }
    """

    prompt = f"""
You are a citation validator. Check if this SOURCE actually supports the CLAIM.

CLAIM:
{claim}

SOURCE URL:
{source_url}

SOURCE CONTENT:
{source_text[:2000]}

TASK:
1. Does the source DIRECTLY support the claim? (yes/partial/no)
2. How confident are you? (0.0-1.0)
3. Why? (brief reasoning)

OUTPUT JSON:
{{
  "supports": "yes|partial|no",
  "confidence": 0.9,
  "reasoning": "The source explicitly states..."
}}
"""

    try:
        response = call_claude_api(
            prompt=prompt,
            temperature=0.2,
            max_tokens=500
        )

        # Parse JSON response
        import json
        if "```json" in response:
            json_start = response.find("```json") + 7
            json_end = response.find("```", json_start)
            response = response[json_start:json_end].strip()

        data = json.loads(response)
        return data

    except Exception as e:
        logger.error(f"Citation validation failed: {e}")
        return {
            "supports": "unknown",
            "confidence": 0.5,
            "reasoning": f"Validation error: {str(e)}"
        }


def cross_validate_claims(
    gemini_claim: Dict,
    claude_claim: Dict,
    sources: Dict[str, str]
) -> Dict:
    """
    Cross-validate a claim from both agents against their sources

    Returns validation report with cross-check results
    """

    results = {
        "gemini_validation": None,
        "claude_validation": None,
        "cross_validated": False,
        "recommendation": ""
    }

    # Validate Gemini's claim against their source
    if gemini_claim.get("your_source") and gemini_claim["your_source"] in sources:
        results["gemini_validation"] = validate_citation(
            gemini_claim.get("your_statement", ""),
            sources[gemini_claim["your_source"]],
            gemini_claim["your_source"]
        )

    # Validate Claude's claim against their source
    if claude_claim.get("your_source") and claude_claim["your_source"] in sources:
        results["claude_validation"] = validate_citation(
            claude_claim.get("your_statement", ""),
            sources[claude_claim["your_source"]],
            claude_claim["your_source"]
        )

    # Determine cross-validation status
    g_supports = results["gemini_validation"].get("supports") if results["gemini_validation"] else None
    c_supports = results["claude_validation"].get("supports") if results["claude_validation"] else None

    if g_supports == "yes" and c_supports == "yes":
        results["cross_validated"] = True
        results["recommendation"] = "Strong agreement - both sources support claim"
    elif g_supports == "yes" and c_supports in ["partial", None]:
        results["recommendation"] = "Accept Gemini's version - stronger source"
    elif c_supports == "yes" and g_supports in ["partial", None]:
        results["recommendation"] = "Accept Claude's version - stronger source"
    elif g_supports == "no" or c_supports == "no":
        results["cross_validated"] = False
        results["recommendation"] = "Reject - at least one source doesn't support claim"
    else:
        results["recommendation"] = "Uncertain - need better sources"

    return results
