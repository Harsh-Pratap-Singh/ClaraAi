"""
Clara AI Pipeline – Account Memo Extractor
Extracts structured account information from demo/onboarding call transcripts.
Uses LLM (Groq free tier) with rule-based fallback.
"""
from __future__ import annotations
import json, re, hashlib
from pathlib import Path
from scripts.llm_client import llm_extract_json
from scripts.config import logger

# ── LLM Extraction Prompts ────────────────────────────────────────────

DEMO_EXTRACTION_SYSTEM = """You are a data extraction assistant for a call-center automation company.
You will receive a transcript of a DEMO CALL with a prospective client.
Extract ALL factual information into the required JSON schema.

RULES:
- Only extract facts explicitly stated in the transcript.
- Do NOT hallucinate or invent any information.
- If a field is not mentioned, set it to null or an empty list.
- For ambiguous info, add a note under "questions_or_unknowns".
- Return ONLY valid JSON matching the schema below.

Required JSON schema:
{
  "account_id": "<generated from company name>",
  "company_name": "<string>",
  "business_hours": {
    "days": "<e.g. Monday-Friday>",
    "start": "<e.g. 08:00>",
    "end": "<e.g. 17:00>",
    "timezone": "<e.g. EST>"
  },
  "office_address": "<string or null>",
  "services_supported": ["<list of services>"],
  "emergency_definition": ["<list of emergency triggers>"],
  "emergency_routing_rules": {
    "primary_contact": "<name or role>",
    "secondary_contact": "<name or role>",
    "fallback": "<description>"
  },
  "non_emergency_routing_rules": "<description>",
  "call_transfer_rules": {
    "timeout_seconds": 30,
    "max_retries": 2,
    "failure_message": "<what to say if transfer fails>"
  },
  "integration_constraints": ["<list of constraints>"],
  "after_hours_flow_summary": "<description>",
  "office_hours_flow_summary": "<description>",
  "questions_or_unknowns": ["<list of unclear items>"],
  "notes": "<short notes>"
}"""

ONBOARDING_EXTRACTION_SYSTEM = """You are a data extraction assistant for a call-center automation company.
You will receive a transcript of an ONBOARDING CALL with an existing client.
Extract ALL factual information that represents UPDATES or ADDITIONS to the account.
This is for updating an existing account memo — focus on what is NEW or CHANGED.

RULES:
- Only extract facts explicitly stated in the transcript.
- Do NOT hallucinate or invent any information.
- If a field is not mentioned in this onboarding call, set it to null (it will not overwrite).
- Return ONLY valid JSON matching the same schema as the demo extraction.
- Pay special attention to: changed hours, new services, updated routing, new constraints.

Required JSON schema (same as demo extraction):
{
  "account_id": "<must match existing account>",
  "company_name": "<string>",
  "business_hours": { "days": "<>", "start": "<>", "end": "<>", "timezone": "<>" },
  "office_address": "<string or null>",
  "services_supported": ["<updated list>"],
  "emergency_definition": ["<updated triggers>"],
  "emergency_routing_rules": { "primary_contact": "<>", "secondary_contact": "<>", "fallback": "<>" },
  "non_emergency_routing_rules": "<>",
  "call_transfer_rules": { "timeout_seconds": 30, "max_retries": 2, "failure_message": "<>" },
  "integration_constraints": ["<updated constraints>"],
  "after_hours_flow_summary": "<>",
  "office_hours_flow_summary": "<>",
  "questions_or_unknowns": ["<>"],
  "notes": "<>"
}"""


def generate_account_id(company_name: str) -> str:
    """Generate a deterministic account_id from company name."""
    slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")
    short_hash = hashlib.md5(slug.encode()).hexdigest()[:6]
    return f"acc-{slug[:20]}-{short_hash}"


def _extract_with_llm(transcript: str, call_type: str) -> dict | None:
    """Use LLM to extract structured data from transcript."""
    system = DEMO_EXTRACTION_SYSTEM if call_type == "demo" else ONBOARDING_EXTRACTION_SYSTEM
    user_prompt = f"Here is the {call_type} call transcript:\n\n{transcript}"
    return llm_extract_json(system, user_prompt)


