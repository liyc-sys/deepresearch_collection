# 五个 Deep Research 框架的内部架构对比

本文档分析仓库中五个框架各自如何通过多轮调用完成最终的 research report。

---

## 总览：执行流程对比

| 框架 | 核心模式 | 搜索→报告的路径 | 多轮控制方式 | 报告生成策略 |
|------|---------|---------------|-------------|------------|
| InfoAgent | LangGraph 状态图循环 | 搜索→访问→总结→下一轮→最终合成 | 固定轮数（max_cycles） | 所有轮次摘要一次性合成 |
| MiroFlow | 单 Agent 工具循环 + 子 Agent | 搜索→抓取→推理→继续/停止→总结 | LLM 自主决定停止 | 对话历史整体总结 |
| OAgents | Manager-Worker 多 Agent 委派 | Manager 分解→Worker 搜索→Manager 合成 | Manager 步数限制 | 从 memory 中提取所有观测合成 |
| pydantic-deepagents | 异步并行子 Agent + 渐进写作 | Planner 规划→并行子 Agent 研究→逐节写入 | TODO 列表驱动 | 逐节增量写入文件 |
| YunqueAgent | 单 Agent ReAct 循环 + 动态上下文管理 | 搜索→访问→记忆更新→继续→合成 | 调用次数/token/超时三重限制 | 收集研究素材后 LLM 合成 |

---

## 1. InfoAgent（Re-TRAC）

**框架基座**: LangGraph StateGraph

### 架构图

```
用户问题
  ↓
init_graph ── 初始化 state（消息列表、cycle 历史）
  ↓
┌─────────── 研究循环（最多 max_cycles 轮）──────────┐
│                                                    │
│  start_cycle ── 注入上一轮摘要作为"记忆"            │
│      ↓                                             │
│  ┌── llm ── LLM 推理，决定搜索/访问/结束           │
│  │    ↓                                            │
│  │  [有 tool_call?]                                │
│  │    ├─ 是 → tools_prep → tools → tools_merge     │
│  │    │        （执行搜索/访问，结果合并回消息）       │
│  │    │        └→ 回到 llm（继续推理）              │
│  │    │                                            │
│  │    └─ 否 → end_cycle                            │
│  │              ↓                                  │
│  │         LLM 总结本轮发现（结构化格式：             │
│  │         当前答案/证据/分析/来源/不确定性）          │
│  │              ↓                                  │
│  │         [达到 max_cycles?]                       │
│  │            ├─ 否 → start_cycle（下一轮）          │
│  │            └─ 是 → final                        │
│  └──────────────────────────────────────────────── │
└────────────────────────────────────────────────────┘
  ↓
final ── 将所有轮次摘要送入 LLM，合成最终 Markdown 报告
  ↓
保存 .md 文件
```

### 关键设计

- **递归轨迹压缩**：每轮结束时，LLM 用结构化 prompt 总结当前发现，特别标注"不确定性与信息缺口"。下一轮的 `continue_prompt` 会注入这些缺口，引导 LLM 扩展搜索方向。
- **LLM 调用点**：每轮内 N 次（推理+工具循环）+ 1 次总结 + 最终 1 次报告合成。2 轮研究约 5 次 LLM 调用。
- **工具**：`search`（Serper API 批量搜索）、`visit`（Jina API 抓取+摘要 LLM 提取关键信息）。
- **报告合成**：最终节点将所有轮次摘要拼接，通过 `report_synthesis_prompt` 一次性让 LLM 生成完整报告（Executive Summary → 引言 → 主体 → 分析 → 结论 → 参考文献）。

---

## 2. MiroFlow

**框架基座**: 自研 Orchestrator + MCP 工具服务器

### 架构图

