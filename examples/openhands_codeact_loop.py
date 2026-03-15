"""
LAP Example: Minimal OpenHands CodeAct Agent Loop

This is a conceptual demonstration of how a familiar agent architecture
(like the one used in OpenHands) can be elegantly defined using LAP's primitives
(Anchors, Transformers, and Verdicts) and executed on an Event Bus.

By explicitly separating the semantic contract (Pipeline/Anchors) from the
implementation (Routers), the entire agent loop becomes type-safe,
infinitely extensible, and natively observable.
"""

from omnifactory.protocol.anchor import (
    AnchorSpec, Route, RouteAction, TransformerSpec, TransformMethod, ValidatorKind, ValidatorSpec, VerdictKind
)
from omnifactory.protocol.pipeline import NodeKind, PipelineEdge, PipelineNode, PipelineSpec

def build_codeact_pipeline() -> PipelineSpec:
    """
    Defines the standard ReAct/CodeAct Agent Loop as a LAP Pipeline.
    
    1. Context (Transformer): tool-observation -> agent-state
    2. LLM (Soft Anchor): agent-state -> agent-action
    3. Tool (Hard Anchor): agent-action -> tool-observation
    """

    # Node 1: Context Transformer
    # Transforms the raw observations and user input into a format the LLM can understand (e.g. Chat History)
    context_node = PipelineNode(
        id="context",
        kind=NodeKind.TRANSFORMER,
        transformer=TransformerSpec(
            id="context-router",
            name="Context Builder",
            from_format="tool-observation",
            to_format="agent-state",
            method=TransformMethod.RULE,
        ),
    )

    # Node 2: LLM Anchor (Soft Validation)
    # The LLM reads the state and decides the next action.
    # It outputs a Verdict. If it decides to call a tool, it fails the soft validation (FAIL),
    # meaning the pipeline needs to route to a Hard Anchor to verify and execute the tool.
    llm_node = PipelineNode(
        id="llm",
        kind=NodeKind.ANCHOR,
        anchor=AnchorSpec(
            id="llm-router",
            name="LLM Semantic Decider",
            format_in="agent-state",
            format_out="agent-action",
            validator=ValidatorSpec(
                id="llm",
                kind=ValidatorKind.SOFT,
                description="Call LLM to get the next action (tool_call or finish text).",
            ),
            routes={
                # PASS: Output is raw text/finish. Emit and exit pipeline.
                VerdictKind.PASS: Route(action=RouteAction.EMIT),
                # FAIL: Output contains tool calls. Route to Tool Anchor.
                VerdictKind.FAIL: Route(action=RouteAction.NEXT, target="tool"),
            },
        ),
    )

    # Node 3: Tool Anchor (Hard Validation)
    # Verifies the tool call syntax and executes the tool (e.g. bash, editor).
    # Crucially, both PASS (success) and FAIL (error) route back to the Context node,
    # because the LLM needs to see the result (whether output or error stack trace) to proceed.
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
                description="Execute the requested tool and return the output or stderr.",
            ),
            routes={
                # PASS: Tool executed successfully. Route observation back to Context.
                VerdictKind.PASS: Route(action=RouteAction.NEXT, target="context"),
                # FAIL: Tool failed (e.g. bash syntax error). Route diagnosis back to Context for LLM to self-heal.
                VerdictKind.FAIL: Route(action=RouteAction.NEXT, target="context"),
            },
        ),
    )

    return PipelineSpec(
        id="codeact-loop",
        name="LAP CodeAct Agent Loop",
        nodes=[context_node, llm_node, tool_node],
        edges=[
            PipelineEdge(source="context", target="llm"),
            PipelineEdge(source="llm", target="tool", condition=VerdictKind.FAIL),
            PipelineEdge(source="tool", target="context"),
        ],
        entry="context",
    )
