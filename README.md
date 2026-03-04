# Clara AI — Automation Pipeline

Processes demo and onboarding call transcripts to generate versioned Retell AI agent configurations. Runs entirely on free-tier tools (Groq LLM, n8n, Flask).

## How it works

Two pipelines run back-to-back:

**Pipeline A** — takes a demo call transcript, extracts account info (company name, hours, services, emergency policy, etc.), and builds a v1 Retell agent spec with a full system prompt.

**Pipeline B** — takes the follow-up onboarding call, extracts updates, merges them into the existing v1 memo, computes a diff, generates a changelog, and outputs a v2 agent spec.

## Setup

### Prerequisites

- Python 3.9 or higher
- pip
- Docker & Docker Compose (only if you want n8n orchestration — not required)
- Groq API key (optional — pipeline works without it using rule-based extraction)

### Installation

```bash
git clone https://github.com/Harsh-Pratap-Singh/ClaraAi.git
cd ClaraAi
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
```

Open `.env` and set your Groq API key if you have one:

```
GROQ_API_KEY=gsk_your_key_here
```

**Don't have a Groq key?** That's fine — leave it blank or skip the `.env` file entirely. The pipeline will automatically use the rule-based extraction fallback (regex pattern matching). It's less accurate but fully functional and works completely offline with zero external dependencies.

Get a free key at https://console.groq.com if you want LLM-powered extraction.

## Usage

### Run the full pipeline (all 10 transcripts)

```bash
python -m scripts.pipeline --batch
```

This processes all 5 demo transcripts → v1 outputs, then all 5 onboarding transcripts → v2 outputs with diffs and changelogs. Takes about 15-20 seconds with Groq, instant with rule-based fallback.

### Run individual files

```bash
# single demo call → v1
python -m scripts.pipeline --demo dataset/demo/01_comfort_air_solutions.txt

# single onboarding call → v2 (auto-matches to existing v1 account)
python -m scripts.pipeline --onboarding dataset/onboarding/01_comfort_air_solutions.txt

# onboarding with explicit account ID
python -m scripts.pipeline --onboarding dataset/onboarding/01_comfort_air_solutions.txt --account acc-comfort-air-solutions-xxxx
```

### Check results

```bash
python -m scripts.pipeline --summary
```

Prints a summary of all processed accounts, versions, and file paths.

## Dashboard

```bash
python dashboard/app.py
```

Open http://localhost:8080 in your browser. The dashboard shows:

- All processed accounts as cards (with v1/v2 version badges)
- Tabbed detail view: account memo, agent spec, changelog, diff viewer
- Color-coded diff viewer highlighting exactly what changed between v1 and v2

## LLM mode vs Rule-based mode

The pipeline has two extraction modes and picks one automatically:

| | LLM mode (Groq) | Rule-based mode |
|---|---|---|
| **When** | `GROQ_API_KEY` is set in `.env` | No API key, or Groq is down |
| **Model** | Llama 3.3 70B (falls back to 8B) | Regex pattern matching |
| **Accuracy** | High — understands context | Good — catches structured info |
| **Speed** | ~2s per transcript | Instant |
| **Cost** | Free (Groq free tier) | Free (no network needed) |
| **Offline** | No | Yes |

The rule-based extractor pulls: company name, business hours, services list, emergency handling, address, and contact info using pattern matching. It won't catch everything an LLM would, but it produces valid output that flows through the rest of the pipeline identically.

If the Groq API returns an error or hits a rate limit, the pipeline retries automatically (with backoff), then falls back to the lighter Llama 3.1 8B model, and only then falls back to rule-based. No manual intervention needed.

## Output structure

After running `--batch`, you get:

```
outputs/
  accounts/
    acc-comfort-air-solutions-xxxx/
      v1/
        account_memo.json       ← structured account data
        agent_spec.json         ← full Retell agent config
        agent_prompt.txt        ← standalone system prompt
      v2/
        account_memo.json       ← updated account data
        agent_spec.json         ← updated agent config
        agent_prompt.txt        ← updated system prompt
        changelog.md            ← human-readable list of changes
        changes.json            ← machine-readable diff
    acc-apex-plumbing-group-xxxx/
      v1/ ...
      v2/ ...
    ... (5 accounts total)
  batch_summary.json            ← run metadata for all accounts
  task_tracker.json             ← processing task log
```

