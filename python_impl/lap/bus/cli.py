"""
omni-bus CLI — 事件总线实时监控工具

用法:
    omni-bus tail              # 实时 tail 全局事件流
    omni-bus tail --from-start # 从头读取所有历史事件
    omni-bus trace <trace_id>  # 查看特定任务的完整事件链
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime

import click

from lap.bus.client import OmniBusClient
from lap.protocol.events import FactoryEvent


# 终端着色

_COLORS = {
    "task.": "green",
    "agent.llm.": "cyan",
    "agent.tool.": "yellow",
    "agent.think": "white",
    "agent.state.": "magenta",
    "agent.delegate": "blue",
    "system.": "red",
}


def _color_for(event_type: str) -> str:
    for prefix, color in _COLORS.items():
        if event_type.startswith(prefix):
            return color
    return "white"


def _format_event(event: FactoryEvent) -> str:
    """格式化单个事件为终端可读行"""
    ts = event.timestamp.strftime("%H:%M:%S.%f")[:-3]
    etype = event.event_type.ljust(22)
    source = event.source.ljust(20)

    # 从 payload 中提取关键信息作为摘要
    summary_parts: list[str] = []
    p = event.payload

    if "instruction" in p:
        summary_parts.append(f'"{p["instruction"][:60]}"')
    if "message" in p:
        summary_parts.append(f'"{p["message"][:60]}"')
    if "tool" in p:
        summary_parts.append(f'tool={p["tool"]}')
    if "args" in p and isinstance(p["args"], dict):
        args_str = " ".join(f'{k}={v}' for k, v in list(p["args"].items())[:3])
        summary_parts.append(args_str)
    if "from_state" in p and "to_state" in p:
        summary_parts.append(f'{p["from_state"]} → {p["to_state"]}')
    if "status" in p:
        summary_parts.append(f'status={p["status"]}')
    if "result" in p:
        r = str(p["result"])
        summary_parts.append(r[:60])

    # metadata 摘要
    if event.metadata:
        m = event.metadata
        if m.prompt_tokens:
            summary_parts.append(f"tokens={m.prompt_tokens}+{m.completion_tokens or 0}")
        if m.cost_usd:
            summary_parts.append(f"${m.cost_usd:.4f}")
        if m.duration_ms:
            summary_parts.append(f"{m.duration_ms:.0f}ms")

    summary = "  ".join(summary_parts) if summary_parts else ""

    color = _color_for(event.event_type)
    colored_type = click.style(etype, fg=color, bold=True)
    colored_source = click.style(source, fg="bright_black")

    return f"[{ts}] {colored_type} {colored_source} {summary}"


# CLI 命令


@click.group()
def main():
    """OmniBus CLI — OmniFactory 事件总线监控"""
    pass


@main.command()
@click.option("--redis", default="redis://localhost:6379", help="Redis URL")
@click.option("--from-start", is_flag=True, help="从流的起始位置读取 (含历史)")
def tail(redis: str, from_start: bool):
    """实时 tail 全局事件流"""
    asyncio.run(_tail(redis, from_start))


async def _tail(redis_url: str, from_start: bool):
    click.echo(click.style("OmniBus Tail — Ctrl+C to exit", fg="bright_black"))
    click.echo(click.style("─" * 80, fg="bright_black"))

    last_id = "0-0" if from_start else "$"

    async with OmniBusClient(redis_url) as bus:
        try:
            async for event in bus.tail(last_id=last_id):
                click.echo(_format_event(event))
        except KeyboardInterrupt:
            pass


@main.command()
@click.argument("trace_id")
@click.option("--redis", default="redis://localhost:6379", help="Redis URL")
def trace(trace_id: str, redis: str):
    """查看特定任务的完整事件链"""
    asyncio.run(_trace(trace_id, redis))


async def _trace(trace_id: str, redis_url: str):
    async with OmniBusClient(redis_url) as bus:
        events = await bus.read_trace(trace_id)

    if not events:
        click.echo(f"No events found for trace {trace_id}")
        return

    click.echo(click.style(f"Trace: {trace_id}  ({len(events)} events)", bold=True))
    click.echo(click.style("─" * 80, fg="bright_black"))

    for event in events:
        click.echo(_format_event(event))


if __name__ == "__main__":
    main()
