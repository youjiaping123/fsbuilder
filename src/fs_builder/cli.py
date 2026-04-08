"""Command-line interface for fs-builder."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from .analyzer import analyze_requirement
from .errors import CLIError, FSBuilderError
from .generator import LegacyLLMGenerator, count_failed_parts
from .merger import merge_featurescript
from .models import AssemblyPlan
from .paths import featurescript_output_path, plan_output_path
from .plan_io import load_plan_file, write_plan_file
from .settings import Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fs-builder",
        description="CLI-first demo tool for natural language to Onshape FeatureScript.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze requirement text into a plan.")
    _add_requirement_source(analyze_parser)
    _add_shared_options(analyze_parser, include_generate=False)
    analyze_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write the validated plan JSON to this file instead of stdout.",
    )
    analyze_parser.set_defaults(handler=_run_analyze)

    validate_parser = subparsers.add_parser("validate-plan", help="Validate an existing plan file.")
    validate_parser.add_argument("--plan", type=Path, required=True, help="Path to a plan JSON file.")
    validate_parser.set_defaults(handler=_run_validate_plan)

    generate_parser = subparsers.add_parser(
        "generate",
        help="Run the legacy LLM generator and merge a FeatureScript file from a plan.",
    )
    generate_parser.add_argument("--plan", type=Path, required=True, help="Path to a validated plan JSON file.")
    _add_shared_options(generate_parser, include_analyze=False)
    generate_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output .fs path. Defaults to output/<assembly_name>.fs.",
    )
    generate_parser.set_defaults(handler=_run_generate)

    build_parser = subparsers.add_parser(
        "build",
        help="Analyze or load a plan, then run the legacy generator and merger.",
    )
    build_parser.add_argument("requirement", nargs="?", help="Inline requirement string.")
    build_parser.add_argument("--input", "-i", type=Path, help="Path to a requirement text file.")
    build_parser.add_argument("--plan", type=Path, default=None, help="Skip analysis and load a plan file.")
    _add_shared_options(build_parser)
    build_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output .fs path. Defaults to output/<assembly_name>.fs.",
    )
    build_parser.add_argument(
        "--plan-output",
        type=Path,
        default=None,
        help="Where to save the validated plan. Defaults to output/<assembly_name>_plan.json.",
    )
    build_parser.set_defaults(handler=_run_build)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return args.handler(args)
    except FSBuilderError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


def _run_analyze(args: argparse.Namespace) -> int:
    settings = _resolve_settings(args, include_generate=False)
    requirement = _read_requirement(args.requirement, args.input)
    plan = analyze_requirement(requirement, settings)
    if args.output is not None:
        write_plan_file(plan, args.output)
        print(args.output)
    else:
        print(plan.to_pretty_json())
    return 0


def _run_validate_plan(args: argparse.Namespace) -> int:
    plan = load_plan_file(args.plan)
    print(f"Plan is valid: {plan.assembly_name} ({len(plan.parts)} parts)")
    return 0


def _run_generate(args: argparse.Namespace) -> int:
    settings = _resolve_settings(args, include_analyze=False)
    plan = load_plan_file(args.plan)
    results = LegacyLLMGenerator(settings).generate(plan)
    fs_content = merge_featurescript(plan, results)
    output_path = args.output or featurescript_output_path(settings.output_dir, plan.assembly_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(fs_content, encoding="utf-8")
    _print_generation_summary(output_path, results)
    return 0


def _run_build(args: argparse.Namespace) -> int:
    settings = _resolve_settings(args)
    if args.plan is not None:
        if args.requirement or args.input:
            raise CLIError("Use either --plan or requirement text, not both.")
        plan = load_plan_file(args.plan)
    else:
        requirement = _read_requirement(args.requirement, args.input)
        plan = analyze_requirement(requirement, settings)

    saved_plan_path = args.plan_output or plan_output_path(settings.output_dir, plan.assembly_name)
    write_plan_file(plan, saved_plan_path)

    results = LegacyLLMGenerator(settings).generate(plan)
    fs_content = merge_featurescript(plan, results)
    output_path = args.output or featurescript_output_path(settings.output_dir, plan.assembly_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(fs_content, encoding="utf-8")

    print(f"Plan saved: {saved_plan_path}")
    _print_generation_summary(output_path, results)
    return 0


def _add_requirement_source(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("requirement", nargs="?", help="Inline requirement string.")
    group.add_argument("--input", "-i", type=Path, help="Path to a requirement text file.")


def _add_shared_options(
    parser: argparse.ArgumentParser,
    *,
    include_analyze: bool = True,
    include_generate: bool = True,
) -> None:
    parser.add_argument("--api-key", default=None, help="Override OPENAI_API_KEY.")
    parser.add_argument("--base-url", default=None, help="Override OPENAI_BASE_URL.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Default output directory for generated files.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Max concurrent API calls for the legacy generator.",
    )
    if include_analyze:
        parser.add_argument(
            "--analyze-model",
            default=None,
            help="Model used for requirement analysis.",
        )
    if include_generate:
        parser.add_argument(
            "--generate-model",
            default=None,
            help="Model used by the legacy FeatureScript generator.",
        )


def _resolve_settings(
    args: argparse.Namespace,
    *,
    include_analyze: bool = True,
    include_generate: bool = True,
) -> Settings:
    return Settings.from_sources(
        api_key=getattr(args, "api_key", None),
        base_url=getattr(args, "base_url", None),
        analyze_model=getattr(args, "analyze_model", None) if include_analyze else None,
        generate_model=getattr(args, "generate_model", None) if include_generate else None,
        concurrency=getattr(args, "concurrency", 4),
        output_dir=getattr(args, "output_dir", Path("output")),
    )


def _read_requirement(raw_requirement: str | None, input_path: Path | None) -> str:
    if raw_requirement and input_path:
        raise CLIError("Use either inline requirement text or --input, not both.")
    if input_path is not None:
        try:
            requirement = input_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError as exc:
            raise CLIError(f"Requirement file not found: {input_path}") from exc
    else:
        requirement = (raw_requirement or "").strip()

    if not requirement:
        raise CLIError("Requirement text is required. Pass inline text or --input FILE.")
    return requirement


def _print_generation_summary(output_path: Path, results: list) -> None:
    failed = count_failed_parts(results)
    succeeded = len(results) - failed
    print(f"FeatureScript written: {output_path}")
    print(f"Parts generated: {succeeded}/{len(results)}")
    if failed:
        print(f"Warning: {failed} part(s) failed and were embedded as error comments.")
