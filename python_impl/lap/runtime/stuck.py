"""StuckDetector — 检测 Agent 陷入循环

从 OpenHands stuck.py 简化。检测三种模式:
1. 重复 action-observation: 连续 N 次相同命令 + 相同结果
2. 重复错误: 连续 N 次相同命令 + 错误
3. 独白循环: 连续 N 次相同纯文本响应 (无 tool_call)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class StuckAnalysis:
    """stuck 分析结果"""
    loop_type: str
    repeat_times: int


class StuckDetector:
    """检测 Agent 循环

    维护最近 N 步的 action-observation 历史,
    检测是否陷入重复模式。
    """

    def __init__(self, max_history: int = 12, repeat_threshold: int = 3):
        self.max_history = max_history
        self.repeat_threshold = repeat_threshold
        self._history: list[dict[str, Any]] = []
        self.stuck_analysis: StuckAnalysis | None = None

    def record(self, step_data: dict[str, Any]) -> None:
        """记录一步的 action-observation 数据

        step_data 应包含:
            tool_calls: list[dict] — 本轮工具调用 (或 None 表示纯文本)
            tool_results: list[dict] — 本轮工具结果 (或 None)
            text_output: str | None — 纯文本输出
        """
        self._history.append(step_data)
        if len(self._history) > self.max_history:
            self._history.pop(0)

    def is_stuck(self) -> bool:
        """检测是否陷入循环"""
        self.stuck_analysis = None

        if len(self._history) < self.repeat_threshold:
            return False

        # 场景 1: 重复 action-observation
        if self._check_repeating_action_observation():
            return True

        # 场景 2: 独白循环
        if self._check_monologue():
            return True

        # 场景 3: 交替模式 (A-B-A-B)
        if self._check_alternating_pattern():
            return True

        return False

    def _normalize_step(self, step: dict[str, Any]) -> str:
        """将一步归一化为可比较的字符串"""
        tool_calls = step.get("tool_calls")
        if tool_calls:
            # 用 tool_name + 部分 args 作为指纹
            parts = []
            for tc in tool_calls:
                name = tc.get("tool_name", "")
                args = tc.get("tool_args", {})
                parts.append(f"{name}:{_hash_args(args)}")
            return "|".join(parts)
        else:
            # 纯文本: 用前 200 字符作为指纹
            text = step.get("text_output", "")
            return f"text:{text[:200]}"

    def _normalize_result(self, step: dict[str, Any]) -> str:
        """将工具结果归一化"""
        results = step.get("tool_results")
        if results:
            return "|".join(r.get("content", "")[:200] for r in results)
        return ""

    def _check_repeating_action_observation(self) -> bool:
        """检测连续 N 次相同的 action + observation"""
        n = self.repeat_threshold
        if len(self._history) < n:
            return False

        recent = self._history[-n:]
        actions = [self._normalize_step(s) for s in recent]
        results = [self._normalize_result(s) for s in recent]

        if len(set(actions)) == 1 and len(set(results)) == 1:
            self.stuck_analysis = StuckAnalysis(
                loop_type="repeating_action_observation",
                repeat_times=n,
            )
            return True
        return False

    def _check_monologue(self) -> bool:
        """检测连续 N 次相同纯文本响应"""
        n = self.repeat_threshold
        recent_text_steps = [
            s for s in self._history[-n * 2:]
            if not s.get("tool_calls")
        ]

        if len(recent_text_steps) < n:
            return False

        last_n = recent_text_steps[-n:]
        fingerprints = [self._normalize_step(s) for s in last_n]
        if len(set(fingerprints)) == 1:
            self.stuck_analysis = StuckAnalysis(
                loop_type="monologue",
                repeat_times=n,
            )
            return True
        return False

    def _check_alternating_pattern(self) -> bool:
        """检测 A-B-A-B 交替模式 (需要 6 步)"""
        if len(self._history) < 6:
            return False

        last_6 = self._history[-6:]
        actions = [self._normalize_step(s) for s in last_6]

        # A-B-A-B-A-B pattern: even indices same, odd indices same
        evens_same = all(actions[i] == actions[0] for i in range(0, 6, 2))
        odds_same = all(actions[i] == actions[1] for i in range(1, 6, 2))

        if evens_same and odds_same and actions[0] != actions[1]:
            self.stuck_analysis = StuckAnalysis(
                loop_type="alternating_pattern",
                repeat_times=3,
            )
            return True
        return False


def _hash_args(args: dict[str, Any]) -> str:
    """简单的参数哈希，用于比较"""
    parts = []
    for k, v in sorted(args.items()):
        v_str = str(v)[:100]
        parts.append(f"{k}={v_str}")
    return ",".join(parts)
