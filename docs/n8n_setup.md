# n8n Setup Guide

## Overview

The Clara AI Pipeline includes n8n workflow exports for automation orchestration. n8n is self-hosted locally via Docker (free).

---

## Quick Start

### 1. Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop/) installed
- [Docker Compose](https://docs.docker.com/compose/) available

### 2. Start n8n

```bash
# From the project root directory
docker-compose up n8n -d
```

n8n will be available at: **http://localhost:5678**

Default credentials:
- Username: `clara`
- Password: `clara2024`

### 3. Import Workflows

1. Open http://localhost:5678
2. Click **Workflows** → **Import from File**
3. Import each workflow:

| File | Purpose |
|---|---|
| `workflows/n8n_batch_pipeline.json` | Run all 10 dataset files at once |
| `workflows/n8n_single_demo.json` | Process a single demo call via webhook |
| `workflows/n8n_single_onboarding.json` | Process a single onboarding call via webhook |

### 4. Configure Environment

In n8n, set these environment variables (Settings → Variables):

| Variable | Value |
|---|---|
| `GROQ_API_KEY` | Your Groq API key (from https://console.groq.com) |
| `RETELL_API_KEY` | (Optional) Your Retell API key |

Or pass them via docker-compose environment section.

---

## Workflow Descriptions

### Batch Pipeline (`n8n_batch_pipeline.json`)

Runs the complete pipeline on all dataset files:

```
Manual Trigger → Run Batch Pipeline → Read Summary → Parse Accounts → Format Status
```

1. **Manual Trigger**: Click "Execute" to start
2. **Run Batch Pipeline**: Executes `python -m scripts.pipeline --batch`
3. **Read Summary**: Reads the batch_summary.json output
4. **Parse Accounts**: Splits results per account
5. **Format Status**: Shows v1/v2 status per account

### Single Demo Webhook (`n8n_single_demo.json`)

Accepts a single demo call via HTTP webhook:

```
POST http://localhost:5678/webhook/clara/demo
Content-Type: application/json

{
  "transcript": "<full transcript text>",
  "filename": "acme_corp.txt"
}
```

### Single Onboarding Webhook (`n8n_single_onboarding.json`)

Accepts an onboarding call via HTTP webhook:

```
POST http://localhost:5678/webhook/clara/onboarding
Content-Type: application/json

{
  "transcript": "<full transcript text>",
  "filename": "acme_onboarding.txt",
  "account_id": "acc-acme-abc123"
}
```

---

## Running Without n8n

You can also run the pipeline directly via Python (no Docker needed):

```bash
# Install dependencies
pip install -r requirements.txt

# Run batch (all 10 files)
python -m scripts.pipeline --batch

# Run single demo
python -m scripts.pipeline --demo dataset/demo/01_comfort_air_solutions.txt

# Run single onboarding
python -m scripts.pipeline --onboarding dataset/onboarding/01_comfort_air_solutions.txt

# View summary
python -m scripts.pipeline --summary
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| n8n can't reach Python scripts | Ensure the project volume is mounted at `/data/project` |
| Workflow execution timeout | Increase timeout in n8n settings (Settings → Executions) |
| Permission errors on Docker | Add your user to the docker group: `sudo usermod -aG docker $USER` |
| n8n port conflict | Change the port in docker-compose.yml (e.g., `5679:5678`) |
