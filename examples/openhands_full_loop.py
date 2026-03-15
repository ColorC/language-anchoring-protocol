"""
LAP Example: OpenHands CodeAct Agent Loop (Full Version with Context Management)

This example demonstrates how LAP elegantly handles traditional "engineering problems"
(like Context Window Overflow or State Management) by turning them into pure
Semantic Typing and Routing problems.

Instead of writing a complex `while` loop with hardcoded token counting and truncation,
we define semantic `Formats` (e.g., `agent-state` vs `agent-state-compressed`) and
use `Anchors` to enforce them.
"""

from omnifactory.protocol.anchor import (
    AnchorSpec, Route, RouteAction, TransformerSpec, TransformMethod, ValidatorKind, ValidatorSpec, VerdictKind
)
from omnifactory.protocol.pipeline import NodeKind, PipelineEdge, PipelineNode, PipelineSpec

def build_full_codeact_pipeline() -> PipelineSpec:
    """
    Defines a robust Agent Loop with Context Compression.
    
    1. Context Builder: tool-observation -> raw-agent-state
    2. Context Validator (Hard): raw-agent-state -> [PASS] agent-state | [FAIL] raw-agent-state (needs compression)
    3. Context Compressor (Transformer): raw-agent-state -> agent-state
    4. LLM (Soft): agent-state -> agent-action
    5. Tool (Hard): agent-action -> tool-observation
    """

    # 1. Context Builder
    # Simply appends the new observation to the history. Output format is unverified.
    builder_node = PipelineNode(
        id="context-builder",
        kind=NodeKind.TRANSFORMER,
        transformer=TransformerSpec(
            id="history-appender",
            name="History Appender",
            from_format="tool-observation",
            to_format="raw-agent-state",
            method=TransformMethod.RULE,
            description="Appends the new observation or user input to the message history.",
        ),
    )

    # 2. Context Validator (The "Context Window Guard")
    # This replaces hardcoded IF statements. It strictly validates if the state fits the LLM.
    validator_node = PipelineNode(
        id="context-validator",
        kind=NodeKind.ANCHOR,
        anchor=AnchorSpec(
            id="length-checker",
            name="Context Window Guard",
            format_in="raw-agent-state",
            format_out="agent-state",
            validator=ValidatorSpec(
                id="token-counter",
                kind=ValidatorKind.HARD,
                description="Checks if total token count is under the LLM's context limit (e.g. 100k).",
            ),
            routes={
                # PASS: Semantic tag 'LLM-processable' granted. Proceed to LLM.
                VerdictKind.PASS: Route(action=RouteAction.NEXT, target="llm"),
                # FAIL: Too long! Route to the compressor to fix the semantic type.
                VerdictKind.FAIL: Route(action=RouteAction.NEXT, target="context-compressor"),
            },
        ),
    )

    # 3. Context Compressor
    # Only triggered if the validator FAILs. Transforms raw state into compressed state.
    compressor_node = PipelineNode(
        id="context-compressor",
        kind=NodeKind.TRANSFORMER,
        transformer=TransformerSpec(
            id="history-summarizer",
            name="History Summarizer",
            from_format="raw-agent-state",
            to_format="agent-state",
            method=TransformMethod.LLM,
            description="Summarizes older messages to reduce token count while preserving core semantics.",
        ),
    )

    # 4. LLM Node
    llm_node = PipelineNode(
        id="llm",
        kind=NodeKind.ANCHOR,
        anchor=AnchorSpec(
            id="llm-router",
            name="LLM Semantic Decider",
            format_in="agent-state",
            format_out="agent-action",
            validator=ValidatorSpec(
                id="llm-caller",
                kind=ValidatorKind.SOFT,
                description="Call LLM to decide the next action.",
            ),
            routes={
                VerdictKind.PASS: Route(action=RouteAction.EMIT),
                VerdictKind.FAIL: Route(action=RouteAction.NEXT, target="tool"),
            },
        ),
    )

    # 5. Tool Node
    # Crucially, any missing semantic constraints (like a Dirty Git Commit) would be caught here
    # or by an upstream Ground Truth Anchor, turning state inconsistency into a simple Verdict routing issue.
    tool_node = PipelineNode(
        id="tool",
        kind=NodeKind.ANCHOR,
        anchor=AnchorSpec(
            id="tool-router",
            name="Tool Execution Validator",
            format_in="agent-action",
            format_out="tool-observation",
            validator=ValidatorSpec(
                id="tool-executor",
                kind=ValidatorKind.HARD,
                description="Execute tool and return output/diagnosis.",
            ),
            routes={
                # Both success and failure route back to the start of the loop
                VerdictKind.PASS: Route(action=RouteAction.NEXT, target="context-builder"),
                VerdictKind.FAIL: Route(action=RouteAction.NEXT, target="context-builder"),
            },
        ),
    )

    return PipelineSpec(
        id="codeact-full-loop",
        name="LAP CodeAct Full Agent Loop",
        nodes=[builder_node, validator_node, compressor_node, llm_node, tool_node],
        edges=[
            PipelineEdge(source="context-builder", target="context-validator"),
            PipelineEdge(source="context-validator", target="llm", condition=VerdictKind.PASS),
            PipelineEdge(source="context-validator", target="context-compressor", condition=VerdictKind.FAIL),
            PipelineEdge(source="context-compressor", target="llm"),
            PipelineEdge(source="llm", target="tool", condition=VerdictKind.FAIL),
            PipelineEdge(source="tool", target="context-builder"),
        ],
        entry="context-builder",
    )
