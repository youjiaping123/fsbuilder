"""fs-builder 命令行入口。"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .application import analyze_command, build_command, generate_command, validate_plan_command
from .errors import FSBuilderError
from .generation import GenerationReport
from .settings import Settings, load_project_env
from .webui import serve_web_ui


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fs-builder",
        description="把自然语言需求转换为结构化 plan，并生成 Onshape FeatureScript。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="把需求文本分析成 plan。")
    _add_requirement_source(analyze_parser)
    _add_shared_options(analyze_parser)
    analyze_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="把校验后的 plan JSON 写入指定文件；未传时输出到 stdout。",
    )
    analyze_parser.set_defaults(handler=_run_analyze)

    validate_parser = subparsers.add_parser("validate-plan", help="校验已有 plan 文件。")
    validate_parser.add_argument("--plan", type=Path, required=True, help="plan JSON 文件路径。")
    validate_parser.set_defaults(handler=_run_validate_plan)

    generate_parser = subparsers.add_parser(
        "generate",
        help="根据已校验的 plan 生成 FeatureScript。",
    )
    generate_parser.add_argument(
        "--plan",
        type=Path,
        required=True,
        help="已校验的 plan JSON 文件路径。",
    )
    _add_shared_options(generate_parser, include_analyze=False)
    generate_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出 `.fs` 文件路径；未传时默认写入 `output/<assembly_name>.fs`。",
    )
    generate_parser.set_defaults(handler=_run_generate)

    build_parser = subparsers.add_parser(
        "build",
        help="分析需求或读取已有 plan，然后生成 FeatureScript。",
    )
    build_parser.add_argument("requirement", nargs="?", help="内联需求文本。")
    build_parser.add_argument("--input", "-i", type=Path, help="需求文本文件路径。")
    build_parser.add_argument(
        "--plan",
        type=Path,
        default=None,
        help="跳过分析，直接读取 plan 文件。",
    )
    _add_shared_options(build_parser)
    build_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出 `.fs` 文件路径；未传时默认写入 `output/<assembly_name>.fs`。",
    )
    build_parser.add_argument(
        "--plan-output",
        type=Path,
        default=None,
        help="保存校验后 plan 的路径；未传时默认写入 `output/<assembly_name>_plan.json`。",
    )
    build_parser.set_defaults(handler=_run_build)

    serve_parser = subparsers.add_parser("serve", help="启动本地 Web UI。")
    _add_shared_options(serve_parser)
    serve_parser.add_argument("--host", default="127.0.0.1", help="监听地址。")
    serve_parser.add_argument("--port", type=int, default=8000, help="监听端口。")
    serve_parser.set_defaults(handler=_run_serve)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return int(args.handler(args))
    except FSBuilderError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2


def _run_analyze(args: argparse.Namespace) -> int:
    settings = _resolve_settings(args)
    result = analyze_command(
        settings=settings,
        requirement_text=args.requirement,
        input_path=args.input,
        output_path=args.output,
    )
    if result.output_path is not None:
        print(f"Plan 已写入：{result.output_path}")
    else:
        print(result.plan.to_pretty_json())
    return 0


def _run_validate_plan(args: argparse.Namespace) -> int:
    result = validate_plan_command(args.plan)
    print(f"Plan 校验通过：{result.plan.assembly_name}（{len(result.plan.parts)} 个零件）")
    return 0


def _run_generate(args: argparse.Namespace) -> int:
    settings = _resolve_settings(args, include_analyze=False)
    result = generate_command(
        settings=settings,
        plan_path=args.plan,
        output_path=args.output,
    )
    _print_generation_summary(result.output_path, result.report)
    return 0


def _run_build(args: argparse.Namespace) -> int:
    settings = _resolve_settings(args)
    result = build_command(
        settings=settings,
        requirement_text=args.requirement,
        input_path=args.input,
        plan_path=args.plan,
        output_path=args.output,
        plan_output_path=args.plan_output,
    )
    print(f"Plan 已写入：{result.plan_path}")
    _print_generation_summary(result.output_path, result.report)
    return 0


def _run_serve(args: argparse.Namespace) -> int:
    settings = _resolve_settings(args)
    display_host = "127.0.0.1" if args.host == "0.0.0.0" else args.host
    print(f"Web UI 已启动：http://{display_host}:{args.port}")
    try:
        serve_web_ui(settings, host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\nWeb UI 已停止。")
    return 0


def _add_requirement_source(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("requirement", nargs="?", help="内联需求文本。")
    group.add_argument("--input", "-i", type=Path, help="需求文本文件路径。")


def _add_shared_options(
    parser: argparse.ArgumentParser,
    *,
    include_analyze: bool = True,
) -> None:
    parser.add_argument("--api-key", default=None, help="覆盖环境变量中的 OPENAI_API_KEY。")
    parser.add_argument("--base-url", default=None, help="覆盖环境变量中的 OPENAI_BASE_URL。")
    parser.add_argument(
        "--api-timeout-seconds",
        type=float,
        default=None,
        help="覆盖环境变量中的 OPENAI_TIMEOUT_SECONDS。",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="默认输出目录。",
    )
    if include_analyze:
        parser.add_argument(
            "--analyze-model",
            default=None,
            help="需求分析阶段使用的模型。",
        )
        parser.add_argument(
            "--analyze-max-tokens",
            type=int,
            default=None,
            help="需求分析阶段的最大输出 token 数。",
        )


def _resolve_settings(
    args: argparse.Namespace,
    *,
    include_analyze: bool = True,
) -> Settings:
    load_project_env()
    return Settings.from_sources(
        api_key=getattr(args, "api_key", None),
        base_url=getattr(args, "base_url", None),
        api_timeout_seconds=getattr(args, "api_timeout_seconds", None),
        analyze_model=getattr(args, "analyze_model", None) if include_analyze else None,
        analyze_max_tokens=getattr(args, "analyze_max_tokens", None) if include_analyze else None,
        output_dir=getattr(args, "output_dir", Path("output")),
    )


def _print_generation_summary(output_path: Path, report: GenerationReport) -> None:
    print(f"FeatureScript 已写入：{output_path}")
    print(f"零件生成结果：{report.succeeded_parts}/{report.total_parts}")
    failed = report.failed_parts
    if failed:
        print(f"警告：有 {failed} 个零件生成失败，已以内联错误注释写入输出文件。")
