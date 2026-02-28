#!/usr/bin/env python
# Deep Research Report generation mode for OAgents.
# This script uses the OAgents framework to conduct web research
# and produce a comprehensive Markdown research report.
#
# Usage:
#   python run_report.py "Your research topic here"
#   python run_report.py --topic "Your research topic here"
#   python run_report.py --topic "Your research topic" --max-steps 25 --search-steps 35

import argparse
import datetime
import importlib
import os
import re

import yaml
from dotenv import load_dotenv

from scripts.text_inspector_tool import TextInspectorTool
from scripts.text_web_browser import (
    FinderTool,
    FindNextTool,
    PageDownTool,
    PageUpTool,
    SimpleTextBrowser,
    VisitTool,
)
from scripts.searcher import SearchTool

from oagents import (
    CodeAgent,
    ToolCallingAgent,
)
from scripts.automodel import get_api_model

load_dotenv(override=True)

AUTHORIZED_IMPORTS = [
    "requests",
    "os",
    "json",
    "re",
    "datetime",
    "csv",
    "io",
]

custom_role_conversions = {"tool-call": "assistant", "tool-response": "user"}

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"

BROWSER_CONFIG = {
    "viewport_size": 1024 * 5,
    "downloads_folder": "downloads_folder",
    "request_kwargs": {
        "headers": {"User-Agent": user_agent},
        "timeout": 300,
    },
    "serpapi_key": os.getenv("SERPAPI_API_KEY"),
}


def parse_args():
    parser = argparse.ArgumentParser(description="OAgents Deep Research Report Generator")
    parser.add_argument(
        "topic_positional",
        type=str,
        nargs="?",
        default=None,
        help="Research topic (positional argument)",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Research topic (named argument)",
    )
    parser.add_argument(
        "--model-id",
        type=str,
        default="bytedance-seed/seed-1.6",
        help="Model ID to use via OpenRouter (default: bytedance-seed/seed-1.6)",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Maximum steps for the manager agent (default: 20)",
    )
    parser.add_argument(
        "--search-steps",
        type=int,
        default=30,
        help="Maximum steps for the search sub-agent per delegation (default: 30)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Directory to save reports (default: reports)",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="English",
        help="Language for the report (default: English)",
    )
    return parser.parse_args()


def load_report_prompts():
    """Load the report-oriented YAML prompt templates.

    Tries importlib.resources first (works if oagents is installed from local source),
    falls back to loading from the local source tree.
    """
    # Determine the path to the YAML files
    # The source tree is at OAgents/src/oagents/prompts/ relative to the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))  # OAgents/
    prompts_dir = os.path.join(project_root, "src", "oagents", "prompts")

    manager_yaml_path = os.path.join(prompts_dir, "code_agent_report.yaml")
    search_yaml_path = os.path.join(prompts_dir, "toolcalling_agent_report.yaml")

    if os.path.exists(manager_yaml_path):
        # Load from local source tree
        with open(manager_yaml_path, "r", encoding="utf-8") as f:
            manager_prompts = yaml.safe_load(f)
        with open(search_yaml_path, "r", encoding="utf-8") as f:
            search_prompts = yaml.safe_load(f)
    else:
        # Fallback: try importlib.resources (if installed from source)
        manager_prompts = yaml.safe_load(
            importlib.resources.files("oagents.prompts")
            .joinpath("code_agent_report.yaml")
            .read_text()
        )
        search_prompts = yaml.safe_load(
            importlib.resources.files("oagents.prompts")
            .joinpath("toolcalling_agent_report.yaml")
            .read_text()
        )
    return manager_prompts, search_prompts


def _synthesize_report_from_memory(agent, model, topic):
    """Fallback: synthesize a report from the agent's memory when the agent
    didn't produce output via final_answer (e.g., hit max_steps)."""
    # Collect all observations and outputs from agent memory
    research_notes = []
    for step in agent.memory.steps:
        step_dict = step.dict() if hasattr(step, "dict") else {}
        # Collect observations (tool outputs)
        if hasattr(step, "observations") and step.observations:
            research_notes.append(f"[Research Finding]\n{step.observations}")
        # Collect model reasoning
        if hasattr(step, "model_output") and step.model_output:
            research_notes.append(f"[Agent Reasoning]\n{step.model_output}")

    if not research_notes:
        return f"# Research Report\n\nNo research data was gathered for topic: {topic}"

    research_context = "\n\n---\n\n".join(research_notes[-20:])  # Last 20 notes to fit context

    synthesis_prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert research report writer. Based on the research notes below, "
                "produce a comprehensive, well-structured Markdown research report. "
                "Include: Title, Executive Summary, Table of Contents, Introduction, "
                "multiple body sections, Analysis & Discussion, Conclusion, and References."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Research Topic:\n{topic}\n\n"
                f"Research Notes Gathered:\n{research_context}\n\n"
                "Now synthesize ALL the above research into a comprehensive Markdown report. "
                "Be thorough and detailed. Include all source URLs found in the research."
            ),
        },
    ]

    try:
        response = model(synthesis_prompt)
        return response.content
    except Exception as e:
        # Last resort: dump the raw research notes
        return (
            f"# Research Report (Raw Notes)\n\n"
            f"*Report synthesis failed: {e}*\n\n"
            f"## Research Notes\n\n{research_context}"
        )


