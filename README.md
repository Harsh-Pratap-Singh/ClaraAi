# Clara AI — Automation Pipeline

Processes demo and onboarding call transcripts to generate versioned Retell AI agent configurations. Runs entirely on free-tier tools (Groq LLM, n8n, Flask).

## How it works

Two pipelines run back-to-back:

**Pipeline A** — takes a demo call transcript, extracts account info (company name, hours, services, emergency policy, etc.), and builds a v1 Retell agent spec with a full system prompt.

**Pipeline B** — takes the follow-up onboarding call, extracts updates, merges them into the existing v1 memo, computes a diff, generates a changelog, and outputs a v2 agent spec.

Both pipelines use Groq's free Llama 3.3 70B for extraction. If no API key is set, it falls back to regex-based extraction that works offline.

## Setup

```bash
git clone https://github.com/Harsh-Pratap-Singh/ClaraAi.git
cd ClaraAi
pip install -r requirements.txt

cp .env.example .env
# add your Groq API key (free at https://console.groq.com), or leave blank for rule-based fallback
```

## Usage

```bash
# process all 10 transcripts (5 demo + 5 onboarding)
python -m scripts.pipeline --batch

# single demo call
python -m scripts.pipeline --demo dataset/demo/01_comfort_air_solutions.txt

# single onboarding call (auto-matches the demo account)
python -m scripts.pipeline --onboarding dataset/onboarding/01_comfort_air_solutions.txt

# check what was processed
python -m scripts.pipeline --summary
```

## Dashboard

```bash
python dashboard/app.py
# open http://localhost:8080
```

Shows all processed accounts with their v1/v2 memos, agent specs, changelogs, and a color-coded diff viewer.

## Docker (optional, for n8n orchestration)

```bash
docker-compose up -d
# n8n at http://localhost:5678 — import workflows from workflows/
# dashboard at http://localhost:8080
```

## Output structure

After running `--batch`, you get:

```
outputs/
  accounts/
    acc-comfort-air-solutions-xxxx/
      v1/   → account_memo.json, agent_spec.json, agent_prompt.txt
      v2/   → same + changelog.md, changes.json
    acc-apex-plumbing-group-xxxx/
      ...
  batch_summary.json
  task_tracker.json
```

- **account_memo.json** — structured data extracted from the transcript
- **agent_spec.json** — full Retell agent config (voice, prompt, settings)
- **agent_prompt.txt** — standalone system prompt, ready to paste into Retell
- **changelog.md** / **changes.json** — what changed between v1 and v2

## Retell integration

The pipeline outputs agent specs and prompts that match Retell's format. Since the free tier doesn't expose the agent creation API, you import manually:

1. Go to https://www.retellai.com, create an agent
2. Paste the contents of `agent_prompt.txt` as the system prompt
3. Adjust voice/model settings from `agent_spec.json` if needed

## Dataset

10 sample transcripts in `dataset/` — 5 demo calls and 5 matching onboarding calls for: Comfort Air Solutions, Apex Plumbing Group, Guardian Fire Protection, Reliable Electric Services, ProCare Property Maintenance. Files with the same number prefix (e.g. `01_`) belong to the same account.

## Tech stack

| Component | Tool |
|---|---|
| LLM | Groq (Llama 3.3 70B, free tier) |
| Orchestration | n8n (self-hosted Docker) |
| Dashboard | Flask |
| Diffing | deepdiff |
| Storage | Local JSON files |
| Agent platform | Retell (manual import) |

## Limitations

- Retell agent creation is manual (no free API access)
- Groq free tier has rate limits (~30 req/min) — retry logic handles this
- Rule-based fallback is less accurate than LLM extraction
- Onboarding-to-demo matching relies on filename prefix convention
