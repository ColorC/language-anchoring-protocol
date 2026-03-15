"""
LAP 锚定原语 — Verdict, Route, Validator, Anchor, Transformer

这些是 LAP 的机制层原语。Format 是语义层（定义"是什么"），
这里的原语定义"怎么判定"和"往哪走"。

原语关系:
    Validator → Verdict → Route
    Anchor = Format_in + Validator + Routes → Format_out
    Transformer = Format_A → Format_B (LLM 驱动的类型转换)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# Verdict: 判定结果


class VerdictKind(str, Enum):
    """判定结果的种类"""

    PASS = "pass"
    """锚定成功：输出满足约束"""

    FAIL = "fail"
    """锚定失败：输出不满足约束，附带诊断信息用于反馈"""

    PARTIAL = "partial"
    """部分通过：可以继续但不完整（think 中间态等）"""


class Verdict(BaseModel):
    """判定结果

    Validator 的输出。不只是 bool——它携带诊断信息，
    这些诊断信息会被路由回 LLM 作为反馈。

    V0.2: 新增 confidence (语义置信度) 和 granted_tags (授予标签)。
    confidence 量化软锚定的语义匹配确信度。
    granted_tags 声明本次验证确认了哪些语义维度，在管线中累积。

    示例:
        Verdict(kind=PASS, output={"compiled": True}, confidence=1.0)
        Verdict(kind=FAIL, diagnosis="Line 42: undefined variable 'x'")
        Verdict(kind=PASS, output=data, confidence=0.9,
                granted_tags=["source.verified", "domain.frontend"])
    """

    kind: VerdictKind
    """判定种类"""

    output: Any = None
    """判定产物（PASS 时的产物，或 FAIL 时的原始输入）"""

    diagnosis: str | None = None
    """失败诊断。反馈回路的关键——路由回 LLM 使其自我修正。"""

    details: dict[str, Any] = Field(default_factory=dict)
    """结构化判定细节（错误行号、失败的测试名等）"""

    # V0.2 新增字段

    confidence: float | None = None
    """语义匹配确信度 (0.0 ~ 1.0)。
    硬锚定器总是 1.0。软锚定器反映语义距离。
    None 表示未评估 (向后兼容 V0.1 行为)。"""

    granted_tags: list[str] = Field(default_factory=list)
    """本次判定授予的语义标签。
    声明 validator 确认了哪些语义维度。
    在管线中只增不减地累积——经过的 validator 越多，
    数据携带的已验证语义维度越多。
    例: ["source.p4.verified", "domain.battle"]"""


# Route: 路由指令


class RouteAction(str, Enum):
    """路由动作"""

    NEXT = "next"
    """前进到管线中的下一个节点"""

    RETRY = "retry"
    """重试当前锚点（带诊断反馈）"""

    JUMP = "jump"
    """跳转到指定锚点 (target 必填)"""

    EMIT = "emit"
    """输出最终产物，退出管线"""

    HALT = "halt"
    """停止管线（不可恢复错误）"""


class Route(BaseModel):
    """路由指令

    Verdict 出来后，查路由表决定下一步。
    """

    action: RouteAction
    """路由动作"""

    target: str | None = None
    """目标节点 ID（JUMP 时必填，NEXT 时可选以覆盖默认顺序）"""

    feedback: str | None = None
    """携带给目标节点的反馈信息"""

    max_retries: int = 3
    """最大重试次数（仅 RETRY 时生效）"""


# Validator: 判定器


class ValidatorKind(str, Enum):
    """判定器的性质"""

    HARD = "hard"
    """硬锚定器：确定性判定，可证明。
    编译器、JSON Schema、测试套件。同一输入永远同一结果。"""

    SOFT = "soft"
    """软锚定器：概率性判定，不可证明。
    LLM-as-judge、人工审查。同一输入可能不同结果。"""


class ValidatorSpec(BaseModel):
    """判定器规约（声明）

    描述判定器"是什么"，不包含"怎么做"。
    具体实现由运行时绑定。
    """

    id: str
    """判定器唯一标识"""

    kind: ValidatorKind
    """硬/软"""

    description: str
    """自然语言描述（语言锚定之根——LLM 和人类都能读懂）"""


class Validator(ABC):
    """判定器运行时接口（实现）

    ValidatorSpec 是声明，Validator 是实现。
    同一个 ValidatorSpec 可以有多种实现（mock、真实、远程等）。
    """

    def __init__(self, spec: ValidatorSpec):
        self.spec = spec

    @abstractmethod
    async def validate(self, input_data: Any) -> Verdict:
        """执行判定"""
        ...


# Anchor: 锚点


class AnchorSpec(BaseModel):
    """锚点规约 — LAP 的原子执行单位

    Anchor 是一个带类型签名的函数:
        format_in → Validator → format_out

    它回答三个问题:
    1. 输入是什么类型？ (format_in)
    2. 怎么判定？ (validator)
    3. 输出是什么类型？ (format_out)
    4. 判定后往哪走？ (routes)
    """

    id: str
    """锚点唯一标识"""

    name: str
    """人类可读名称"""

    format_in: str
    """输入类型 (Format ID)"""

    format_out: str
    """输出类型 (Format ID)"""

    validator: ValidatorSpec
    """判定器规约"""

    routes: dict[VerdictKind, Route]
    """路由表: Verdict → Route"""


# Transformer: 类型转换器


class TransformMethod(str, Enum):
    """转换方式"""

    LLM = "llm"
    """由 LLM 驱动的概率性转换（本质上是软锚定）"""

    RULE = "rule"
    """由确定性规则驱动的转换（解析、映射、提取）"""

    HYBRID = "hybrid"
    """混合: 部分确定性 + 部分 LLM"""


class TransformerSpec(BaseModel):
    """类型转换器规约

    当两个节点的 format_out 和 format_in 不直接兼容
    但存在语义继承关系时，需要 Transformer 做类型转换。

    Transformer 本身也是一种 Anchor——有输入、有判定、有输出。
    区别在于它的核心职责是"转换类型"而非"验证正确性"。

    示例:
        TransformerSpec(
            id="chat-to-spec",
            from_format="chat-message",
            to_format="spec",
            method=TransformMethod.LLM,
            description="将用户的自然语言输入转换为结构化需求规格"
        )

    深刻洞察:
        传统软件工程中的"编程"在 LAP 框架下就是一个 Transformer:
        Spec → Code。"写文档"是 Code → Doc。"设计测试"是 Spec → TestPlan。
    """

    id: str
    """转换器唯一标识"""

    name: str
    """人类可读名称"""

    from_format: str
    """源类型 (Format ID)"""

    to_format: str
    """目标类型 (Format ID)"""

    method: TransformMethod
    """转换方式"""

    description: str
    """自然语言描述转换逻辑"""


class Transformer(ABC):
    """Transformer 运行时接口"""

    def __init__(self, spec: TransformerSpec):
        self.spec = spec

    @abstractmethod
    async def transform(self, input_data: Any) -> Verdict:
        """执行类型转换

        Returns:
            Verdict: PASS + 转换后的产物, 或 FAIL + 诊断
        """
        ...
