#!/bin/bash

QUESTION="${1:-What are the latest advances in AI agent frameworks for deep research?}"

cd /Users/liyc/Desktop/推理框架/deepresearch_collection/pydantic-deepagents/deepresearch
source /Users/liyc/Desktop/推理框架/deepresearch_collection/.venv_tier1/bin/activate

python run_headless.py "$QUESTION"
