#!/usr/bin/env python3
# Run with: .venv/bin/python3 app.py
"""
fs-builder Web UI — FastAPI server with SSE progress streaming.

Run:
    python app.py
    # or
    uvicorn app:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import analyzer
import generator
import merger

# Load .env from project root (safe even if the file doesn't exist)
load_dotenv(Path(__file__).parent / ".env")

app = FastAPI(title="fs-builder")
app.mount("/static", StaticFiles(directory="static"), name="static")


class GenerateRequest(BaseModel):
    requirement: str
    api_key: str = ""          # empty = use OPENAI_API_KEY env var
    base_url: str = ""
    analyze_model: str = ""
    generate_model: str = ""
    concurrency: int = 4


@app.get("/", response_class=HTMLResponse)
async def index():
    return Path("static/index.html").read_text(encoding="utf-8")


@app.get("/api/config")
async def get_config():
    """Return non-secret env-var defaults for the UI to pre-fill."""
    return {
        "has_api_key": bool(os.environ.get("OPENAI_API_KEY")),
        "base_url":       os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "analyze_model":  os.environ.get("ANALYZE_MODEL",   "gpt-4o"),
        "generate_model": os.environ.get("GENERATE_MODEL",  "gpt-4o-mini"),
    }


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _resolve(req_val: str, env_key: str, fallback: str) -> str:
    """Use request value if provided, otherwise fall back to env var, then hardcoded default."""
    return req_val.strip() or os.environ.get(env_key, fallback)


@app.post("/api/generate")
async def generate_endpoint(req: GenerateRequest):
    async def stream() -> AsyncGenerator[str, None]:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Resolve effective settings (request → env var → default)
        api_key       = req.api_key.strip()       or os.environ.get("OPENAI_API_KEY") or ""
        base_url      = _resolve(req.base_url,      "OPENAI_BASE_URL", "https://api.openai.com/v1")
        analyze_model = _resolve(req.analyze_model, "ANALYZE_MODEL",   "gpt-4o")
        gen_model     = _resolve(req.generate_model,"GENERATE_MODEL",  "gpt-4o-mini")

        if not api_key:
            yield _sse({"type": "error", "message": "No API key provided and OPENAI_API_KEY is not set."})
            return

        # ── Step 1: Analyze (streaming) ──────────────────────────────────
        yield _sse({
            "type": "step", "n": 1, "status": "start",
            "message": f"Analyzing with {analyze_model}…",
        })

        plan = None
        accumulated = []
        try:
            async for chunk in analyzer.analyze_stream(
                req.requirement,
                model=analyze_model,
                api_key=api_key,
                base_url=base_url or None,
            ):
                # Check for the final sentinel
                if chunk.startswith("{") and '"__done__"' in chunk:
                    sentinel = json.loads(chunk)
                    plan = sentinel["plan"]
                else:
                    accumulated.append(chunk)
                    yield _sse({"type": "analyze_token", "text": chunk})

        except Exception as e:
            yield _sse({"type": "error", "message": str(e)})
            return

        yield _sse({
            "type": "step", "n": 1, "status": "done",
            "summary": {
                "assembly_name": plan["assembly_name"],
                "parts_count": len(plan["parts"]),
            },
        })

        plan_path = output_dir / f"{plan['assembly_name']}_plan.json"
        plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")

        # ── Step 2: Generate ─────────────────────────────────────────────
        total_parts = len(plan["parts"])
        yield _sse({
            "type": "step", "n": 2, "status": "start",
            "message": f"Generating {total_parts} parts…",
            "total": total_parts,
        })

        queue: asyncio.Queue = asyncio.Queue()

        async def on_part_done(result):
            await queue.put(result)

        gen_task = asyncio.create_task(
            generator.generate_async(
                plan,
                model=gen_model,
                api_key=api_key,
                base_url=base_url or None,
                max_concurrent=req.concurrency,
                on_part_done=on_part_done,
            )
        )

        done_count = 0
        while done_count < total_parts:
            try:
                result = await asyncio.wait_for(queue.get(), timeout=60.0)
                done_count += 1
                yield _sse({
                    "type": "part_progress",
                    "done": done_count,
                    "total": total_parts,
                    "part_name": result.part_name,
                    "success": result.error is None,
                })
            except asyncio.TimeoutError:
                if gen_task.done():
                    break

        try:
            results = await gen_task
        except Exception as e:
            yield _sse({"type": "error", "message": str(e)})
            return

        ok = sum(1 for r in results if not r.error)
        failed = sum(1 for r in results if r.error)
        yield _sse({"type": "step", "n": 2, "status": "done", "success": ok, "failed": failed})

        # ── Step 3: Merge ────────────────────────────────────────────────
        yield _sse({"type": "step", "n": 3, "status": "start"})

        fs_content = merger.merge(plan, results)
        output_path = output_dir / f"{plan['assembly_name']}.fs"
        output_path.write_text(fs_content, encoding="utf-8")

        yield _sse({"type": "step", "n": 3, "status": "done"})
        yield _sse({
            "type": "done",
            "code": fs_content,
            "filename": output_path.name,
            "size": len(fs_content),
        })

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def run():
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