```
用户问题
  ↓
Pipeline 初始化（加载 LLM Client、Tool Manager、Prompt Class）
  ↓
[可选] Hint 生成 ── 用 OpenAI 生成任务提示
  ↓
System Prompt 生成 ── 含所有可用 MCP 工具定义
  ↓
┌───────── 主 Agent 循环（while turn < max_turns）──────────┐
│                                                           │
│  LLM 调用 ── 发送完整消息历史 + 工具定义                     │
│      ↓                                                    │
│  [有 tool_call?]                                          │
│    ├─ search → Serper MCP 搜索                             │
│    ├─ scrape/read → Jina/Playwright 抓取                   │
│    ├─ python → E2B 沙箱执行代码                             │
│    ├─ agent-* → 委派给子 Agent（独立循环）                   │
│    ├─ 无 tool_call → 结束循环                               │
│    └→ 结果写回消息历史                                      │
│                                                           │
│  [上下文超限?] → 移除最早的消息对，重试                       │
└───────────────────────────────────────────────────────────┘
  ↓
最终总结阶段
  ├─ 生成 summarize_prompt（含报告格式要求）
  ├─ LLM 基于完整对话历史生成报告
  └─ 上下文超限时：逐步裁剪历史重试
  ↓
保存 .md 文件
```

### 关键设计

- **工具丰富**：通过 MCP 协议集成搜索（Serper）、网页抓取（Jina/Playwright）、代码执行（E2B）、音频转写、图像分析、推理增强等 8 类工具服务器。
- **子 Agent 机制**：当主 Agent 调用以 `agent-` 前缀开头的工具时，触发子 Agent 独立执行循环，返回处理后的结果而非原始数据。
- **上下文管理**：当对话历史超出 token 限制时，自动移除最早的 assistant-user 消息对，保留系统提示和最近内容，反复重试直到成功。
- **LLM 自主停止**：没有固定轮数限制（`max_turns: -1`），由 LLM 自行判断何时停止调用工具。
- **报告合成**：使用 `MainAgentPromptReport` 类的 `generate_summarize_prompt()`，要求 LLM 从完整对话历史中提取信息生成结构化报告。

---

## 3. OAgents

**框架基座**: 自研 MultiStepAgent（ReAct 模式）

### 架构图

```
用户问题
  ↓
Manager Agent (CodeAgent, max_steps=20)
  ↓
┌───────── Manager 步骤循环 ──────────────────────────────┐
│                                                         │
│  [Planning] Manager 分解研究任务为 4-6 个子话题            │
│      ↓                                                  │
│  [Step N] Manager 生成 Python 代码调用子 Agent            │
│      ↓                                                  │
│  search_agent(task="研究子话题 X")                        │
│      ↓                                                  │
│  ┌── Search Agent (ToolCallingAgent, max_steps=30) ──┐  │
│  │                                                    │  │
│  │  搜索循环：                                         │  │
│  │    search() → 获取搜索结果                           │  │
│  │    visit()  → 访问网页提取内容                       │  │
│  │    page_down/find → 浏览页面                        │  │
│  │    ...重复直到信息足够                                │  │
│  │      ↓                                             │  │
│  │  返回研究发现给 Manager                              │  │
│  └────────────────────────────────────────────────────┘  │
│      ↓                                                  │
│  Manager 记录结果到 Memory                               │
│  继续下一个子话题...                                      │
│                                                         │
│  [所有子话题完成后]                                       │
│  Manager 从 Memory 中所有观测合成最终报告                  │
└─────────────────────────────────────────────────────────┘
  ↓
保存 report.md
```

### 关键设计

- **Manager-Worker 层级**：Manager（CodeAgent）负责规划和合成，Worker（ToolCallingAgent）负责实际搜索。Manager 通过生成 Python 代码来调用 Worker。
- **搜索反射器**：`query_rollout()` 生成多种搜索查询变体，`query_reflect()` 基于 LLM 反馈优化查询，`result_reflect()` 分析搜索结果质量。
- **Memory 系统**：`AgentMemory` 记录每一步的 `ActionStep`（模型输出、工具调用、观测结果）和 `PlanningStep`（任务分解）。报告合成时遍历所有步骤提取信息。
- **两类执行器**：CodeAgent 通过 `LocalPythonInterpreter` 执行生成的 Python 代码；ToolCallingAgent 通过 JSON 格式调用预定义工具。
- **报告合成**：Manager 完成所有研究后，`_synthesize_report_from_memory()` 收集所有 step 的观测结果，发送给 LLM 一次性合成 Markdown 报告。
- **工具**：DuckDuckGo 搜索、Wikipedia 搜索、网页访问（含页面滚动/查找）、文件检查。

