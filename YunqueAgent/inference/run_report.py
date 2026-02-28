"""
YunqueAgent Deep Research Report 模式入口脚本。

用法：
    python run_report.py --question "你的研究主题" --output ../output

会自动从 .env 读取模型和 API 配置。
"""

import argparse
import asyncio
import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path

# 加载 .env
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"Loaded .env from {env_path}")
else:
    print(f"Warning: .env not found at {env_path}")

from agent import Agent


def sanitize_filename(text: str, max_len: int = 60) -> str:
    """将问题文本转为安全的文件名。"""
    sanitized = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', text)
    sanitized = re.sub(r'\s+', '_', sanitized.strip())
    return sanitized[:max_len] if sanitized else "report"


def main():
    parser = argparse.ArgumentParser(description="YunqueAgent Deep Research Report Generator")
    parser.add_argument("--question", type=str, required=True, help="Research topic / question")
    parser.add_argument("--output", type=str, default="../output", help="Output directory for the report")
    parser.add_argument("--temperature", type=float, default=0.7, help="LLM temperature")
    parser.add_argument("--top_p", type=float, default=0.95, help="LLM top_p")
    parser.add_argument("--presence_penalty", type=float, default=1.1, help="LLM presence penalty")
    args = parser.parse_args()

    question = args.question
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    model = os.getenv("LLM_MODEL", "bytedance-seed/seed-1.6")
    print(f"Research question: {question}")
    print(f"Model: {model}")
    print(f"Output directory: {output_dir}")

    # 构造 Agent 需要的 LLM config
    llm_cfg = {
        "model": model,
        "generate_cfg": {
            "temperature": args.temperature,
            "top_p": args.top_p,
            "presence_penalty": args.presence_penalty,
        },
    }

    # 构造与 Agent._run 兼容的数据格式
    data = {
        "item": {
            "question": question,
            "answer": "",  # 报告模式无标准答案
        },
        "rollout_idx": 1,
    }

    # 创建报告模式 Agent
    agent = Agent(
        llm=llm_cfg,
        function_list=["search", "visit", "google_scholar"],
        report_mode=True,
    )

    print("\n" + "=" * 60)
    print("Starting deep research report generation...")
    print("=" * 60 + "\n")

    # 运行 Agent
    result = asyncio.run(agent._run(data, model))

    # 提取报告
    prediction = result.get("prediction", "")
    termination = result.get("termination", "")

    print("\n" + "=" * 60)
    print(f"Research completed. Termination: {termination}")
    print("=" * 60)

    # 保存报告为 Markdown 文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = sanitize_filename(question)
    report_filename = f"{timestamp}_{safe_name}.md"
    report_path = output_dir / report_filename

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(prediction)

    print(f"\nReport saved to: {report_path}")
    print(f"Report length: {len(prediction)} characters")

    # 同时保存完整结果（包含 traces）为 JSON
    result_path = output_dir / f"{timestamp}_{safe_name}_full.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Full result saved to: {result_path}")

    # 打印报告预览
    print("\n" + "=" * 60)
    print("REPORT PREVIEW (first 2000 chars):")
    print("=" * 60)
    print(prediction[:2000])
    if len(prediction) > 2000:
        print(f"\n... ({len(prediction) - 2000} more characters)")


if __name__ == "__main__":
    main()