def _extract_with_rules(transcript: str, call_type: str) -> dict:
    """Rule-based fallback extraction when LLM is not available."""
    logger.info("Using rule-based extraction (no LLM)")
    text = transcript.lower()

    # Company name – try patterns
    company_name = "Unknown Company"
    patterns = [
        r"(?:company|business|we are|this is|welcome to|from)\s+([A-Z][A-Za-z\s&]+?)(?:\.|,|\n|$)",
        r"(?:calling from|represent)\s+([A-Z][A-Za-z\s&]+?)(?:\.|,|\n|$)",
    ]
    for pat in patterns:
        match = re.search(pat, transcript)
        if match:
            company_name = match.group(1).strip()
            break

    # Business hours
    hours = {"days": None, "start": None, "end": None, "timezone": None}
    hour_match = re.search(r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))\s*(?:to|-)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))", text)
    if hour_match:
        hours["start"] = hour_match.group(1).strip()
        hours["end"] = hour_match.group(2).strip()
    
    day_match = re.search(r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)[\s\-]*(through|to|thru)[\s\-]*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", text)
    if day_match:
        hours["days"] = f"{day_match.group(1).title()} - {day_match.group(3).title()}"
    elif "monday through friday" in text or "monday to friday" in text:
        hours["days"] = "Monday - Friday"

    tz_match = re.search(r"\b(EST|CST|MST|PST|EDT|CDT|MDT|PDT|ET|CT|MT|PT|Eastern|Central|Mountain|Pacific)\b", transcript, re.IGNORECASE)
    if tz_match:
        hours["timezone"] = tz_match.group(1).upper()

    # Services
    services = []
    service_keywords = ["hvac", "plumbing", "electrical", "heating", "cooling", "air conditioning",
                        "fire protection", "sprinkler", "maintenance", "repair", "installation",
                        "commercial", "residential", "emergency service", "drain", "sewer"]
    for kw in service_keywords:
        if kw in text:
            services.append(kw.title())

    # Emergency definitions
    emergencies = []
    emergency_keywords = ["no heat", "no cooling", "gas leak", "water leak", "flood", "fire",
                         "carbon monoxide", "frozen pipe", "burst pipe", "no hot water",
                         "sewage backup", "power outage", "electrical fire", "smoke"]
    for kw in emergency_keywords:
        if kw in text:
            emergencies.append(kw.title())

    # Address
    address = None
    addr_match = re.search(r"(\d+\s+[A-Z][A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Lane|Ln|Way|Court|Ct)[.,]?\s*(?:[A-Z][a-z]+[,.]?\s*)?(?:[A-Z]{2}\s+\d{5})?)", transcript)
    if addr_match:
        address = addr_match.group(1).strip()

    account_id = generate_account_id(company_name)

    return {
        "account_id": account_id,
        "company_name": company_name,
        "business_hours": hours,
        "office_address": address,
        "services_supported": services,
        "emergency_definition": emergencies,
        "emergency_routing_rules": {
            "primary_contact": None,
            "secondary_contact": None,
            "fallback": "Take message and assure callback within 15 minutes"
        },
        "non_emergency_routing_rules": "Take message with name, number, and issue description. Confirm callback within next business day.",
        "call_transfer_rules": {
            "timeout_seconds": 30,
            "max_retries": 2,
            "failure_message": "I apologize, I'm unable to connect you right now. Let me take your information and have someone call you back shortly."
        },
        "integration_constraints": [],
        "after_hours_flow_summary": "Greet caller, determine urgency, collect info, attempt transfer for emergencies, take message for non-emergencies.",
        "office_hours_flow_summary": "Greet caller, collect name and reason, transfer to appropriate department.",
        "questions_or_unknowns": ["Rule-based extraction – some fields may be incomplete. LLM extraction recommended."],
        "notes": f"Extracted via rule-based fallback from {call_type} call."
    }


def extract_account_memo(transcript: str, call_type: str = "demo") -> dict:
    """
    Main extraction entry point.
    Tries LLM first, falls back to rule-based extraction.
    
    Args:
        transcript: Raw transcript text
        call_type: "demo" or "onboarding"
    
    Returns:
        Structured account memo dict
    """
    logger.info(f"Extracting account memo from {call_type} call ({len(transcript)} chars)")

    # Try LLM extraction first
    result = _extract_with_llm(transcript, call_type)

    if result is None:
        # Fallback to rule-based
        result = _extract_with_rules(transcript, call_type)
    
    # Ensure account_id exists
    if not result.get("account_id") and result.get("company_name"):
        result["account_id"] = generate_account_id(result["company_name"])
    
    logger.info(f"Extraction complete: account_id={result.get('account_id')}, company={result.get('company_name')}")
    return result