---

## 4. pydantic-deepagents

**框架基座**: Pydantic AI + 异步子 Agent 系统

### 架构图

```
用户问题
  ↓
Main Agent（含完整工具集）
  ↓
Step 1: 派遣 Planner 子 Agent
  ├─ 分析问题，提出澄清性问题
  ├─ 拆解为 4-6 个子话题
  └─ 保存计划到 /plans/
  ↓
Step 2: 创建 TODO 列表
  └─ 为每个子话题创建 pending 状态的 TODO
  ↓
Step 3: 并行派遣 N 个研究子 Agent（异步）
  ├─ task("研究子话题1", subagent="general-purpose", mode="async")
  ├─ task("研究子话题2", subagent="general-purpose", mode="async")
  ├─ task("研究子话题3", subagent="general-purpose", mode="async")
  └─ ...每个子 Agent 独立搜索→抓取→提取→保存到 /workspace/notes/
  ↓
Step 4: wait_tasks() ── 阻塞等待所有子 Agent 完成
  ↓
Step 5: 逐节合成报告
  ├─ read_file("/workspace/notes/topic1.md")
  ├─ 如有信息缺口，额外搜索补充
  ├─ edit_file("/workspace/report.md") ── 追加该节内容
  ├─ update_todo_status("t1", "completed")
  └─ 重复直到所有节完成
  ↓
保存最终 report.md
```

### 关键设计

- **真正的异步并行**：多个研究子 Agent 同时运行（`mode="async"`），通过 `wait_tasks()` 统一等待，显著缩短研究时间。
- **TODO 驱动流程**：用显式的 TODO 列表追踪研究进度，每完成一个子话题就更新状态，确保不遗漏。
- **MCP 工具生态**：通过 MCP 协议集成 Tavily、Jina、Brave、Firecrawl 等多种搜索/抓取服务，以及 Playwright 浏览器自动化。
- **渐进式报告写作**：不是最后一次性合成，而是逐节读取子 Agent 的研究笔记，逐节写入报告文件，可以随时补充和修改。
- **容错设计**：子 Agent 搜索失败时自动回退到模型自身知识，不会因工具错误中断整个流程。
- **Planner 子 Agent**：专门负责规划，会主动提出澄清性问题（headless 模式下自动选择选项），输出结构化的研究计划。
- **Checkpoint 系统**：支持 `save_checkpoint()` / `rewind_to()`，可在任意时刻保存/恢复会话状态。

---

## 5. YunqueAgent

**框架基座**: 自研 ReAct Agent + 动态上下文管理

### 架构图

```
用户问题
  ↓
Agent._run() 主循环（三重限制：75 次 LLM 调用 / 110K token / 90 分钟）
  ↓
┌───────── 推理循环 ────────────────────────────────────┐
│                                                       │
│  LLM 调用 ── 发送 system_prompt + 消息历史              │
│      ↓                                                │
│  [输出包含 <tool_call>?]                               │
│    ├─ search → Serper API 批量搜索                     │
│    ├─ visit → Jina 抓取 + 摘要 LLM 提取               │
│    ├─ google_scholar → 学术搜索                        │
│    ├─ CodeExecutor → SandboxFusion 执行 Python          │
│    └─ 无 → Supervisor 介入纠正                         │
│      ↓                                                │
│  [上下文管理] Memory Manager（独立 LLM 调用）            │
│    ├─ 提取当前 sub-goal                                │
│    ├─ 判断 merge（继续当前子目标）或 new（新子目标）      │
│    ├─ 生成 MemoryUnit（sub_goal + tools_log + summary） │
│    └─ 当开始新子目标时：                                │
│        用 memory 摘要替换旧消息 → 大幅压缩上下文          │
│      ↓                                                │
│  [检测到 <report> 标签?] → 终止循环                     │
│  [接近限制?] → 强制合成报告                             │
└───────────────────────────────────────────────────────┘
  ↓
报告提取 / 合成
  ├─ 正常结束：从 <report> 标签提取报告内容
  └─ 强制结束：_synthesize_report() 从研究轨迹提取素材合成
  ↓
保存 .md 文件
```

