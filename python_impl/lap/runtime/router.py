"""Router — Anchor 的运行时执行实现

Router 是 LAP 中 Anchor 的运行时绑定:
    PipelineSpec 描述"是什么" (声明)
    Router 实现"怎么做" (执行)

三个内置 Router:
    ContextRouter — 拼接 messages (确定性, 总是 PASS)
    LLMRouter     — 调用 LLM (语义整流器), 支持多工具分发
    ToolRouter    — 执行工具 (确定性整流器), 支持 bash/editor/think
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from lap.protocol.anchor import Verdict, VerdictKind
from lap.runtime.llm import LLMClient
from lap.runtime.tool_executor import ToolExecutor


class Router(ABC):
    """Router 运行时接口"""

    @abstractmethod
    def run(self, input_data: Any) -> Verdict:
        ...


class ContextRouter(Router):
    """拼接 messages — 确定性整流器

    输入: dict with keys:
        system_prompt: str
        user_input: str (首轮) 或 None (后续轮)
        messages: list[dict] (已有的 messages 历史)
        tool_results: list[dict] | None (工具执行结果列表, 多 tool_call 支持)
        tool_result: str | None (单个工具结果, 向后兼容)
        tool_use_id: str | None (单个 tool_use id, 向后兼容)

    输出 (PASS): 完整的 messages list (Anthropic 格式)
    """

    def run(self, input_data: Any) -> Verdict:
        messages: list[dict] = list(input_data.get("messages", []))
        user_input = input_data.get("user_input")
        tool_results = input_data.get("tool_results")

        if user_input and not messages:
            # 首轮: 加入用户输入
            messages.append({"role": "user", "content": user_input})
        elif tool_results:
            # 后续轮: 加入所有工具执行结果 (批量)
            content_blocks = []
            for tr in tool_results:
                content_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tr["tool_use_id"],
                    "content": tr["content"],
                })
            messages.append({"role": "user", "content": content_blocks})

        return Verdict(
            kind=VerdictKind.PASS,
            output={
                "system_prompt": input_data.get("system_prompt", ""),
                "messages": messages,
            },
        )


class LLMRouter(Router):
    """调用 LLM — 语义整流器

    输入: dict with system_prompt + messages
    输出:
        PASS (finish tool_call 或纯文本) → 最终结果, 退出管线
        FAIL (有可执行 tool_call) → 工具调用列表, 需要 ToolRouter
    """

    def __init__(self, client: LLMClient):
        self.client = client

    def run(self, input_data: Any) -> Verdict:
        system_prompt = input_data.get("system_prompt", "")
        messages = input_data.get("messages", [])

        response = self.client.call(messages=messages, system=system_prompt)

        # 从 response 中提取文本和 tool_use
        text_parts = []
        tool_uses = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        text_output = "\n".join(text_parts)

        # 构建 assistant message (包含所有 content blocks)
        assistant_content = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        updated_messages = messages + [{"role": "assistant", "content": assistant_content}]

        # 无 tool_call → PASS → 管线出口
        if not tool_uses:
            return Verdict(
                kind=VerdictKind.PASS,
                output=text_output,
            )

        # 检查是否有 finish tool_call → PASS → 管线出口
        for tool in tool_uses:
            if tool.name == "finish":
                return Verdict(
                    kind=VerdictKind.PASS,
                    output=tool.input.get("message", text_output),
                )

        # 有可执行 tool_call → FAIL → ToolRouter
        tool_calls = []
        for tool in tool_uses:
            tool_calls.append({
                "tool_name": tool.name,
                "tool_args": tool.input,
                "tool_use_id": tool.id,
            })

        return Verdict(
            kind=VerdictKind.FAIL,
            output={
                "tool_calls": tool_calls,
                "text": text_output,
                "system_prompt": system_prompt,
                "messages": updated_messages,
            },
            diagnosis=f"LLM requests {len(tool_calls)} tool(s): {', '.join(tc['tool_name'] for tc in tool_calls)}",
        )


class ToolRouter(Router):
    """执行工具 — 确定性整流器

    输入: dict with tool_calls, messages, system_prompt
    输出 (PASS): 所有工具执行结果 + 回传给 ContextRouter 的数据
    """

    def __init__(self, executor: ToolExecutor | None = None):
        self.executor = executor or ToolExecutor()

    def run(self, input_data: Any) -> Verdict:
        tool_calls = input_data.get("tool_calls", [])
        tool_results = []

        for tc in tool_calls:
            tool_name = tc["tool_name"]
            tool_args = tc["tool_args"]
            tool_use_id = tc["tool_use_id"]

            result = self.executor.execute(tool_name, tool_args)
            tool_results.append({
                "tool_use_id": tool_use_id,
                "content": result,
            })

        return Verdict(
            kind=VerdictKind.PASS,
            output={
                "system_prompt": input_data.get("system_prompt", ""),
                "messages": input_data.get("messages", []),
                "tool_results": tool_results,
            },
        )
