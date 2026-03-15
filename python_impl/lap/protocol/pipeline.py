"""
LAP Pipeline — 管线组合 + 类型检查器

Pipeline 是 Anchor 和 Transformer 的有向图组合。
它回答一个问题: "这些节点连起来，类型能对得上吗？"

Pipeline 的类型检查就是 LAP 的"编译器":
    - 直连: source.format_out == target.format_in → OK
    - 子类型: source.format_out <: target.format_in → 自动协变
    - 需要 Transformer: 存在 T(A→B) → 自动插入
    - 类型冲突: 无法转换 → 编译错误

示例: Agent 双锚点管线
    Pipeline(
        nodes = [Anchor_LLM, Anchor_Tool],
        edges = [LLM→Tool (on FAIL), Tool→LLM (always)],
    )
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from lap.protocol.anchor import (
    AnchorSpec,
    TransformerSpec,
    VerdictKind,
)
from lap.protocol.format import ConnectionCheck, FormatRegistry


# Pipeline 节点


class NodeKind(str, __import__("enum").Enum):
    """管线节点种类"""

    ANCHOR = "anchor"
    """锚点节点: 输入 → 判定 → 路由"""

    TRANSFORMER = "transformer"
    """转换器节点: 类型A → 类型B"""


class PipelineNode(BaseModel):
    """管线中的一个节点"""

    id: str
    """节点唯一标识"""

    kind: NodeKind
    """节点种类"""

    anchor: AnchorSpec | None = None
    """锚点规约 (kind=ANCHOR 时)"""

    transformer: TransformerSpec | None = None
    """转换器规约 (kind=TRANSFORMER 时)"""

    @property
    def format_in(self) -> str:
        """输入类型"""
        if self.kind == NodeKind.ANCHOR and self.anchor:
            return self.anchor.format_in
        if self.kind == NodeKind.TRANSFORMER and self.transformer:
            return self.transformer.from_format
        raise ValueError(f"Node '{self.id}' has no spec")

    @property
    def format_out(self) -> str:
        """输出类型"""
        if self.kind == NodeKind.ANCHOR and self.anchor:
            return self.anchor.format_out
        if self.kind == NodeKind.TRANSFORMER and self.transformer:
            return self.transformer.to_format
        raise ValueError(f"Node '{self.id}' has no spec")


# Pipeline 边


class PipelineEdge(BaseModel):
    """管线中的一条边 (节点间的连接)"""

    source: str
    """源节点 ID"""

    target: str
    """目标节点 ID"""

    condition: VerdictKind | None = None
    """触发条件 (None = 无条件/总是)。
    当源节点是 Anchor 时，按 Verdict 路由。"""

    label: str | None = None
    """人类可读的边标签 (用于可视化)"""


# Pipeline 规约


class PipelineSpec(BaseModel):
    """管线规约 — 节点和边的有向图

    PipelineSpec 是声明式的——它描述"是什么"，
    不包含执行逻辑。执行由 PipelineRunner 处理 (未来实现)。
    """

    id: str
    """管线唯一标识"""

    name: str
    """人类可读名称"""

    description: str
    """管线用途描述"""

    nodes: list[PipelineNode]
    """所有节点"""

    edges: list[PipelineEdge]
    """所有边"""

    entry: str
    """入口节点 ID"""

    group: str | None = None
    """管线所属组。同组管线共享事件空间，组外消费者不消费。
    例: "igame-benchmark"。"""

    tags: list[str] = Field(default_factory=list)
    """管线的语义标签。发射的事件会自动继承这些标签。
    例: ["igame.benchmark.battle", "unity.lua"]"""


# 类型检查结果


class EdgeCheckResult(BaseModel):
    """单条边的类型检查结果"""

    edge: PipelineEdge
    """被检查的边"""

    source_format_out: str
    """源节点的输出类型"""

    target_format_in: str
    """目标节点的输入类型"""

    connection: ConnectionCheck
    """类型连接检查详情"""


class PipelineCheckResult(BaseModel):
    """整个管线的类型检查结果"""

    pipeline_id: str
    """被检查的管线 ID"""

    valid: bool
    """管线是否类型安全"""

    edge_results: list[EdgeCheckResult]
    """每条边的检查结果"""

    errors: list[str]
    """结构性错误 (缺失节点、缺失入口等)"""

    warnings: list[str] = Field(default_factory=list)
    """警告 (孤立节点、未使用的路由等)"""

    @property
    def type_errors(self) -> list[EdgeCheckResult]:
        """所有类型不兼容的边"""
        return [r for r in self.edge_results if not r.connection.compatible]

    @property
    def needs_transformers(self) -> list[EdgeCheckResult]:
        """需要插入 Transformer 的边"""
        return [r for r in self.edge_results if r.connection.needs_transformer]


# Pipeline 类型检查器 (编译器)


class PipelineChecker:
    """管线类型检查器 — LAP 的"编译器"

    验证管线中所有边的类型安全性。

    使用方式:
        registry = create_builtin_registry()
        checker = PipelineChecker(registry)
        result = checker.check(pipeline_spec)
        if not result.valid:
            for err in result.type_errors:
                print(f"类型冲突: {err.source_format_out} → {err.target_format_in}")
    """

    def __init__(self, registry: FormatRegistry):
        self.registry = registry

    def check(self, pipeline: PipelineSpec) -> PipelineCheckResult:
        """执行完整的管线类型检查"""
        errors: list[str] = []
        warnings: list[str] = []
        edge_results: list[EdgeCheckResult] = []

        # ── 构建节点索引 ──
        node_map: dict[str, PipelineNode] = {}
        for node in pipeline.nodes:
            if node.id in node_map:
                errors.append(f"重复的节点 ID: '{node.id}'")
            node_map[node.id] = node

        # ── 检查入口 ──
        if pipeline.entry not in node_map:
            errors.append(
                f"入口节点 '{pipeline.entry}' 不存在于节点列表中"
            )

        # ── 检查每条边的类型安全性 ──
        referenced_nodes: set[str] = {pipeline.entry}

        for edge in pipeline.edges:
            referenced_nodes.add(edge.source)
            referenced_nodes.add(edge.target)

            # 检查节点存在性
            if edge.source not in node_map:
                errors.append(
                    f"边引用了不存在的源节点: '{edge.source}'"
                )
                continue
            if edge.target not in node_map:
                errors.append(
                    f"边引用了不存在的目标节点: '{edge.target}'"
                )
                continue

            source_node = node_map[edge.source]
            target_node = node_map[edge.target]

            # 获取输出/输入类型
            try:
                source_out = source_node.format_out
                target_in = target_node.format_in
            except ValueError as e:
                errors.append(str(e))
                continue

            # 检查 Format 是否已注册
            if not self.registry.is_registered(source_out):
                errors.append(
                    f"节点 '{edge.source}' 的输出类型 '{source_out}' 未注册"
                )
                continue
            if not self.registry.is_registered(target_in):
                errors.append(
                    f"节点 '{edge.target}' 的输入类型 '{target_in}' 未注册"
                )
                continue

            # 类型检查
            connection = self.registry.check_connection(source_out, target_in)
            edge_results.append(
                EdgeCheckResult(
                    edge=edge,
                    source_format_out=source_out,
                    target_format_in=target_in,
                    connection=connection,
                )
            )

        # ── 检查孤立节点 ──
        for node_id in node_map:
            if node_id not in referenced_nodes:
                warnings.append(f"孤立节点: '{node_id}' 未被任何边引用")

        # ── 汇总 ──
        all_edges_ok = all(r.connection.compatible for r in edge_results)
        valid = len(errors) == 0 and all_edges_ok

        return PipelineCheckResult(
            pipeline_id=pipeline.id,
            valid=valid,
            edge_results=edge_results,
            errors=errors,
            warnings=warnings,
        )


# 便捷构建器


def describe_agent_loop() -> PipelineSpec:
    """用 LAP 类型库描述 Agent 双锚点循环 (自举验证)。

    数据流: Anchor_LLM --(FAIL)--> Anchor_Tool --> obs_to_state --> Anchor_LLM
    出口:   Anchor_LLM --(PASS)--> EMIT (finish/reject)

    obs_to_state 是显式 Transformer: tool-observation -> agent-state,
    对应 controller.py 中手写的 state.history.append() 操作。
    """
    from lap.protocol.anchor import (
        AnchorSpec,
        Route,
        RouteAction,
        TransformerSpec,
        TransformMethod,
        ValidatorKind,
        ValidatorSpec,
    )

    anchor_llm = PipelineNode(
        id="anchor_llm",
        kind=NodeKind.ANCHOR,
        anchor=AnchorSpec(
            id="anchor_llm",
            name="LLM 决策锚点",
            format_in="agent-state",
            format_out="agent-action",
            validator=ValidatorSpec(
                id="llm-self",
                kind=ValidatorKind.SOFT,
                description="LLM 自身作为判定器: 接收状态, 产出 Action",
            ),
            routes={
                VerdictKind.PASS: Route(
                    action=RouteAction.EMIT,
                    feedback="Agent 决定结束 (finish/reject)",
                ),
                VerdictKind.PARTIAL: Route(
                    action=RouteAction.RETRY,
                    feedback="Agent 在思考, 不产生副作用, 继续循环",
                ),
                VerdictKind.FAIL: Route(
                    action=RouteAction.NEXT,
                    target="anchor_tool",
                    feedback="Agent 需要工具执行, 需要外部硬锚定",
                ),
            },
        ),
    )

    anchor_tool = PipelineNode(
        id="anchor_tool",
        kind=NodeKind.ANCHOR,
        anchor=AnchorSpec(
            id="anchor_tool",
            name="工具执行锚点",
            format_in="agent-action",
            format_out="tool-observation",
            validator=ValidatorSpec(
                id="tool-executor",
                kind=ValidatorKind.HARD,
                description="工具执行器: schema 校验 + 执行, 确定性判定",
            ),
            routes={
                VerdictKind.PASS: Route(
                    action=RouteAction.NEXT,
                    target="obs_to_state",
                    feedback="工具执行成功, 带观察结果进入状态合并",
                ),
                VerdictKind.FAIL: Route(
                    action=RouteAction.NEXT,
                    target="obs_to_state",
                    feedback="工具执行失败, 带错误诊断进入状态合并",
                ),
            },
        ),
    )

    obs_to_state = PipelineNode(
        id="obs_to_state",
        kind=NodeKind.TRANSFORMER,
        transformer=TransformerSpec(
            id="obs-to-state",
            name="观察结果 → Agent 状态",
            from_format="tool-observation",
            to_format="agent-state",
            method=TransformMethod.RULE,
            description=(
                "将工具观察结果合并进 Agent 运行状态。"
                "具体操作: state.last_observation = obs, "
                "state.history.append({action, obs})。"
                "确定性规则转换, 不需要 LLM。"
            ),
        ),
    )

    return PipelineSpec(
        id="agent-loop",
        name="Agent 双锚点循环",
        description=(
            "Agent 的 step 循环 = 两个 Anchor + 一个 Transformer 的 Pipeline。"
            "Anchor_LLM (软锚定) 做决策, Anchor_Tool (硬锚定) 做执行, "
            "obs_to_state (Transformer) 做类型转换。"
            "这是 LAP 的最小自治单元——双锚点。"
        ),
        nodes=[anchor_llm, anchor_tool, obs_to_state],
        edges=[
            PipelineEdge(
                source="anchor_llm",
                target="anchor_tool",
                condition=VerdictKind.FAIL,
                label="需要工具 (tool_call)",
            ),
            PipelineEdge(
                source="anchor_tool",
                target="obs_to_state",
                condition=None,
                label="工具执行完毕, 进入类型转换",
            ),
            PipelineEdge(
                source="obs_to_state",
                target="anchor_llm",
                condition=None,
                label="状态合并完成, 回到 LLM 决策",
            ),
        ],
        entry="anchor_llm",
    )
