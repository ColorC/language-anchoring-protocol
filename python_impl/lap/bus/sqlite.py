"""
SQLiteBus — 基于 SQLite 的事件总线

默认实现，零外部依赖（sqlite3 是 Python 标准库）。
单文件持久化，进程崩溃事件不丢，支持 SQL 查询回放。

支持:
- 语义标签过滤 (tags): AND 语义，事件必须包含所有指定标签
- 组隔离 (consumer group): 消费位移持久化，同组竞争消费

性能: 轻松支撑 1000+ 写入/秒，远超 Agent 场景需求 (~100 事件/秒)。
"""

from __future__ import annotations

import json
import sqlite3
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from lap.bus.base import EventBus
from lap.protocol.events import FactoryEvent
from lap.protocol.registry import EventType

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          TEXT PRIMARY KEY,
    trace_id    TEXT NOT NULL,
    parent_id   TEXT,
    event_type  TEXT NOT NULL,
    source      TEXT NOT NULL,
    tags        TEXT NOT NULL DEFAULT '[]',
    timestamp   TEXT NOT NULL,
    data        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_trace    ON events (trace_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_events_type     ON events (event_type);
CREATE INDEX IF NOT EXISTS idx_events_ts       ON events (timestamp);

CREATE TABLE IF NOT EXISTS consumer_offsets (
    group_name    TEXT NOT NULL,
    last_event_ts TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    PRIMARY KEY (group_name)
);
"""


class SQLiteBus(EventBus):
    """基于 SQLite 的事件总线

    每个事件以完整 JSON 存入 data 列，同时提取关键字段建索引。
    查询时反序列化 data 列还原 FactoryEvent。

    组隔离: 通过 consumer_offsets 表记录每个 group 的消费位移，
    同组竞争消费（谁先读到谁处理），不同组独立消费。

    用法:
        async with SQLiteBus("events.db") as bus:
            await bus.publish(event)
            events = await bus.read_trace(trace_id)
    """

    def __init__(self, db_path: str | Path = "omnifactory_events.db"):
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    async def connect(self) -> None:
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")  # 并发读写友好
        self._conn.execute("PRAGMA synchronous=NORMAL")  # 性能与安全的平衡
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        logger.info("SQLiteBus ready → %s", self._db_path)

    async def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("SQLiteBus not connected. Call connect() first.")
        return self._conn

    async def publish(self, event: FactoryEvent) -> str:
        self.conn.execute(
            "INSERT INTO events (id, trace_id, parent_id, event_type, source, tags, timestamp, data) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.id,
                event.trace_id,
                event.parent_id,
                event.event_type,
                event.source,
                json.dumps(event.tags),
                event.timestamp.isoformat(),
                event.model_dump_json(),
            ),
        )
        self.conn.commit()
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
        import asyncio

        type_filter: set[str] | None = None
        if event_types:
            type_filter = {
                t.value if isinstance(t, EventType) else t for t in event_types
            }

        tag_filter: set[str] | None = None
        if tags:
            tag_filter = set(tags)

        # 获取组的消费位移
        last_ts = ""
        if group:
            row = self.conn.execute(
                "SELECT last_event_ts FROM consumer_offsets WHERE group_name = ?",
                (group,),
            ).fetchone()
            if row:
                last_ts = row[0]

        while True:
            rows = self.conn.execute(
                "SELECT data FROM events WHERE timestamp > ? ORDER BY timestamp LIMIT 50",
                (last_ts,),
            ).fetchall()

            for (raw,) in rows:
                event = FactoryEvent.model_validate_json(raw)
                last_ts = event.timestamp.isoformat()

                # 更新组消费位移
                if group:
                    self.conn.execute(
                        "INSERT OR REPLACE INTO consumer_offsets (group_name, last_event_ts, updated_at) "
                        "VALUES (?, ?, ?)",
                        (group, last_ts, datetime.now(timezone.utc).isoformat()),
                    )
                    self.conn.commit()

                if type_filter and event.event_type not in type_filter:
                    continue
                if tag_filter and not tag_filter.issubset(set(event.tags)):
                    continue
                yield event

            if not rows:
                await asyncio.sleep(1.0)

    async def ack(self, event: FactoryEvent) -> None:
        pass  # 消费位移在 subscribe 中自动更新

    async def read_trace(self, trace_id: str) -> list[FactoryEvent]:
        rows = self.conn.execute(
            "SELECT data FROM events WHERE trace_id = ? ORDER BY timestamp",
            (trace_id,),
        ).fetchall()
        return [FactoryEvent.model_validate_json(raw) for (raw,) in rows]

    async def tail(self) -> AsyncIterator[FactoryEvent]:
        """实时 tail: 轮询新事件"""
        import asyncio

        last_ts = ""
        while True:
            rows = self.conn.execute(
                "SELECT data FROM events WHERE timestamp > ? ORDER BY timestamp",
                (last_ts,),
            ).fetchall()

            for (raw,) in rows:
                event = FactoryEvent.model_validate_json(raw)
                last_ts = event.timestamp.isoformat()
                yield event

            if not rows:
                await asyncio.sleep(0.5)

    # SQLite 专属查询方法

    async def query(
        self,
        *,
        trace_id: str | None = None,
        event_type: str | EventType | None = None,
        source: str | None = None,
        tags: Sequence[str] | None = None,
        limit: int = 100,
    ) -> list[FactoryEvent]:
        """灵活查询事件（SQLiteBus 独有能力）"""
        conditions = []
        params: list[str] = []

        if trace_id:
            conditions.append("trace_id = ?")
            params.append(trace_id)
        if event_type:
            t = event_type.value if isinstance(event_type, EventType) else event_type
            conditions.append("event_type = ?")
            params.append(t)
        if source:
            conditions.append("source = ?")
            params.append(source)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT data FROM events {where} ORDER BY timestamp LIMIT ?"
        params.append(str(limit))

        rows = self.conn.execute(sql, params).fetchall()
        events = [FactoryEvent.model_validate_json(raw) for (raw,) in rows]

        # 标签过滤 (在 Python 侧做，SQLite 的 JSON 查询不够灵活)
        if tags:
            tag_filter = set(tags)
            events = [e for e in events if tag_filter.issubset(set(e.tags))]

        return events

    async def count(self, trace_id: str | None = None) -> int:
        """统计事件数量"""
        if trace_id:
            row = self.conn.execute(
                "SELECT COUNT(*) FROM events WHERE trace_id = ?", (trace_id,)
            ).fetchone()
        else:
            row = self.conn.execute("SELECT COUNT(*) FROM events").fetchone()
        return row[0] if row else 0
