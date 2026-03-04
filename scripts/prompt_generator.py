"""
Clara AI Pipeline – Retell Agent Spec Generator
Generates a Retell-compatible agent configuration from an account memo.
"""
from __future__ import annotations
import json
from scripts.config import logger


def _build_system_prompt(memo: dict) -> str:
    """Generate the agent's system prompt from account memo."""
    company = memo.get("company_name", "the company")
    hours = memo.get("business_hours", {})
    address = memo.get("office_address", "N/A")
    services = memo.get("services_supported", [])
    emergencies = memo.get("emergency_definition", [])
    emergency_routing = memo.get("emergency_routing_rules", {})
    non_emergency_routing = memo.get("non_emergency_routing_rules", "")
    transfer_rules = memo.get("call_transfer_rules", {})
    integration_constraints = memo.get("integration_constraints", [])
    after_hours = memo.get("after_hours_flow_summary", "")
    office_hours = memo.get("office_hours_flow_summary", "")

    hrs_str = "Not specified"
    if hours.get("days") and hours.get("start") and hours.get("end"):
        hrs_str = f"{hours['days']}, {hours['start']} – {hours['end']}"
        if hours.get("timezone"):
            hrs_str += f" {hours['timezone']}"

    services_str = ", ".join(services) if services else "General services"
    emergencies_str = ", ".join(emergencies) if emergencies else "Life-safety issues, flooding, gas leaks, no heat/cooling"

    constraints_str = ""
    if integration_constraints:
        constraints_str = "\n\nIMPORTANT CONSTRAINTS:\n" + "\n".join(f"- {c}" for c in integration_constraints)

    primary = emergency_routing.get("primary_contact", "on-call technician")
    secondary = emergency_routing.get("secondary_contact", "manager")
    fallback = emergency_routing.get("fallback", "Take message and assure callback")

    timeout = transfer_rules.get("timeout_seconds", 30)
    retries = transfer_rules.get("max_retries", 2)
    fail_msg = transfer_rules.get("failure_message", "I'm unable to connect you right now. Let me take your information.")

    prompt = f"""You are a professional virtual receptionist for {company}.

COMPANY INFORMATION:
- Company: {company}
- Business Hours: {hrs_str}
- Office Address: {address}
- Services: {services_str}

═══════════════════════════════════════════════════
DURING BUSINESS HOURS FLOW:
═══════════════════════════════════════════════════
1. GREETING: "Thank you for calling {company}. How can I help you today?"
2. IDENTIFY PURPOSE: Listen and determine the caller's need.
3. COLLECT INFO: Ask for the caller's name and callback number.
   - Only collect what is needed for routing. Do NOT ask excessive questions.
4. ROUTE/TRANSFER: Transfer the call to the appropriate person or department.
   - Wait up to {timeout} seconds for an answer.
   - If no answer, retry up to {retries} time(s).
   - If transfer fails: "{fail_msg}"
5. CONFIRM: Summarize what will happen next.
6. WRAP UP: "Is there anything else I can help you with?"
7. CLOSE: "Thank you for calling {company}. Have a great day!"

{office_hours}

═══════════════════════════════════════════════════
AFTER HOURS FLOW:
═══════════════════════════════════════════════════
1. GREETING: "Thank you for calling {company}. Our office is currently closed. Our business hours are {hrs_str}."
2. DETERMINE URGENCY: "Is this an emergency?"
3. IF EMERGENCY:
   Emergency triggers: {emergencies_str}
   a. Collect caller's name, phone number, and address IMMEDIATELY.
   b. Attempt to transfer to {primary}.
   c. If {primary} unavailable, try {secondary}.
   d. If all transfers fail: "{fallback}"
   e. Assure the caller: "I've dispatched this as urgent. Someone will contact you within 15 minutes."
4. IF NOT EMERGENCY:
   a. {non_emergency_routing if non_emergency_routing else "Take a message with name, number, and brief description of the issue."}
   b. Confirm: "We'll have someone return your call on the next business day."
5. WRAP UP: "Is there anything else I can help you with?"
6. CLOSE: "Thank you for calling {company}. Goodnight!"

{after_hours}

═══════════════════════════════════════════════════
CALL TRANSFER PROTOCOL:
═══════════════════════════════════════════════════
- Ring timeout: {timeout} seconds
- Max retries: {retries}
- On failure: "{fail_msg}"
- NEVER mention internal systems, function calls, or technical processes to the caller.
- NEVER say "I'm transferring you to a function" or similar.

═══════════════════════════════════════════════════
EMERGENCY ROUTING ORDER:
═══════════════════════════════════════════════════
1. {primary}
2. {secondary}
3. Fallback: {fallback}
{constraints_str}

═══════════════════════════════════════════════════
GENERAL RULES:
═══════════════════════════════════════════════════
- Be professional, warm, and concise.
- Do NOT ask more than 3 questions in a row without confirming understanding.
- Do NOT mention internal tools, APIs, or function calls to the caller.
- If you don't know an answer, say "Let me take your information and have the right person get back to you."
- Always confirm the caller's name and number before ending.
- Keep the conversation flowing naturally."""

    return prompt


def generate_agent_spec(memo: dict, version: str = "v1") -> dict:
    """
    Generate a Retell Agent Draft Specification from an account memo.
    
    Args:
        memo: Account memo dict
        version: Version string (v1 for demo, v2 for post-onboarding)
    
    Returns:
        Agent spec dict ready for Retell import
    """
    company = memo.get("company_name", "Unknown Company")
    account_id = memo.get("account_id", "unknown")
    hours = memo.get("business_hours", {})

    system_prompt = _build_system_prompt(memo)

    spec = {
        "agent_name": f"{company} – Virtual Receptionist",
        "account_id": account_id,
        "voice_style": {
            "voice_id": "professional-female-1",
            "language": "en-US",
            "speed": 1.0,
            "pitch": "medium",
            "style": "professional, warm, concise"
        },
        "system_prompt": system_prompt,
        "key_variables": {
            "timezone": hours.get("timezone", "EST"),
            "business_hours": hours,
            "office_address": memo.get("office_address"),
            "emergency_routing": memo.get("emergency_routing_rules", {}),
            "services": memo.get("services_supported", [])
        },
        "tool_invocation_placeholders": {
            "transfer_call": {
                "description": "Transfer to a phone number (never mention to caller)",
                "parameters": ["target_number", "timeout_seconds"]
            },
            "create_ticket": {
                "description": "Create a service ticket (never mention to caller)",
                "parameters": ["caller_name", "caller_phone", "issue_description", "urgency"]
            },
            "send_sms": {
                "description": "Send SMS confirmation (never mention to caller)",
                "parameters": ["phone_number", "message"]
            }
        },
        "call_transfer_protocol": memo.get("call_transfer_rules", {
            "timeout_seconds": 30,
            "max_retries": 2,
            "failure_message": "I apologize, I'm unable to connect you right now."
        }),
        "fallback_protocol": {
            "all_transfers_failed": "Take complete message and create urgent ticket",
            "caller_message": "I've taken your information and marked this as priority. You'll hear back shortly.",
            "internal_action": "Create ticket + send SMS alert to on-call staff"
        },
        "version": version,
        "metadata": {
            "generated_from": "demo_call" if version == "v1" else "onboarding_update",
            "company_name": company,
            "account_id": account_id
        }
    }

    logger.info(f"Generated agent spec {version} for {company} ({account_id})")
    return spec
