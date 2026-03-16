<div align="center">

<h1>⚙️ fs-builder</h1>

<p>
  <a href="README.md">中文</a>
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/Onshape-FeatureScript-FF6B35?style=flat-square"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square"/>
</p>

<p><strong>Natural Language → Onshape FeatureScript Generator</strong></p>

</div>

---

## Overview

Describe a mechanical assembly in plain text. fs-builder uses AI to produce a ready-to-paste [Onshape Feature Studio](https://www.onshape.com/en/features/featurescript) `.fs` file in three steps:

| Step | Module | Description |
|------|--------|-------------|
| **1. Analyze** | `analyzer.py` | AI converts the requirement into a structured JSON design plan |
| **2. Generate** | `generator.py` | AI generates FeatureScript code for each part concurrently |
| **3. Merge** | `merger.py` | Deterministic merge of all snippets into one compilable `.fs` file |

## Quick Start

### Web UI (recommended)

```bash
cp .env.example .env   # add your API key
./start.sh             # starts server and opens browser
```

Type your requirement in the web page and click **Generate FeatureScript**.

### CLI

```bash
# inline requirement
python main.py "Design a cold drawing die, OD 50mm, with punch, die body, and blank holder"

# from a file
python main.py --input examples/drawing_die.txt

# skip analysis, reuse an existing plan
python main.py --plan output/my_assembly_plan.json
```

## Setup

**Requirements:** Python ≥ 3.9, an OpenAI-compatible API key.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -e .
```

Copy `.env.example` to `.env` and fill in your key:

```env
OPENAI_API_KEY=sk-...

# optional
# OPENAI_BASE_URL=https://api.openai.com/v1
# ANALYZE_MODEL=gpt-4o
# GENERATE_MODEL=gpt-4o-mini
```

> Once `.env` is configured, both the Web UI and CLI pick it up automatically.

## Project Layout

```
fs-builder/
├── app.py              # FastAPI server (SSE streaming)
├── main.py             # CLI entry point
├── analyzer.py         # Step 1 — requirement → JSON design plan
├── generator.py        # Step 2 — concurrent per-part FeatureScript generation
├── merger.py           # Step 3 — merge snippets into .fs file
├── prompts/
│   ├── analyze.txt     # system prompt for the analyzer
│   └── generate.txt    # system prompt for the code generator
├── examples/
│   └── drawing_die.txt # sample requirement (cold drawing die)
├── static/
│   └── index.html      # web UI
├── output/             # generated .fs files (gitignored)
└── .env.example
```

## Architecture

```
User requirement (plain text)
        │
        ▼
  ┌───────────┐  AI (gpt-4o)   ┌──────────────────────┐
  │ Analyzer  │ ─────────────▶ │  JSON design plan    │
  └───────────┘                │  parts + positions   │
                               └──────────┬───────────┘
                                          │
                                          ▼
                          ┌──────────────────────────────┐
                          │  Generator (concurrent)      │  AI (gpt-4o-mini)
                          │  one API call per part       │ ──────────────▶
                          └──────────────┬───────────────┘
                                         │
                                         ▼
                          ┌──────────────────────────────┐
                          │  Merger (deterministic)      │
                          │  wraps each part in {} scope │
                          │  adds FeatureScript header   │
                          └──────────────┬───────────────┘
                                         │
                                         ▼
                            output/<assembly_name>.fs
```

The JSON plan is the contract between Step 1 and Step 2. It is saved to `output/<name>_plan.json` so you can re-run generation without re-calling the analyzer.

## CLI Reference

```
python main.py [requirement | --input FILE]
               [--output FILE]       output .fs path (default: output/<name>.fs)
               [--plan FILE]         skip Step 1, load existing JSON plan
               [--dry-run]           run Step 1 only, print the plan and exit
               [--api-key KEY]       override OPENAI_API_KEY
               [--base-url URL]      OpenAI-compatible base URL
               [--analyze-model M]   model for Step 1 (default: gpt-4o)
               [--generate-model M]  model for Step 2 (default: gpt-4o-mini)
               [--concurrency N]     max parallel API calls (default: 8)
```

## Using the Output

1. Open [Onshape](https://cad.onshape.com) and create a new document
2. Open **Feature Studio** from the tab bar
3. Paste the contents of the generated `.fs` file
4. Click **Compile** — the feature appears in Part Studio
