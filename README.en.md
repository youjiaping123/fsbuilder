# fs-builder

CLI-first graduation-demo tool for turning simple mechanical requirements into Onshape FeatureScript.

Current version:

- keeps the three-step flow: `analyze -> generate -> merge`
- removes the previous Web UI and server deployment path
- keeps Step 2 as a **legacy LLM generator**
- prepares the codebase for future deterministic FeatureScript templates

## Supported Scope

The plan schema currently supports only five simple shapes:

- `box`
- `cylinder`
- `hollow_cylinder`
- `tapered_cylinder`
- `flange`

Unsupported shapes fail fast during validation.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
cp .env.example .env
```

## CLI Commands

Analyze requirement text into a validated plan:

```bash
fs-builder analyze --input examples/drawing_die.txt --output output/drawing_die_plan.json
```

Validate an existing plan:

```bash
fs-builder validate-plan --plan output/drawing_die_plan.json
```

Generate FeatureScript from an existing plan:

```bash
fs-builder generate --plan output/drawing_die_plan.json
```

Run the full pipeline:

```bash
fs-builder build --input examples/drawing_die.txt
```

## Notes

- This is still a demo-oriented codebase.
- The current generator is temporary and LLM-based.
- Deterministic FeatureScript templates are intentionally not implemented yet.

## Tests

```bash
pytest
```
