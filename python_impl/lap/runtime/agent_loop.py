"""Agent Loop — 用 LAP 描述 + 绑定真实 Router 的编程 Agent

复刻 OpenHands CodeAct Agent 的调度逻辑:
- 4 个工具: bash, str_replace_editor, finish, think
- 多 tool_call 支持
- StuckDetector 循环检测
- EventBus 全程事件驱动
"""

from __future__ import annotations

import platform

from lap.protocol.anchor import (
    AnchorSpec,
    Route,
    RouteAction,
    TransformerSpec,
    TransformMethod,
    ValidatorKind,
    ValidatorSpec,
    VerdictKind,
)
from lap.protocol.pipeline import (
    NodeKind,
    PipelineEdge,
    PipelineNode,
    PipelineSpec,
)
from lap.runtime.llm import LLMClient
from lap.runtime.router import ContextRouter, LLMRouter, Router, ToolRouter
from lap.runtime.runner import PipelineRunner
from lap.runtime.tool_executor import ToolExecutor

DEFAULT_SYSTEM_PROMPT = f"""\
You are a helpful assistant that can execute bash commands and edit files on the local machine.

You have the following tools available:
- **bash**: Execute bash commands. Use this for running programs, installing packages, etc.
- **str_replace_editor**: View, create, and edit files. Supports: view, create, str_replace, insert, undo_edit.
- **think**: Log your reasoning process. Use this to brainstorm, plan, or analyze before acting.
- **finish**: Signal that you have completed the task. Always call this when done.

## Workflow

1. Understand the task. Use `think` if you need to plan.
2. Use `str_replace_editor` with `view` to examine files and directories.
3. Use `str_replace_editor` with `create` or `str_replace` to make changes.
4. Use `bash` to run commands, tests, etc.
5. Call `finish` with a summary when done.

## Important Guidelines

- Always use absolute file paths (starting with /).
- When editing files, use `str_replace` with enough context to uniquely identify the replacement target.
- Verify your changes by viewing the file or running tests after editing.
- If a command fails, analyze the error and try a different approach.
- Do not run interactive commands (vim, nano, etc.). Use str_replace_editor instead.

<system_info>
{platform.system()} {platform.release()} {platform.machine()}
</system_info>
"""


def build_agent_pipeline() -> PipelineSpec:
    """构建 Agent Loop 的 PipelineSpec (声明)"""

    context_node = PipelineNode(
        id="context",
        kind=NodeKind.TRANSFORMER,
        transformer=TransformerSpec(
            id="context-router",
            name="Context 拼接器",
            from_format="tool-observation",
            to_format="agent-state",
            method=TransformMethod.RULE,
            description="将 user_input / tool_results 拼接为 Anthropic messages 格式",
        ),
    )

    llm_node = PipelineNode(
        id="llm",
        kind=NodeKind.ANCHOR,
        anchor=AnchorSpec(
            id="llm-router",
            name="LLM 语义整流器",
            format_in="agent-state",
            format_out="agent-action",
            validator=ValidatorSpec(
                id="llm",
                kind=ValidatorKind.SOFT,
                description="LLM 调用: 接收 messages, 产出 response (支持多工具调用)",
            ),
            routes={
                VerdictKind.PASS: Route(
                    action=RouteAction.EMIT,
                    feedback="LLM 调用 finish / 返回纯文本, 任务结束",
                ),
                VerdictKind.FAIL: Route(
                    action=RouteAction.NEXT,
                    target="tool",
                    feedback="LLM 请求工具执行 (bash/editor/think)",
                ),
            },
        ),
    )

    tool_node = PipelineNode(
        id="tool",
        kind=NodeKind.ANCHOR,
        anchor=AnchorSpec(
            id="tool-router",
            name="工具执行整流器",
            format_in="agent-action",
            format_out="tool-observation",
            validator=ValidatorSpec(
                id="tool-executor",
                kind=ValidatorKind.HARD,
                description="按 tool_name 分发执行: bash, str_replace_editor, think",
            ),
            routes={
                VerdictKind.PASS: Route(
                    action=RouteAction.NEXT,
                    target="context",
                    feedback="工具执行完成, 结果回到 Context 拼接",
                ),
                VerdictKind.FAIL: Route(
                    action=RouteAction.NEXT,
                    target="context",
                    feedback="工具执行失败, 错误信息回到 Context 拼接",
                ),
            },
        ),
    )

    return PipelineSpec(
        id="agent-loop",
        name="LAP CodeAct Agent Loop",
        description="ContextRouter -> LLMRouter -> ToolRouter 循环 (复刻 OpenHands 调度逻辑)",
        nodes=[context_node, llm_node, tool_node],
        edges=[
            PipelineEdge(source="context", target="llm", label="messages 就绪"),
            PipelineEdge(source="llm", target="tool", condition=VerdictKind.FAIL, label="需要工具"),
            PipelineEdge(source="tool", target="context", label="工具结果回拼"),
        ],
        entry="context",
    )


def build_bindings(
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: int = 30,
) -> dict[str, Router]:
    """构建 Router 绑定 (实现)"""
    client = LLMClient(model=model, base_url=base_url, api_key=api_key)
    executor = ToolExecutor(timeout=timeout)
    return {
        "context": ContextRouter(),
        "llm": LLMRouter(client),
        "tool": ToolRouter(executor=executor),
    }


async def run_agent(
    task: str,
    *,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    max_steps: int = 50,
    db_path: str | None = None,
) -> str:
    """运行 LAP CodeAct Agent (EventBus 驱动)

    Args:
        task: 用户任务描述
        system_prompt: 系统提示词
        model/base_url/api_key: LLM 配置 (默认从环境变量读取)
        max_steps: 最大执行步数
        db_path: SQLite 事件库路径 (默认 data/events.db)

    Returns:
        Agent 的最终输出
    """
    from pathlib import Path
    from lap.bus.sqlite import SQLiteBus

    db = Path(db_path) if db_path else Path("data/events.db")
    db.parent.mkdir(parents=True, exist_ok=True)

    pipeline = build_agent_pipeline()
    bindings = build_bindings(model=model, base_url=base_url, api_key=api_key)

    async with SQLiteBus(db) as bus:
        runner = PipelineRunner(pipeline, bindings, bus, max_steps=max_steps)
        result = await runner.run({
            "system_prompt": system_prompt,
            "user_input": task,
            "messages": [],
        })
        return result
