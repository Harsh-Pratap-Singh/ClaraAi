# Retell Agent Setup Guide

## Overview

This document explains how to use the **Agent Spec JSON** outputs from the Clara AI Pipeline to configure agents in the Retell platform.

---

## Option A: Free Tier API (if available)

If Retell offers a free tier with API access:

1. **Create Account**: Sign up at [https://www.retellai.com](https://www.retellai.com)
2. **Get API Key**: Navigate to Settings → API Keys → Create New Key
3. **Set Environment Variable**:
   ```bash
   # In your .env file
   RETELL_API_KEY=your_key_here
   ```
4. The pipeline will automatically attempt to create agents via the Retell API.

---

## Option B: Manual Import (Recommended for Free Tier)

Since Retell may not offer free programmatic agent creation, follow these steps to manually import the generated agent configuration:

### Step 1: Locate Your Agent Spec

After running the pipeline, find the agent spec at:
```
outputs/accounts/<account_id>/v1/agent_spec.json   (initial draft)
outputs/accounts/<account_id>/v2/agent_spec.json   (after onboarding)
```

### Step 2: Create Agent in Retell Dashboard

1. Log in to [Retell Dashboard](https://dashboard.retellai.com)
2. Click **"Create New Agent"**
3. Fill in the following from the spec:

| Spec Field | Retell UI Field |
|---|---|
| `agent_name` | Agent Name |
| `voice_style.voice_id` | Voice Selection |
| `voice_style.language` | Language |
| `system_prompt` | System Prompt / Instructions |

### Step 3: Configure the System Prompt

1. Copy the entire content of `agent_prompt.txt` (also available in the `system_prompt` field of the spec)
2. Paste it into the **System Prompt / Instructions** field in Retell
3. This prompt contains:
   - Business hours flow
   - After-hours flow  
   - Emergency routing protocol
   - Transfer/fallback protocols
   - Constraints and special rules

### Step 4: Configure Tool Functions (Optional)

The spec includes `tool_invocation_placeholders`:
- **transfer_call**: Configure Retell's call transfer feature
- **create_ticket**: If you have a ticketing integration
- **send_sms**: If you have SMS capabilities

These are placeholders — configure them based on your Retell plan's available integrations.

### Step 5: Test the Agent

1. Use Retell's built-in test call feature
2. Test both business-hours and after-hours scenarios
3. Test emergency vs. non-emergency flows
4. Verify transfer behavior

---

## Versioning in Retell

When updating from v1 to v2:

1. **Option A**: Create a new agent version in Retell (if supported)
2. **Option B**: Update the existing agent's system prompt with the v2 content
3. **Always review** the `changelog.md` to understand what changed

The changelog is located at:
```
outputs/accounts/<account_id>/v2/changelog.md
```

---

## Agent Spec Schema Reference

```json
{
  "agent_name": "Company Name – Virtual Receptionist",
  "account_id": "acc-company-hash",
  "voice_style": {
    "voice_id": "professional-female-1",
    "language": "en-US",
    "speed": 1.0,
    "pitch": "medium",
    "style": "professional, warm, concise"
  },
  "system_prompt": "<full generated prompt>",
  "key_variables": {
    "timezone": "EST",
    "business_hours": { ... },
    "office_address": "...",
    "emergency_routing": { ... },
    "services": [ ... ]
  },
  "tool_invocation_placeholders": {
    "transfer_call": { ... },
    "create_ticket": { ... },
    "send_sms": { ... }
  },
  "call_transfer_protocol": {
    "timeout_seconds": 30,
    "max_retries": 2,
    "failure_message": "..."
  },
  "fallback_protocol": { ... },
  "version": "v1",
  "metadata": { ... }
}
```

---

## Notes

- The system prompt is the most critical piece — it contains all business logic
- Tool invocations are never mentioned to callers (this is enforced in the prompt)
- The prompt is designed to be Retell-compatible but can work with other voice AI platforms
- For production use, you would integrate Retell's actual phone number and transfer APIs
