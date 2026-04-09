# fs-builder

CLI-first graduation-demo tool for turning simple mechanical requirements into Onshape FeatureScript.

Current version:

- keeps the three-step flow: `analyze -> generate -> merge`
- removes the previous Web UI and server deployment path
- uses deterministic FeatureScript templates by default for Step 2
- keeps `--legacy` only as an explicit compatibility path

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

Optional environment override:

```env
# ANALYZE_MAX_TOKENS=2048
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

Use the old LLM-based path only when needed:

```bash
fs-builder generate --plan output/drawing_die_plan.json --legacy --api-key sk-...
```

Run the full pipeline:

```bash
fs-builder build --input examples/drawing_die.txt
```

## Notes

- This is still a demo-oriented codebase.
- Step 2 now defaults to deterministic templates for the five supported shapes.
- LLM generation is still available behind `--legacy`.
- The bundled reference guide lives at `src/fs_builder/references/featurescript_guide.md`.
- The analyzer defaults to `ANALYZE_MAX_TOKENS=2048` because some OpenAI-compatible providers return empty content at very large values.

## Tests

```bash
pytest
```