### 关键设计

- **动态上下文管理**：独立的 Memory Manager（使用单独的 LLM）在每次工具调用后更新 MemoryUnit。当 Agent 开始新的 sub-goal 时，用压缩后的 memory 摘要替换完整的历史消息，将消息数从 N 压缩到约 5 条，防止上下文溢出。
- **三重保护机制**：LLM 调用次数（75）、总 token 数（110K）、执行时间（90 分钟）任一达到限制即停止，并触发报告合成。
- **Supervisor 监督**：独立的 Supervisor 模块监控 Agent 行为，处理截断响应、缺失工具调用、接近限制等异常情况，自动介入纠正或提取答案。
- **报告模式**：使用 `REPORT_SYSTEM_PROMPT` 替代原始 QA prompt，检测 `<report>` 而非 `<answer>` 标签作为终止信号。任何限制触发时，`_synthesize_report()` 从所有研究轨迹中提取素材，调用 LLM 合成完整报告。
- **工具**：`search`（批量 Google 搜索）、`visit`（网页抓取+深度分析）、`google_scholar`（学术搜索）、`CodeExecutor`（Python 沙箱执行，可选）。

---

## 横向对比

### 搜索策略

| 框架 | 搜索引擎 | 网页抓取 | 学术搜索 | 代码执行 |
|------|---------|---------|---------|---------|
| InfoAgent | Serper | Jina + 摘要 LLM | - | - |
| MiroFlow | Serper | Jina / Playwright | - | E2B 沙箱 |
| OAgents | DuckDuckGo / SerpAPI | 文本浏览器（滚动/查找） | - | 本地 Python |
| pydantic-deepagents | Tavily / Brave / Firecrawl | Jina / Playwright | - | Docker 沙箱 |
| YunqueAgent | Serper | Jina + 摘要 LLM | Google Scholar | SandboxFusion |

### 多轮研究的控制机制

| 框架 | 轮数控制 | 停止条件 | 信息积累方式 |
|------|---------|---------|------------|
| InfoAgent | 固定 max_cycles | 轮数耗尽 | 每轮摘要（含缺口分析）→ 下轮输入 |
| MiroFlow | 无固定限制 | LLM 不再调用工具 | 完整对话历史（超限时裁剪旧消息） |
| OAgents | Manager max_steps | 步数耗尽或 Manager 决定 | Memory 中的 ActionStep 列表 |
| pydantic-deepagents | TODO 列表驱动 | 所有 TODO 完成 | 子 Agent 写入独立笔记文件 |
| YunqueAgent | 75 次调用 / 110K token / 90 分钟 | 三重限制任一触发 | MemoryUnit 动态压缩（sub-goal 粒度） |

### 报告生成方式

| 框架 | 时机 | 方式 | 输入 |
|------|------|------|------|
| InfoAgent | 所有轮次结束后 | 一次性 LLM 合成 | 所有轮次的结构化摘要 |
| MiroFlow | 主循环结束后 | 一次性 LLM 总结（含重试） | 完整对话历史 |
| OAgents | Manager 完成后 | 一次性 LLM 合成 | Memory 中所有 step 的观测 |
| pydantic-deepagents | 研究过程中 | 逐节增量写入文件 | 各子 Agent 的笔记文件 |
| YunqueAgent | Agent 输出 `<report>` 或触发限制 | Agent 自行产出或强制合成 | 研究轨迹中的分析和工具响应 |
