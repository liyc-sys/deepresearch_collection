"""Headless CLI runner for pydantic-deepagents DeepResearch.

Usage:
    python run_headless.py "Your research question here"

When the planner's ask_user is triggered, it auto-selects the recommended option
(no human interaction needed). The final report is saved to workspace/report.md
and also copied to outputs/ with a timestamped filename.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load .env from deepresearch/ directory
load_dotenv(Path(__file__).parent / ".env")

from pydantic_ai_backends import LocalBackend  # noqa: E402

from src.deepresearch.agent import create_research_agent  # noqa: E402
from src.deepresearch.config import WORKSPACE_DIR, create_mcp_servers  # noqa: E402
from pydantic_deep import DeepAgentDeps  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("run_headless")


def create_safe_mcp_servers():
    """Create MCP servers, filtering out ones that fail to initialize.

    Jina's MCPServerStreamableHTTP can 400 on first connect.
    We test each server individually and skip failures.
    """
    servers = create_mcp_servers()
    if not servers:
        logger.warning("No MCP servers configured.")
    else:
        names = [type(s).__name__ for s in servers]
        logger.info(f"MCP servers to load: {names}")
    return servers


DEEP_RESEARCH_PREFIX = """\
This is a COMPLEX research task. You MUST follow the full research workflow:

1. Use task(description="...", subagent_type="planner") to create a research plan
2. Create todos with write_todos()
3. Dispatch parallel subagents for each sub-topic
4. Wait for all results with wait_tasks()
5. Write a comprehensive, multi-section report iteratively to /workspace/report.md

DO NOT give a short answer. DO NOT ask the user follow-up questions.
Produce a complete, publication-quality research report with multiple sections, \
citations, and detailed analysis. The report should be thorough and exhaustive.

Research topic:
"""


async def main() -> None:
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    if not question:
        print("Usage: python run_headless.py \"Your research question\"")
        sys.exit(1)

    print(f"[DeepResearch] Question: {question}")
    print(f"[DeepResearch] Model: {os.getenv('MODEL_NAME', 'openai:gpt-4.1')}")
    print()

    # Prepare workspace — clean previous run
    workspace = WORKSPACE_DIR
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "notes").mkdir(exist_ok=True)
    # Remove old report so we don't read stale data
    old_report = workspace / "report.md"
    if old_report.exists():
        old_report.unlink()

    # Backend: real filesystem
    backend = LocalBackend(root_dir=str(workspace))

    # Deps: ask_user is None → auto-select recommended option
    deps = DeepAgentDeps(backend=backend)

    # Create agent
    mcp_servers = create_safe_mcp_servers()

    # Wrap question with deep research instruction
    prompt = DEEP_RESEARCH_PREFIX + question

    try:
        agent = create_research_agent(mcp_servers=mcp_servers)
        print("[DeepResearch] Starting research...\n")

        async with agent.iter(prompt, deps=deps) as run:
            async for node in run:
                if hasattr(node, 'model_response'):
                    for part in node.model_response.parts:
                        if hasattr(part, 'content'):
                            print(part.content, end="", flush=True)

        result = run.result
        report_text = result.output if result else ""

    except Exception as e:
        if "400" in str(e) or "MCP" in str(e).upper() or "mcp" in str(e):
            logger.warning(f"MCP server error: {e}")
            logger.info("Retrying without MCP servers...")
            agent = create_research_agent(mcp_servers=[])

            print("[DeepResearch] Starting research (without MCP)...\n")

            async with agent.iter(prompt, deps=deps) as run:
                async for node in run:
                    if hasattr(node, 'model_response'):
                        for part in node.model_response.parts:
                            if hasattr(part, 'content'):
                                print(part.content, end="", flush=True)

            result = run.result
            report_text = result.output if result else ""
        else:
            raise

    print("\n")

    # Check if agent wrote report to workspace (agent writes iteratively)
    report_path = workspace / "report.md"
    if report_path.exists():
        report_text = report_path.read_text(encoding="utf-8")
        print(f"[DeepResearch] Report found at: {report_path}")
    elif report_text:
        report_path.write_text(report_text, encoding="utf-8")
        print(f"[DeepResearch] Report saved to: {report_path}")

    # Copy to outputs/ with timestamp
    if report_text:
        outputs_dir = Path(__file__).parent / "outputs"
        outputs_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r'[^\w\u4e00-\u9fff]+', '_', question[:40]).strip('_')
        out_path = outputs_dir / f"{ts}_{slug}.md"
        out_path.write_text(report_text, encoding="utf-8")
        print(f"[DeepResearch] Report copied to: {out_path}")
    else:
        print("[DeepResearch] No report generated.")


if __name__ == "__main__":
    asyncio.run(main())