### What each file contains

- **account_memo.json** — structured JSON with company name, hours, services, emergency policy, address, contacts, and any unknowns flagged as `questions_or_unknowns` (never invents data)
- **agent_spec.json** — complete Retell-compatible agent config: voice settings, model, system prompt, response parameters
- **agent_prompt.txt** — the system prompt on its own, ready to copy-paste into Retell's dashboard
- **changelog.md** — markdown list of what changed from v1 to v2 (e.g. "Added service: Water heater installation")
- **changes.json** — the raw diff object for programmatic use

## Retell integration

The pipeline generates agent specs matching Retell's expected format. Since the free tier doesn't expose the agent creation API, you import manually:

1. Sign up at https://www.retellai.com (free tier)
2. Create a new agent
3. Paste the contents of `agent_prompt.txt` into the System Prompt field
4. Optionally configure voice and model settings from `agent_spec.json`

See [docs/retell_setup.md](docs/retell_setup.md) for a step-by-step walkthrough.

## Docker (optional)

If you want to use n8n for visual workflow orchestration:

```bash
docker-compose up -d
```

This starts three services:
- **n8n** at http://localhost:5678 (default credentials: clara / clara2024)
- **Pipeline** container with all scripts
- **Dashboard** at http://localhost:8080

Import the workflow JSONs from `workflows/` into the n8n UI. See [docs/n8n_setup.md](docs/n8n_setup.md) for details.

## Dataset

10 sample transcripts in `dataset/`:

```
dataset/
  demo/
    01_comfort_air_solutions.txt
    02_apex_plumbing_group.txt
    03_guardian_fire_protection.txt
    04_reliable_electric_services.txt
    05_procare_property_maintenance.txt
  onboarding/
    01_comfort_air_solutions.txt
    02_apex_plumbing_group.txt
    03_guardian_fire_protection.txt
    04_reliable_electric_services.txt
    05_procare_property_maintenance.txt
```

Files with the same number prefix (e.g. `01_`) belong to the same account. The pipeline uses this convention to auto-match onboarding calls to their demo counterpart.

## Project structure

```
scripts/
  config.py              ← env vars, paths, model names
  llm_client.py          ← Groq API wrapper with retry + fallback
  extractor.py           ← LLM + rule-based transcript extraction
  prompt_generator.py    ← builds Retell agent specs and system prompts
  versioning.py          ← deep merge, diff computation, changelog generation
  storage.py             ← file I/O for account artifacts
  task_tracker.py        ← local JSON tracker + optional GitHub Issues
  pipeline.py            ← main orchestrator and CLI entry point
dashboard/
  app.py                 ← Flask web dashboard
workflows/
  n8n_batch_pipeline.json
  n8n_single_demo.json
  n8n_single_onboarding.json
docs/
  retell_setup.md
  n8n_setup.md
```

## Tech stack

| Component | Tool |
|---|---|
| LLM | Groq — Llama 3.3 70B, free tier |
| Fallback | Rule-based regex extraction (offline, no cost) |
| Orchestration | n8n (self-hosted Docker) |
| Dashboard | Flask |
| Diffing | deepdiff |
| Storage | Local JSON files |
| Agent platform | Retell (manual spec import) |

## Error handling and reliability

- **LLM retries**: if Groq returns 429 (rate limit) or 500, the pipeline waits and retries with exponential backoff
- **Model fallback**: Llama 3.3 70B → Llama 3.1 8B → rule-based extraction
- **Idempotent**: safe to re-run `--batch` multiple times — overwrites existing outputs cleanly
- **Logging**: all steps log to console with timestamps, making it easy to debug failures
- **No hallucination**: any field the extractor can't confidently fill goes into `questions_or_unknowns` instead of being guessed

## Limitations

- Retell agent creation is manual (free tier has no API access)
- Groq free tier is rate-limited (~30 req/min) — retry logic handles it but batch runs may take longer under heavy use
- Rule-based fallback is less accurate — misses context-dependent details
- Account matching between demo and onboarding relies on the filename number prefix
