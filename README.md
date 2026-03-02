# Deep Research Framework Collection

> Adapting 5 open-source factual QA agent frameworks into unified deep research report generators — with comparative architecture analysis and standardized benchmarking.

## Motivation

Most open-source "deep research" agent frameworks (InfoAgent, MiroFlow, OAgents, etc.) were originally designed for **factual question answering** — they retrieve evidence from the web and produce short, direct answers. However, generating a **comprehensive, multi-section research report** from a single topic requires fundamentally different orchestration: iterative planning, structured outline generation, section-level synthesis, and coherent long-form writing.

This project **independently extends and adapts** all 5 frameworks so that each one can produce structured deep research reports, while preserving their original search and reasoning capabilities. A unified execution interface and shared environment setup allow **side-by-side comparison** of how different architectural choices (LangGraph state machines, ReAct loops, manager-worker hierarchies, async sub-agents, etc.) affect report quality, depth, and efficiency.

## Frameworks

| Framework | Origin | Architecture | Key Technique |
|-----------|--------|-------------|---------------|
| **InfoAgent (RE-TRAC)** | Microsoft Research | LangGraph StateGraph | Recursive trajectory compression with uncertainty analysis |
| **MiroFlow** | Samsung Research | Orchestrator + MCP Servers | Rich tool ecosystem (8 types), sub-agent delegation |
| **OAgents** | OPPO PersonalAI Lab | Manager-Worker Multi-Agent | Search reflection + memory-based synthesis |
| **pydantic-deepagents** | Pydantic AI Ecosystem | Async Sub-Agents | TODO-driven parallel research, incremental report writing |
| **YunqueAgent** | Tencent Yunque | ReAct + Dynamic Memory | Sub-goal-driven context management, triple-protection limits |

## What Was Changed

Each framework required different modifications to support report generation:

- **InfoAgent**: Extended the fixed-cycle research loop to accumulate structured section summaries instead of a single answer; added report outline planning before the research phase.
- **MiroFlow**: Configured the orchestrator pipeline to include outline generation and section-by-section summarization stages; leveraged MCP tool servers for parallel section research.
- **OAgents**: Modified the Manager agent to decompose a topic into report sections (instead of sub-questions), spawn Worker agents per section, and synthesize results into a coherent report via memory composition.
- **pydantic-deepagents**: Adapted the TODO-driven workflow to treat each report section as an independent async research task; enabled incremental file-based report assembly.
- **YunqueAgent**: Introduced a report planning phase into the ReAct loop; configured the supervisor module to manage section-level progress tracking within its dynamic memory system.

## Architecture Comparison

| Dimension | InfoAgent | MiroFlow | OAgents | pydantic-deepagents | YunqueAgent |
|-----------|-----------|----------|---------|---------------------|-------------|
| Core Pattern | LangGraph loops | Tool orchestration | Manager-Worker | Async sub-agents | ReAct + Memory |
| Multi-Round Control | Fixed cycles | LLM decides | Manager steps | TODO-list driven | 3-tier limits |
| Report Generation | One-shot synthesis | Conversation summary | Memory synthesis | Incremental writes | Agent self-output |
| Sub-agent Support | No | Yes (MCP-based) | Yes (Code-based) | Yes (Async) | Yes |
| Search Backend | Serper + Jina | Serper + Jina + Playwright | DuckDuckGo / SerpAPI | Tavily / Brave / Firecrawl | Serper + Google Scholar |
| Code Execution | No | E2B sandbox | Local Python | Docker | SandboxFusion |

> See [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed analysis of each framework's internal execution flow, prompt design, and report generation mechanism.

## Project Structure

```
deepresearch_collection/
├── InfoAgent/                  # Microsoft RE-TRAC framework (adapted)
├── MiroFlow/                   # Samsung MiroMind agent (adapted)
├── OAgents/                    # OPPO multi-agent framework (adapted)
├── pydantic-deepagents/        # Pydantic AI deep agents (adapted)
├── YunqueAgent/                # Tencent Yunque agent (adapted)
│
├── run_infoagent.sh            # Unified launch scripts
├── run_miroflow.sh
├── run_oagents.sh
├── run_pydantic_deepagents.sh
├── run_yunqueagent.sh
├── setup_envs.sh               # One-click environment setup
│
├── ARCHITECTURE.md             # Detailed framework comparison
├── SETUP.md                    # Environment & API key configuration
├── requirements_tier1.txt      # Shared dependencies (4 frameworks)
└── requirements_yunque.txt     # YunqueAgent dependencies (OpenAI 1.x)
```

## Quick Start

```bash
# 1. Set up virtual environments (requires Python >= 3.12)
bash setup_envs.sh

# 2. Configure API keys for each framework (see SETUP.md)

# 3. Generate a deep research report with any framework
bash run_infoagent.sh "Recent advances in LLM-based autonomous agents"
bash run_miroflow.sh "Recent advances in LLM-based autonomous agents"
bash run_oagents.sh "Recent advances in LLM-based autonomous agents"
bash run_pydantic_deepagents.sh "Recent advances in LLM-based autonomous agents"
bash run_yunqueagent.sh "Recent advances in LLM-based autonomous agents"
```

Two separate virtual environments are maintained due to OpenAI SDK version conflicts:
- `.venv_tier1` — InfoAgent, MiroFlow, OAgents, pydantic-deepagents (openai 2.x)
- `.venv_yunque` — YunqueAgent (openai 1.x)

## Documentation

- Environment & API key setup: [SETUP.md](SETUP.md)
- Framework architecture deep-dive: [ARCHITECTURE.md](ARCHITECTURE.md)

## License

Each sub-framework retains its original license. See the LICENSE file within each framework directory.
