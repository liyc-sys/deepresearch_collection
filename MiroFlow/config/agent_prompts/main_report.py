from config.agent_prompts.main_boxed_answer import MainAgentPromptBoxedAnswer


class MainAgentPromptReport(MainAgentPromptBoxedAnswer):
    """
    Report-oriented prompt class. Inherits system prompt and tool-use logic
    from MainAgentPromptBoxedAnswer, but replaces the summarize prompt to
    generate a full Markdown research report instead of a \boxed{} answer.
    """

    def generate_summarize_prompt(
        self,
        task_description: str,
        task_failed: bool = False,
        chinese_context: bool = False,
    ) -> str:
        summarize_prompt = (
            (
                "============="
                "============="
                "============="
                "This is a direct instruction to you (the assistant), not the result of a tool call.\n\n"
            )
            + (
                "**Important: You have either exhausted the context token limit or reached the maximum number of interaction turns. "
                "You must now synthesize all gathered information into a comprehensive research report.**\n\n"
                if task_failed
                else ""
            )
            + (
                "We are now ending this research session. Your conversation history will be deleted after this response. "
                "You must NOT initiate any further tool use. This is your final opportunity to produce the research report.\n\n"
                "## Your Task\n\n"
                "Based on ALL the information you have gathered during this research session, "
                "synthesize a **comprehensive, well-structured Markdown research report** that fully addresses the original research topic.\n\n"
                "The original research topic is repeated here for reference:\n\n"
                f"---\n{task_description}\n---\n\n"
                "## Report Requirements\n\n"
                "Your report MUST follow this structure:\n\n"
                "1. **Executive Summary**: A concise overview of key findings (2-3 paragraphs)\n"
                "2. **Introduction**: Background context, scope of research, and methodology used\n"
                "3. **Main Body**: Organized into logical chapters/sections based on the research topic. "
                "Each section should have a clear heading and present findings with supporting evidence, data, and citations.\n"
                "4. **Analysis & Discussion**: Cross-cutting analysis, synthesis of findings, identification of patterns, "
                "contradictions, or gaps in the evidence\n"
                "5. **Conclusion**: Summary of key takeaways and implications\n"
                "6. **References**: List all sources consulted during research, with URLs where available\n\n"
                "## Quality Standards\n\n"
                "- Include specific facts, data points, statistics, and direct quotes from sources\n"
                "- Clearly attribute information to its sources\n"
                "- Distinguish between well-established facts and uncertain/conflicting information\n"
                "- Use Markdown formatting: headers (##, ###), bullet points, numbered lists, tables where appropriate\n"
                "- If the research topic specifies a particular structure, follow that structure instead of the default one above\n"
                "- Do NOT include tool call instructions, meta-commentary about the research process, or speculative filler\n"
                "- Focus on delivering substantive, well-organized content\n"
                "- The report should be thorough and detailed — aim for comprehensive coverage rather than brevity\n"
            )
        )

        if chinese_context:
            summarize_prompt += """

## 中文报告要求

如果原始研究主题涉及中文语境：
- **报告语言**：使用中文撰写完整报告
- **术语处理**：使用恰当的中文学术术语和表达习惯
- **信息保真**：保持中文资源的原始格式和表达方式，避免不必要的翻译
- **结构规范**：按照中文学术报告的规范组织内容
- **引用格式**：参考文献中保留原始语言的标题和链接
"""
        return summarize_prompt
