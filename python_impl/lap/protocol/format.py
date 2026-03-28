"""
LAP Format — 语义类型系统

Format 是 LAP 的灵魂。它不是 JSON Schema 那种结构定义，
而是携带语义的类型——描述"流过管线的这个东西是什么"。

语义之间存在四种关系（非仅继承）：

    1. 继承 (Inheritance, A ⊂ B):
       子类型保持父类型的语义，是更具体的特化。
       例: PythonCode ⊂ Code, FeatureRequirement ⊂ Requirement
       类型兼容性: 需要 B 的地方可以传 A（协变）。

    2. 转换 (Transformation, A → B):
       有语义连续性的形态变化，由 Transformer 驱动（通常是 LLM）。
       转换是有损的——原始信息被坍缩。
       例: Requirement → Code（编程）, Code → Doc（文档化）
       注意: A 和 B 没有继承关系。Code 不是 Requirement 的子类型。

    3. 组合 (Composition, A ∪ B):
       两个独立语义域的数据合在一起，无交集，形成新的聚合。
       例: AgentState + ToolObservation 组合成新的上下文输入。

    4. 合成 (Synthesis, A ∩ B):
       两个语义域有重叠的共同部分，提取交集。
       例: 多个 Requirement 的共同约束提取为 Spec。

类型兼容性规则 (仅基于继承):
    COMPATIBLE(A, B) =
        A == B                          直连（短路）
        OR A <: B                       A 是 B 的子类型，自动向上转型
        OR EXISTS Transformer(A → B)    显式转换可用

    转换、组合、合成关系不提供自动类型兼容性——它们需要显式的
    Transformer 节点来桥接。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Format(BaseModel):
    """语义类型

    LAP 的类型原语。每个 Format 描述一种数据的语义身份，
    而非仅仅描述其结构。

    V0.2: Format 的完整身份由 (id, tags) 共同定义。
    id 是结构身份 (是什么)，tags 是语义维度 (属于什么领域/状态)。
    对人类: name 应当清晰描述类型全部含义。
    对计算机: (id, tags) 整体是唯一标识。

    示例:
        Format(id="requirement", name="Requirement",
               description="一个有状态的意图")

        Format(id="code-diff", name="CodeDiff",
               description="版本控制系统的代码变更快照",
               parent="requirement",
               tags=["source.vcs", "content.diff"])
    """

    id: str
    """类型唯一标识 (结构身份)"""

    name: str
    """人类可读名称。应当完整描述类型的语义含义。"""

    description: str
    """自然语言语义描述。
    这是框架的"语言锚定"之根——LLM 和人类都能读懂。"""

    parent: str | None = None
    """父类型 ID。None 表示根类型。
    语义继承: 子类型保持父类型的意图，但改变表达结构。"""

    json_schema: dict[str, Any] | None = None
    """可选的结构约束 (JSON Schema)。
    当存在时，可用于硬锚定（结构校验）。
    当不存在时，只有语义约束（需要软锚定）。"""

    examples: list[Any] = Field(default_factory=list)
    """示例实例。用于 LLM prompt 构建和文档。"""

    # V0.2 新增字段

    tags: list[str] = Field(default_factory=list)
    """语义标签。该类型的固有语义维度，点分层级命名。
    标签越多 = 类型越窄 = 语义越精确。
    例: ["source.p4", "domain.battle", "content.diff"]"""

    semantic_preconditions: list[str] = Field(default_factory=list)
    """语义前置条件 (人类可读)。
    成为该类型的数据必须满足的语义约束。
    指导 validator 实现者知道该检查什么。
    例: ["changelist 存在于 P4 中", "changelist 包含至少一个脚本文件"]"""

    required_tags: list[str] = Field(default_factory=list)
    """必需标签 (机器可检查)。
    输入数据必须已具备的标签——即上游 validator 必须已通过
    granted_tags 授予了这些标签。
    PipelineChecker 可在编译期验证上游是否覆盖。
    例: ["source.p4.verified", "domain.battle"]"""


class FormatRegistry:
    """Format 注册表 + 类型检查器

    管理所有已注册的 Format，提供子类型检查和兼容性判定。
    这是 LAP 的"编译器"的核心组件。
    """

    def __init__(self) -> None:
        self._formats: dict[str, Format] = {}

    def register(self, fmt: Format) -> None:
        """注册一个 Format"""
        if fmt.parent and fmt.parent not in self._formats:
            raise ValueError(
                f"Cannot register '{fmt.id}': parent '{fmt.parent}' not found. "
                f"Register parent first."
            )
        self._formats[fmt.id] = fmt

    def get(self, format_id: str) -> Format:
        """获取已注册的 Format"""
        if format_id not in self._formats:
            raise KeyError(f"Format '{format_id}' not registered")
        return self._formats[format_id]

    def is_registered(self, format_id: str) -> bool:
        return format_id in self._formats

    # 类型关系

    def ancestors(self, format_id: str) -> list[str]:
        """返回从 format_id 到根类型的继承链（不含自身）

        例: ancestors("code") → ["spec", "requirement"]
        """
        chain: list[str] = []
        current = self._formats.get(format_id)
        while current and current.parent:
            chain.append(current.parent)
            current = self._formats.get(current.parent)
        return chain

    def is_subtype(self, child: str, parent: str) -> bool:
        """判断 child 是否是 parent 的子类型

        child <: parent 意味着:
        child 可以在需要 parent 的地方使用（协变）

        例: is_subtype("code", "spec") → True
            is_subtype("agent-action", "requirement") → False (不同语义域)
        """
        if child == parent:
            return True
        return parent in self.ancestors(child)

    def compatible(self, source: str, target: str) -> bool:
        """检查 source 类型是否可以连接到 target 类型

        兼容性仅基于继承关系:
        1. 相同类型 → 直连
        2. source 是 target 的子类型 → 自动向上转型
        3. 需要 Transformer → 由调用方处理（此处返回 False）

        注意: 跨语义域（如 agent-action → requirement）不自动兼容，
        需要显式 Transformer 桥接。
        """
        return self.is_subtype(source, target)

    def check_connection(self, source: str, target: str) -> ConnectionCheck:
        """检查两个类型之间的连接性，返回详细结果"""
        if source == target:
            return ConnectionCheck(
                compatible=True,
                reason=f"直连: {source} == {target}",
            )

        if self.is_subtype(source, target):
            return ConnectionCheck(
                compatible=True,
                reason=f"子类型: {source} <: {target}",
            )

        if self.is_subtype(target, source):
            return ConnectionCheck(
                compatible=False,
                reason=(
                    f"类型不兼容: {source} 是 {target} 的父类型。"
                    f"需要 Transformer: {source} → {target}"
                ),
                needs_transformer=True,
                transformer_from=source,
                transformer_to=target,
            )

        return ConnectionCheck(
            compatible=False,
            reason=f"类型不兼容: {source} 与 {target} 无继承关系，需要 Transformer 桥接",
            needs_transformer=True,
            transformer_from=source,
            transformer_to=target,
        )

    # 内省

    def all_formats(self) -> list[Format]:
        return list(self._formats.values())

    def type_tree(self) -> dict[str, list[str]]:
        """返回类型继承树 (parent_id → [child_ids])"""
        tree: dict[str, list[str]] = {"__root__": []}
        for fmt in self._formats.values():
            parent_key = fmt.parent or "__root__"
            tree.setdefault(parent_key, []).append(fmt.id)
        return tree


class ConnectionCheck(BaseModel):
    """类型连接检查结果"""

    compatible: bool
    """是否直接兼容"""

    reason: str
    """判定原因（人类可读）"""

    needs_transformer: bool = False
    """是否需要插入 Transformer"""

    transformer_from: str | None = None
    """Transformer 源类型 (needs_transformer=True 时)"""

    transformer_to: str | None = None
    """Transformer 目标类型 (needs_transformer=True 时)"""


# 预定义 Format 层级
#
# 这是 LAP 的"标准库"——一组预定义的语义类型。
# 用户可以扩展，但这些是最常用的。
#
# 注意：类型之间有两种独立的关系维度：
#   1. 继承 (parent): PythonCode ⊂ Code（同一语义域内的特化）
#   2. 转换 (Transformer): Requirement → Code（跨语义域的形态演变）
#
# Agent 运行时类型 (agent-state, agent-action, tool-observation) 是
# 独立的语义域，不是 requirement 的子类型。它们通过 Transformer
# 与意图域连接，而非继承。

BUILTIN_FORMATS = [
    # ── 意图域 (Intent Domain) ──
    # 根类型：一个有状态的意图
    Format(
        id="requirement",
        name="Requirement",
        description="一个有状态的意图。意图域的根类型。",
    ),
    # Requirement 的直接子类型
    Format(
        id="spec",
        name="Specification",
        description="结构化的意图描述。将模糊的需求明确化为可执行的规格。",
        parent="requirement",
    ),
    Format(
        id="ticket",
        name="Ticket",
        description="工单形态的意图。来自项目管理系统（Jira、GitHub Issues 等）。",
        parent="requirement",
    ),
    Format(
        id="chat-message",
        name="ChatMessage",
        description="对话形态的意图。来自用户的自然语言输入。",
        parent="requirement",
    ),
    Format(
        id="ci-signal",
        name="CISignal",
        description="持续集成信号。构建失败、测试失败、安全告警等。",
        parent="requirement",
    ),

    # ── 方案域 (Spec Domain) ──
    # Spec 的子类型
    Format(
        id="code",
        name="Code",
        description="可执行的意图实现。源代码、脚本、配置文件。",
        parent="spec",
    ),
    Format(
        id="test-plan",
        name="TestPlan",
        description="可验证的测试策略。描述如何验证 Spec 的实现。",
        parent="spec",
    ),
    Format(
        id="doc",
        name="Document",
        description="人类可读的描述。文档、README、API 说明。",
        parent="spec",
    ),
    # Code 的子类型
    Format(
        id="binary",
        name="Binary",
        description="可运行的编译产物。编译后的二进制、Docker 镜像。",
        parent="code",
    ),
    # TestPlan 的子类型
    Format(
        id="test-result",
        name="TestResult",
        description="测试执行报告。包含通过/失败/跳过的测试结果。",
        parent="test-plan",
    ),
    # Doc 的子类型
    Format(
        id="api-doc",
        name="APIDoc",
        description="机器+人类可读的接口描述。OpenAPI Spec、GraphQL Schema。",
        parent="doc",
    ),

    # ── Agent 运行时域 (Agent Runtime Domain) ──
    # 独立根类型。与意图域通过 Transformer 连接，而非继承。
    # agent-state 不"是一种" requirement，但它"包含"一个 requirement
    # 的运行时表示。这是组合 (Composition) 关系，不是继承。
    Format(
        id="agent-runtime",
        name="AgentRuntime",
        description="Agent 运行时语义域的根类型。"
        "与意图域 (Requirement) 是独立的语义空间，"
        "通过 Transformer 桥接。",
    ),
    Format(
        id="agent-state",
        name="AgentRunState",
        description="Agent 的运行时状态。包含当前指令、历史、上下文。"
        "是 requirement + 历史观察的组合 (Composition) 产物。",
        parent="agent-runtime",
    ),
    Format(
        id="agent-action",
        name="AgentAction",
        description="Agent 的单步决策输出。tool_call / think / finish / delegate。"
        "是 LLM 对 agent-state 的转换 (Transformation) 产物。",
        parent="agent-runtime",
    ),
    Format(
        id="tool-observation",
        name="ToolObservation",
        description="工具执行后的观察结果。执行状态、输出内容。"
        "是工具对 agent-action 的转换 (Transformation) 产物。",
        parent="agent-runtime",
    ),
]


def create_builtin_registry() -> FormatRegistry:
    """创建包含所有内置 Format 的注册表"""
    registry = FormatRegistry()
    for fmt in BUILTIN_FORMATS:
        registry.register(fmt)
    return registry
