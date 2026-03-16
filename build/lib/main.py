#!/usr/bin/env python3
"""
fs-builder: Natural language → Onshape FeatureScript

Usage:
    python main.py "描述你的机械结构需求"
    python main.py --input examples/drawing_die.txt
    python main.py --input examples/drawing_die.txt --output output/my_die.fs
    python main.py --input examples/drawing_die.txt --dry-run   # only show Step 1 JSON
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import analyzer
import generator
import merger


def _print_step(n: int, title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  Step {n}: {title}")
    print(f"{'─' * 60}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Onshape FeatureScript from natural language requirements."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("requirement", nargs="?", help="Inline requirement string")
    group.add_argument("--input", "-i", type=Path, help="Path to requirement text file")

    parser.add_argument(
        "--output", "-o", type=Path,
        default=None,
        help="Output .fs file path (default: output/<assembly_name>.fs)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Only run Step 1 (analysis) and print the JSON plan, then exit"
    )
    parser.add_argument(
        "--plan", type=Path, default=None,
        help="Skip Step 1 and load an existing JSON plan from this file"
    )
    parser.add_argument(
        "--api-key", default=None,
        help="OpenAI API key (default: OPENAI_API_KEY env var)"
    )
    parser.add_argument(
        "--base-url", default=None,
        help="OpenAI-compatible API base URL (default: https://api.openai.com/v1)"
    )
    parser.add_argument(
        "--analyze-model", default=None,
        help="Model for Step 1 analysis (default: ANALYZE_MODEL env var or gpt-4o)"
    )
    parser.add_argument(
        "--generate-model", default=None,
        help="Model for Step 2 generation (default: GENERATE_MODEL env var or gpt-4o-mini)"
    )
    parser.add_argument(
        "--concurrency", type=int, default=8,
        help="Max concurrent API calls in Step 2 (default: 8)"
    )

    args = parser.parse_args()

    # Resolve settings (CLI flag → env var → default)
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: Provide --api-key or set OPENAI_API_KEY.", file=sys.stderr)
        sys.exit(1)

    base_url      = args.base_url       or os.environ.get("OPENAI_BASE_URL") or None
    analyze_model = args.analyze_model  or os.environ.get("ANALYZE_MODEL",  "gpt-4o")
    gen_model     = args.generate_model or os.environ.get("GENERATE_MODEL", "gpt-4o-mini")

    # --- Read requirement ---
    if args.plan:
        requirement = "(loaded from existing plan)"
    elif args.input:
        requirement = args.input.read_text(encoding="utf-8").strip()
    else:
        requirement = args.requirement.strip()

    # ── Step 1: Analyze ──────────────────────────────────────────────────────
    if args.plan:
        _print_step(1, "Loading existing JSON plan (skipping AI analysis)")
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        print(f"  Loaded: {args.plan}")
    else:
        _print_step(1, f"Analyzing requirement with {analyze_model}...")
        t0 = time.monotonic()
        try:
            plan = analyzer.analyze(
                requirement,
                model=analyze_model,
                api_key=api_key,
                base_url=base_url,
            )
        except ValueError as e:
            print(f"\n[ERROR] Analysis failed:\n{e}", file=sys.stderr)
            sys.exit(1)
        elapsed = time.monotonic() - t0
        print(f"  Done in {elapsed:.1f}s")
        print(f"  Assembly : {plan['assembly_name']}")
        print(f"  Parts    : {len(plan['parts'])}")
        for p in plan["parts"]:
            pos = p["position"]
            print(
                f"    • [{p['id']}] {p['name']}  "
                f"shape={p['shape']}  "
                f"z_bottom={pos['z_bottom_mm']}mm"
            )

    # Save the plan alongside output
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    plan_path = output_dir / f"{plan['assembly_name']}_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Plan saved → {plan_path}")

    if args.dry_run:
        print("\n[dry-run] Stopping after Step 1.")
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return

    # ── Step 2: Generate ─────────────────────────────────────────────────────
    _print_step(2, f"Generating FeatureScript for {len(plan['parts'])} parts (concurrently)...")
    t0 = time.monotonic()
    results = generator.generate(
        plan,
        model=gen_model,
        max_concurrent=args.concurrency,
        api_key=api_key,
        base_url=base_url,
    )
    elapsed = time.monotonic() - t0
    print(f"  Done in {elapsed:.1f}s")

    ok = [r for r in results if not r.error]
    failed = [r for r in results if r.error]
    print(f"  Success : {len(ok)}/{len(results)}")
    for r in failed:
        print(f"  [FAILED] {r.part_id}: {r.error}", file=sys.stderr)

    # ── Step 3: Merge ────────────────────────────────────────────────────────
    _print_step(3, "Merging into single .fs file...")
    fs_content = merger.merge(plan, results)

    output_path = args.output or output_dir / f"{plan['assembly_name']}.fs"
    output_path.write_text(fs_content, encoding="utf-8")

    print(f"  Written → {output_path}")
    print(f"  Size    : {len(fs_content):,} characters")

    if failed:
        print(
            f"\n  Warning: {len(failed)} part(s) failed. "
            "Their sections in the .fs file contain error comments.",
            file=sys.stderr,
        )

    print(f"\n{'═' * 60}")
    print(f"  Done! Copy the contents of:")
    print(f"  {output_path.resolve()}")
    print(f"  into Onshape Feature Studio and run the feature.")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
