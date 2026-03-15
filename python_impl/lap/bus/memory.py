"""
InMemoryBus — 内存事件总线

默认实现，零外部依赖。使用 asyncio.Queue 在进程内分发事件。
适用于: 单进程场景、测试、本地 demo。

支持:
- 语义标签过滤 (tags): AND 语义，事件必须包含所有指定标签
- 组隔离 (group): 同组共享一个 Queue，组内竞争消费

当需要跨进程通信时，切换到 RedisBus (bus/client.py, 需 redis 可选依赖)。
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Sequence

from lap.bus.base import EventBus
from lap.protocol.events import FactoryEvent
from lap.protocol.registry import EventType

logger = logging.getLogger(__name__)


class InMemoryBus(EventBus):
    """内存事件总线

    EventBus 的默认实现。所有事件在进程内通过 asyncio.Queue 分发。
    trace 级别的事件存储在 dict 中，支持 read_trace 回放。

    组隔离: 同 group 的多个 subscribe 调用共享一个 Queue，
    事件只被组内一个消费者处理 (竞争消费)。
    不同 group 各自独立消费 (广播)。
    """

    def __init__(self):
        self._traces: dict[str, list[FactoryEvent]] = defaultdict(list)
        self._global: list[FactoryEvent] = []
        # 组隔离: group_name → shared queue
        self._group_queues: dict[str, asyncio.Queue[FactoryEvent]] = {}
        # 无组订阅: 每个订阅者独立 queue (广播)
        self._broadcast_queues: list[asyncio.Queue[FactoryEvent]] = []

    async def connect(self) -> None:
        logger.info("InMemoryBus ready")

    async def close(self) -> None:
        pass

    async def publish(self, event: FactoryEvent) -> str:
        self._traces[event.trace_id].append(event)
        self._global.append(event)

        # 广播到所有组 queue
        for q in self._group_queues.values():
            await q.put(event)

        # 广播到无组订阅者
        for q in self._broadcast_queues:
            await q.put(event)

        logger.debug("Published %s [%s] tags=%s", event.event_type, event.id, event.tags)
        return event.id

    async def subscribe(
        self,
        group: str,
        consumer: str,
        *,
        event_types: Sequence[str | EventType] | None = None,
        tags: Sequence[str] | None = None,
    ) -> AsyncIterator[FactoryEvent]:
        # 组隔离: 同组共享 queue
        if group:
            if group not in self._group_queues:
                self._group_queues[group] = asyncio.Queue()
            q = self._group_queues[group]
            is_group = True
        else:
            q = asyncio.Queue()
            self._broadcast_queues.append(q)
            is_group = False

        type_filter: set[str] | None = None
        if event_types:
            type_filter = {
                t.value if isinstance(t, EventType) else t for t in event_types
            }

        tag_filter: set[str] | None = None
        if tags:
            tag_filter = set(tags)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break

                if type_filter and event.event_type not in type_filter:
                    continue
                # 标签过滤: 事件的 tags 必须包含订阅指定的所有 tags
                if tag_filter and not tag_filter.issubset(set(event.tags)):
                    continue
                yield event
        finally:
            if not is_group:
                self._broadcast_queues.remove(q)

    async def ack(self, event: FactoryEvent) -> None:
        pass  # no-op in memory mode

    async def read_trace(self, trace_id: str) -> list[FactoryEvent]:
        return list(self._traces.get(trace_id, []))

    async def tail(self) -> AsyncIterator[FactoryEvent]:
        q: asyncio.Queue[FactoryEvent] = asyncio.Queue()
        self._broadcast_queues.append(q)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=2.0)
                    yield event
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
        finally:
            self._broadcast_queues.remove(q)
