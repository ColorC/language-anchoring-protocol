"""PipelineRunner — PipelineSpec + EventBus 驱动的通用执行器

读入 PipelineSpec + Router 绑定，从 entry 节点开始，
按路由表自动循环，每一步都通过 EventBus 发射事件。
"""

from __future__ import annotations

import inspect
import time
from typing import Any

from ulid import ULID

from lap.bus.base import EventBus
from lap.protocol.anchor import RouteAction, VerdictKind
from lap.protocol.events import EventMetadata, FactoryEvent
from lap.protocol.pipeline import PipelineNode, PipelineSpec
from lap.protocol.registry import EventType
from lap.runtime.router import Router
from lap.runtime.stuck import StuckDetector


class PipelineRunner:
    """PipelineSpec + EventBus 驱动的执行器

    每一步 Router.run() 都发射事件到总线，
    完整的执行过程可通过 trace_id 回溯。
    集成 StuckDetector 检测循环。
    """

    def __init__(
        self,
        pipeline: PipelineSpec,
        bindings: dict[str, Router],
        bus: EventBus,
        *,
        max_steps: int = 50,
        source: str = "pipeline",
        stuck_threshold: int = 3,
    ):
        self.pipeline = pipeline
        self.bindings = bindings
        self.bus = bus
        self.max_steps = max_steps
        self.source = source
        self.stuck_detector = StuckDetector(repeat_threshold=stuck_threshold)

        self._nodes: dict[str, PipelineNode] = {n.id: n for n in pipeline.nodes}
        self._edges: dict[tuple[str, VerdictKind | None], str] = {}
        for edge in pipeline.edges:
            self._edges[(edge.source, edge.condition)] = edge.target

    def _resolve_next(self, node_id: str, verdict_kind: VerdictKind) -> str | None:
        target = self._edges.get((node_id, verdict_kind))
        if target:
            return target
        return self._edges.get((node_id, None))

    async def _emit(
        self,
        trace_id: str,
        event_type: EventType,
        payload: dict[str, Any],
        parent_id: str | None = None,
        metadata: EventMetadata | None = None,
    ) -> FactoryEvent:
        event = FactoryEvent(
            trace_id=trace_id,
            parent_id=parent_id,
            event_type=event_type.value,
            source=self.source,
            payload=payload,
            tags=list(self.pipeline.tags),
            metadata=metadata,
        )
        await self.bus.publish(event)
        return event

    async def run(self, initial_input: Any) -> Any:
        """执行管线，全程发射事件"""
        trace_id = str(ULID())
        current_node_id = self.pipeline.entry
        current_input = initial_input

        intent_event = await self._emit(
            trace_id, EventType.TASK_INTENT,
            payload={"pipeline": self.pipeline.id, "entry": self.pipeline.entry},
        )

        for step in range(self.max_steps):
            node = self._nodes[current_node_id]
            router = self.bindings[current_node_id]

            # 发射节点进入事件
            is_hard = node.anchor and node.anchor.validator.kind.value == "hard"
            is_soft = node.anchor and node.anchor.validator.kind.value == "soft"

            if is_hard:
                enter_type = EventType.TOOL_CALL
            elif is_soft:
                enter_type = EventType.LLM_REQUEST
            else:
                enter_type = EventType.STATE_CHANGE

            node_event = await self._emit(
                trace_id, enter_type,
                payload={"step": step, "node": current_node_id},
                parent_id=intent_event.id,
            )

            t0 = time.monotonic()
            verdict = router.run(current_input)
            # 支持 async Router: 如果 run() 返回 coroutine，await 它
            if inspect.isawaitable(verdict):
                verdict = await verdict
            duration_ms = (time.monotonic() - t0) * 1000

            # 发射节点结果事件
            result_payload: dict[str, Any] = {
                "step": step,
                "node": current_node_id,
                "verdict": verdict.kind.value,
            }
            if verdict.diagnosis:
                result_payload["diagnosis"] = verdict.diagnosis

            if is_hard:
                exit_type = EventType.TOOL_RESULT
                meta = EventMetadata(duration_ms=duration_ms, tool_name=current_node_id)
            elif is_soft:
                exit_type = EventType.LLM_RESPONSE
                meta = EventMetadata(latency_ms=duration_ms)
            else:
                exit_type = EventType.STATE_CHANGE
                meta = EventMetadata(duration_ms=duration_ms)

            await self._emit(
                trace_id, exit_type,
                payload=result_payload,
                parent_id=node_event.id,
                metadata=meta,
            )

            # StuckDetector: 记录 LLM/Tool 步骤
            if is_soft:
                # LLM step: 记录 tool_calls 或 text_output
                output = verdict.output
                if verdict.kind == VerdictKind.FAIL and isinstance(output, dict):
                    self.stuck_detector.record({
                        "tool_calls": output.get("tool_calls"),
                        "text_output": output.get("text"),
                    })
                elif verdict.kind == VerdictKind.PASS:
                    self.stuck_detector.record({
                        "tool_calls": None,
                        "text_output": str(output)[:200] if output else "",
                    })
            elif is_hard:
                # Tool step: 补充 tool_results 到最后一条记录
                output = verdict.output
                if isinstance(output, dict) and self.stuck_detector._history:
                    self.stuck_detector._history[-1]["tool_results"] = output.get("tool_results")

                # 检查是否 stuck
                if self.stuck_detector.is_stuck():
                    analysis = self.stuck_detector.stuck_analysis
                    error_msg = f"Agent stuck in loop: {analysis.loop_type} ({analysis.repeat_times}x)"
                    await self._emit(
                        trace_id, EventType.TASK_ERROR,
                        payload={"error": error_msg, "node": current_node_id},
                        parent_id=intent_event.id,
                    )
                    raise RuntimeError(error_msg)

            # 路由
            anchor = node.anchor
            if anchor and verdict.kind in anchor.routes:
                route = anchor.routes[verdict.kind]

                if route.action == RouteAction.EMIT:
                    await self._emit(
                        trace_id, EventType.TASK_FINISH,
                        payload={"step": step, "node": current_node_id},
                        parent_id=intent_event.id,
                    )
                    return verdict.output

                if route.action == RouteAction.HALT:
                    await self._emit(
                        trace_id, EventType.TASK_ERROR,
                        payload={"error": verdict.diagnosis or "halted", "node": current_node_id},
                        parent_id=intent_event.id,
                    )
                    raise RuntimeError(
                        f"Pipeline halted at '{current_node_id}': {verdict.diagnosis}"
                    )

                if route.action == RouteAction.RETRY:
                    continue

                if route.action in (RouteAction.NEXT, RouteAction.JUMP):
                    target = route.target or self._resolve_next(current_node_id, verdict.kind)
                    if not target:
                        raise RuntimeError(f"No target for route at '{current_node_id}'")
                    current_node_id = target
                    current_input = verdict.output
                    continue

            # Transformer 节点
            next_node = self._resolve_next(current_node_id, verdict.kind)
            if next_node:
                current_node_id = next_node
                current_input = verdict.output
                continue

            raise RuntimeError(
                f"Cannot route from '{current_node_id}' with verdict {verdict.kind.value}"
            )

        await self._emit(
            trace_id, EventType.TASK_ERROR,
            payload={"error": f"max_steps ({self.max_steps}) exceeded"},
            parent_id=intent_event.id,
        )
        raise RuntimeError(f"Pipeline exceeded max_steps ({self.max_steps})")