def main():
    args = parse_args()

    # Determine the topic from either positional or named argument
    topic = args.topic_positional or args.topic
    if not topic:
        print("Error: Please provide a research topic.")
        print("Usage: python run_report.py \"Your research topic\"")
        print("   or: python run_report.py --topic \"Your research topic\"")
        return

    print(f"Research topic: {topic}")
    print(f"Model: {args.model_id}")
    print(f"Manager max steps: {args.max_steps}")
    print(f"Search agent max steps: {args.search_steps}")
    print("=" * 60)

    # Setup output directory
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(f"./{BROWSER_CONFIG['downloads_folder']}", exist_ok=True)

    # Load report-oriented prompts
    manager_prompts, search_prompts = load_report_prompts()

    text_limit = 100000

    # Create model - use OpenAIServerModel via OpenRouter (same as run_gaia.py)
    model_name, api_key, api_base, model_wrapper = get_api_model(args.model_id)
    model = model_wrapper(
        model_name,
        custom_role_conversions=custom_role_conversions,
        max_completion_tokens=16384,
        api_key=api_key,
        api_base=api_base,
    )

    # Create tools - use DuckDuckGo and Wikipedia (no SerpApi key needed)
    ddg_search = SearchTool(search_type="duckduckgo", serp_num=10, reflection=False)
    wiki_search = SearchTool(search_type="wiki", reflection=False)

    browser = SimpleTextBrowser(**BROWSER_CONFIG)

    WEB_TOOLS = [
        ddg_search,
        wiki_search,
        VisitTool(browser),
        PageUpTool(browser),
        PageDownTool(browser),
        FinderTool(browser),
        FindNextTool(browser),
        TextInspectorTool(model, text_limit),
    ]

    # Create the search sub-agent with report-oriented prompts
    text_webbrowser_agent = ToolCallingAgent(
        model=model,
        tools=WEB_TOOLS,
        max_steps=args.search_steps,
        verbosity_level=2,
        planning_interval=5,
        name="search_agent",
        description="""A thorough web research assistant that will search the internet and gather detailed information on any topic.
    Provide detailed research tasks with as much context as possible.
    The assistant will search multiple sources, visit relevant pages, and return comprehensive findings with source URLs.
    Your request must be a detailed description of what information to find, not just keywords.""",
        provide_run_summary=True,
        prompt_templates=search_prompts,
    )
    text_webbrowser_agent.prompt_templates["managed_agent"]["task"] += """
    You can navigate to .txt online files.
    If a non-html page is in another format, especially .pdf, use tool 'inspect_file_as_text' to inspect it.
    If after searching you find that you need more information, you can use `final_answer` with your request for clarification as argument to request for more information."""

    # Create the manager agent with report-oriented prompts
    document_inspection_tool = TextInspectorTool(model, text_limit)
    manager_agent = CodeAgent(
        model=model,
        tools=[document_inspection_tool],
        max_steps=args.max_steps,
        verbosity_level=2,
        additional_authorized_imports=AUTHORIZED_IMPORTS,
        planning_interval=4,
        managed_agents=[text_webbrowser_agent],
        prompt_templates=manager_prompts,
    )

    # Run the research
    augmented_topic = f"""Conduct deep research on the following topic and produce a comprehensive Markdown research report.

Research Topic: {topic}

Requirements:
- The report should be written in {args.language}
- Include an executive summary, table of contents, multiple body sections, analysis, conclusion, and references
- Each claim should be attributed to its source with URLs
- Aim for a thorough, well-structured report of at least 2000 words
- Cross-verify important claims from multiple sources"""

    print("\nStarting deep research...\n")
    report = manager_agent.run(augmented_topic)

    # If agent returned empty/None, synthesize report from memory as fallback
    report_text = str(report) if report else ""
    if len(report_text.strip()) < 100:
        print("\nAgent output was empty or too short. Synthesizing report from research memory...")
        report_text = _synthesize_report_from_memory(manager_agent, model, augmented_topic)

    # Save the report
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # Create a safe filename from the topic
    safe_name = re.sub(r"[^\w\s-]", "_", topic[:60]).strip()
    safe_name = re.sub(r"\s+", "_", safe_name)
    output_path = os.path.join(args.output_dir, f"report_{safe_name}_{timestamp}.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print("\n" + "=" * 60)
    print(f"Report saved to: {output_path}")
    print(f"Report length: {len(report_text)} characters")


if __name__ == "__main__":
    main()
