# Deep Research Framework Collection

5 个开源 deep research agent 框架的集合，统一配置、统一运行脚本，用于对比评测各框架生成深度研究报告的能力。

## 框架一览

| 框架 | 来源 | 虚拟环境 | 运行脚本 |
|------|------|---------|---------|
| **InfoAgent** | Microsoft Research | `.venv_tier1` | `run_infoagent.sh` |
| **MiroFlow** | Samsung Research | `.venv_tier1` | `run_miroflow.sh` |
| **OAgents** | 社区开源 | `.venv_tier1` | `run_oagents.sh` |
| **pydantic-deepagents** | Pydantic AI 生态 | `.venv_tier1` | `run_pydantic_deepagents.sh` |
| **YunqueAgent** | 云雀 DeepResearch | `.venv_yunque` | `run_yunqueagent.sh` |

YunqueAgent 的依赖版本与其他 4 个不兼容（openai 1.x vs 2.x），因此使用独立虚拟环境。

## 快速开始

```bash
# 1. 一键配置两个虚拟环境（需要 Python >= 3.12）
bash setup_envs.sh

# 2. 配置各框架的 .env 文件（填入 API Key）
#    详见 SETUP.md

# 3. 运行任意框架生成研究报告
bash run_infoagent.sh "你的研究主题"
bash run_yunqueagent.sh "你的研究主题"
```

## 文档

- 环境配置：[SETUP.md](SETUP.md)
- 五个框架的内部架构对比（多轮调用流程、报告生成机制）：[ARCHITECTURE.md](ARCHITECTURE.md)
