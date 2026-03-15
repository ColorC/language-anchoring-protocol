# LAP — Language Anchoring Protocol
#
# 事件层
from lap.protocol.events import EventMetadata, FactoryEvent
from lap.protocol.registry import EventType

# 语义类型层
from lap.protocol.format import (
    ConnectionCheck,
    Format,
    FormatRegistry,
    create_builtin_registry,
)

# 锚定原语层
from lap.protocol.anchor import (
    AnchorSpec,
    Route,
    RouteAction,
    Transformer,
    TransformerSpec,
    TransformMethod,
    Validator,
    ValidatorKind,
    ValidatorSpec,
    Verdict,
    VerdictKind,
)

# 管线组合层
from lap.protocol.pipeline import (
    EdgeCheckResult,
    NodeKind,
    PipelineChecker,
    PipelineCheckResult,
    PipelineEdge,
    PipelineNode,
    PipelineSpec,
    describe_agent_loop,
)

__all__ = [
    # 事件
    "FactoryEvent",
    "EventMetadata",
    "EventType",
    # 语义类型
    "Format",
    "FormatRegistry",
    "ConnectionCheck",
    "create_builtin_registry",
    # 锚定原语
    "Verdict",
    "VerdictKind",
    "Route",
    "RouteAction",
    "ValidatorSpec",
    "ValidatorKind",
    "Validator",
    "AnchorSpec",
    "TransformerSpec",
    "TransformMethod",
    "Transformer",
    # 管线组合
    "PipelineSpec",
    "PipelineNode",
    "PipelineEdge",
    "NodeKind",
    "PipelineChecker",
    "PipelineCheckResult",
    "EdgeCheckResult",
    "describe_agent_loop",
]
