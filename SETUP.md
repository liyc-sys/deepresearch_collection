# 环境配置指南

本仓库包含 5 个 deep research agent 框架，使用 **两个独立的 Python 虚拟环境** 运行。

## 环境总览

| 虚拟环境 | 适用项目 | Python | 关键依赖版本 |
|---------|---------|--------|------------|
| `.venv_tier1` | InfoAgent, MiroFlow, OAgents, pydantic-deepagents | 3.12 | openai==2.24, pydantic==2.12, tiktoken==0.12 |
| `.venv_yunque` | YunqueAgent | 3.12 | openai==1.99, pydantic==2.11, tiktoken==0.11 |

**为什么需要两个环境？** YunqueAgent 的依赖版本（openai 1.x, json5 0.12, transformers 4.56 等）与其他 4 个项目不兼容。强行合并会导致 import 错误或运行时崩溃。

## 一键配置

### 前置要求

- **Python >= 3.12**（通过以下任一方式安装）：
  ```bash
  # 方式 1: uv（推荐）
  curl -LsSf https://astral.sh/uv/install.sh | sh
  uv python install 3.12

  # 方式 2: Homebrew (macOS)
  brew install python@3.12

  # 方式 3: pyenv
  pyenv install 3.12
  ```

- **API Keys**（运行 agent 需要）：
  - OpenRouter API Key（或其他 OpenAI 兼容 API）
  - Serper API Key（Google 搜索）
  - Jina API Key（网页解析）

### 运行安装脚本

```bash
git clone https://github.com/liyc-sys/deepresearch_collection.git
cd deepresearch_collection
bash setup_envs.sh
```

脚本会自动：
1. 检测 Python 3.12
2. 创建 `.venv_tier1/` 并安装 287 个依赖包
3. 创建 `.venv_yunque/` 并安装 93 个依赖包
4. 提示需要配置的 `.env` 文件

### 配置 API Keys

每个子项目需要各自的 `.env` 文件。从模板复制后填入你的 key：

```bash
# InfoAgent
cp InfoAgent/retrac/retrac/.env.example InfoAgent/retrac/retrac/.env

# MiroFlow
cp MiroFlow/.env.template MiroFlow/.env

# YunqueAgent
cp YunqueAgent/.env.example YunqueAgent/.env

# OAgents
cp OAgents/OAgents/.env.example OAgents/OAgents/.env
cp OAgents/Efficient_Agents/.env.example OAgents/Efficient_Agents/.env

# pydantic-deepagents
cp pydantic-deepagents/deepresearch/.env.example pydantic-deepagents/deepresearch/.env
```

`.env` 中需要配置的关键变量（以 YunqueAgent 为例）：
```
AGENT_API_KEY=sk-or-v1-xxxxxx        # OpenRouter API Key
AGENT_API_BASE=https://openrouter.ai/api/v1
SERPER_KEY_ID=xxxxxx                  # Serper.dev API Key
JINA_API_KEYS=jina_xxxxxx            # Jina.ai API Key
LLM_MODEL=bytedance-seed/seed-1.6    # 模型名（OpenRouter 格式）
```

## 手动配置（如果一键脚本不适用）

### .venv_tier1（InfoAgent / MiroFlow / OAgents / pydantic-deepagents）

```bash
python3.12 -m venv .venv_tier1
source .venv_tier1/bin/activate
pip install -r requirements_tier1.txt
pip install -r requirements_tier1_freeze.txt   # 精确版本锁定
deactivate
```

### .venv_yunque（YunqueAgent）

```bash
python3.12 -m venv .venv_yunque
source .venv_yunque/bin/activate
pip install -r requirements_yunque.txt
deactivate
```

## 运行各框架

每个框架都有对应的一键运行脚本，接受研究问题作为参数：

```bash
# InfoAgent
bash run_infoagent.sh "2025年AI Agent框架的最新进展"

# MiroFlow
bash run_miroflow.sh "2025年AI Agent框架的最新进展"

# OAgents
bash run_oagents.sh "2025年AI Agent框架的最新进展"

# pydantic-deepagents
bash run_pydantic_deepagents.sh "2025年AI Agent框架的最新进展"

# YunqueAgent
bash run_yunqueagent.sh "2025年AI Agent框架的最新进展"
```

不带参数运行时使用默认问题。

## 项目结构

```
deepresearch_collection/
├── .venv_tier1/                   # 共享虚拟环境（InfoAgent/MiroFlow/OAgents/pydantic-deepagents）
├── .venv_yunque/                   # YunqueAgent 专用虚拟环境
├── InfoAgent/                     # Microsoft InfoAgent (retrac)
├── MiroFlow/                      # Samsung MiroFlow
├── OAgents/                       # OAgents
├── YunqueAgent/                   # 云雀 DeepResearch Agent
├── pydantic-deepagents/           # Pydantic AI DeepResearch
├── requirements_tier1.txt         # tier1 声明式依赖
├── requirements_tier1_freeze.txt  # tier1 精确版本锁定
├── requirements_yunque.txt        # yunque 精确版本锁定
├── setup_envs.sh                  # 一键环境配置脚本
├── run_infoagent.sh               # InfoAgent 运行脚本
├── run_miroflow.sh                # MiroFlow 运行脚本
├── run_oagents.sh                 # OAgents 运行脚本
├── run_pydantic_deepagents.sh     # pydantic-deepagents 运行脚本
├── run_yunqueagent.sh             # YunqueAgent 运行脚本
└── SETUP.md                       # 本文档
```

## 常见问题

**Q: `python3.12` 找不到？**
A: 如果用 `uv` 安装的 Python，路径通常在 `~/.local/share/uv/python/cpython-3.12.*/bin/python3.12`。`setup_envs.sh` 会自动检测。

**Q: 某些包安装失败？**
A: `requirements_tier1_freeze.txt` 和 `requirements_yunque.txt` 是从 macOS x86_64 导出的精确版本。如果在 Linux/ARM Mac 上部分包版本不可用，可以改用 `requirements_tier1.txt`（声明式依赖，pip 会自动解析兼容版本）。

**Q: 能不能合并成一个环境？**
A: 不行。YunqueAgent 需要 openai==1.99.5 而其他项目需要 openai>=2.2。这两个版本的 API 不兼容。
