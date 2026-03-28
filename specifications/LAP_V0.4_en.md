# Language Anchoring Protocol (LAP) — V0.4 Specification

> **Status**: Draft / V0.4
> **Date**: 2026-03-28
> **Author**: LAP Protocol Authors
> **Project**: OmniFactory
> **Changes from V0.x**: Major version upgrade. The entire protocol is rebuilt on the **Six-Primitive Semantic Model** as its theoretical foundation. All V0.1–V0.3 mechanisms are preserved and generalized within the new framework. See §9 for backwards-compatibility mapping.

---

## Core Shift

LAP V0.x was **Anchor-centric**: everything revolved around constraining LLM output, validating artifact formats, and routing within predefined pipelines.

LAP V0.4 is **Signal-centric**: **semantic precision supersedes format precision**. In LLM-dense systems, format constraints are a special case of semantic constraints — precise schema validation is only needed when the semantics genuinely require deterministic verification. Most of the time, natural language text itself is the most precise semantic carrier.

This shift does not repudiate V0.x work; it elevates it to a higher abstraction level. Anchors become the expression of Node type signatures. Verdicts become specializations of Signal. Pipelines become the dynamic routing result of Intent.

---

## Table of Contents

1. [Six Primitives](#1-six-primitives)
2. [Signal — The Semantic Currency](#2-signal--the-semantic-currency)
3. [Format — The Type System](#3-format--the-type-system)
4. [Hook — The Perception Layer](#4-hook--the-perception-layer)
5. [Node — The Processing Layer](#5-node--the-processing-layer)
6. [Tool — The Execution Layer](#6-tool--the-execution-layer)
7. [Intent — The Volition Layer](#7-intent--the-volition-layer)
8. [Consciousness Loop — The Execution Model](#8-consciousness-loop--the-execution-model)
9. [Backwards Compatibility: V0.x → V1.0 Mapping](#9-backwards-compatibility-v0x--v10-mapping)
10. [StateAnchor (Retained)](#10-stateanchor-retained)
11. [Task and Intent Unified](#11-task-and-intent-unified)
12. [Message Envelope (Upgraded)](#12-message-envelope-upgraded)
13. [MetaAgent Operation Protocol (Upgraded)](#13-metaagent-operation-protocol-upgraded)
14. [Cross-Machine Interoperability](#14-cross-machine-interoperability)

---

## 1. Six Primitives

LAP V0.4's theoretical foundation is six orthogonal primitives. Any mechanism in any LLM-dense system can be expressed as a combination of these six primitives — and the expression is complete: no mechanism requires any concept outside this model.

| Primitive | Alias | Layer | Responsibility |
|-----------|-------|-------|---------------|
| **Hook** | Sense Organ | Perception | Observe the environment under specific conditions; emit Signal |
| **Signal** | Message | Semantic | Semantic instance flowing between nodes (natural language text + type tag) |
| **Format** | Concept | Type | Semantic type of a Signal; defines "what it is" |
| **Node** | Processing Unit | Processing | Signal → Signal transformation (may invoke LLM) |
| **Tool** | Actuator | Execution | Operate external world; produce observable state changes |
| **Intent** | Volition | Volition | Special Signal triggering an execution cycle; consists of (input_Format, output_Format) pair |

**Model completeness**:
- Evolution mechanism = Consciousness loop (CompletionHook condition = `evolution_outcome: effective`)
- Pain system = Consciousness loop (CompletionHook condition = `pain_signal: decreasing`)
- Task execution = Intent + CompletionHook (condition = `output Format matches`)
- Meta-evolution = Higher-layer Consciousness loop observing lower-layer CompletionHook output

---

## 2. Signal — The Semantic Currency

### 2.1 Definition

Signal is the fundamental unit of exchange in the six-primitive system. All information flows between nodes as Signals. A Signal must be readable in natural language — an LLM or human should be able to directly consume its `text` field without parsing `meta`.

**Semantic Precision Principle**: `text` is the semantic body. Critical semantic information must not be stored only in the structured `meta` field. If information cannot be expressed in a sentence, Signal's `text` is that natural-language sentence.

```python
@dataclass
class Signal:
    format: str       # Format ID (type tag)
    text: str         # Natural language content (semantic body)
    node_id: str = "" # Source node (for traceability)
    meta: dict = field(default_factory=dict)  # Structured info (routing/filtering only)
```

### 2.2 Relationship to V0.x Verdict

V0.x's `Verdict` is a **specialization** of Signal: it expresses the semantic "judgment result." Signal generalizes Verdict — all semantic instances are Signals.

| V0.x Concept | V1.0 Equivalent |
|-------------|----------------|
| `Verdict(kind=PASS)` | `Signal(format="verdict.pass", text="Validation passed: ...")` |
| `Verdict(kind=FAIL, diagnosis=...)` | `Signal(format="verdict.fail", text=diagnosis)` |
| `Verdict.confidence` | `Signal.meta["confidence"]` |
| `Verdict.granted_tags` | `Signal.meta["granted_tags"]` |

### 2.3 Signal Flow Rules

- Signals are produced by Hook/Node; consumed by Node
- A Node consumes a Signal and produces a new Signal (transformation or aggregation)
- A ConsciousnessNode consumes a Signal and produces an Intent (a special Signal)
- A Tool receives invocation commands from a Node; does not directly consume Signals; returns results to the invoking Node
- Signals carry no execution logic — only semantic content

---

## 3. Format — The Type System

### 3.1 Definition

Format is the semantic type system. It defines "what a Signal is," not "how to handle it." Format is **declaration**; Node is **implementation**. The same Format can have multiple Node implementations and can evolve independently.

### 3.2 Format ID Naming Convention

Format IDs use dot-separated namespaces, similar to MIME types:

```
{domain}.{subdomain}[.{specifics}]

Examples:
  pain.routing.gap          # Routing blind-spot pain signal
  verdict.pass              # Anchor validation passed
  verdict.fail              # Anchor validation failed
  completion.evolution      # Evolution completion signal
  intent.evolve.node        # Intent to evolve a node
  state.anchor.git_commit   # git commit state anchor (hard type)
  trace.exec.hard_node      # TRACE-SED extracted hard-node execution trace
```

### 3.3 Format Definition Structure

```python
class FormatSpec(BaseModel):
    id: str                        # Globally unique ID
    name: str                      # Human-readable name
    description: str               # Natural language description (core — LLM-readable)
    examples: list[FormatExample]  # 2–5 input→output examples (primary definition method)
    parent_id: str | None = None   # Parent type (type inheritance)
    hard: bool = False             # True = hard type (deterministic), False = soft (semantic)
    schema: dict | None = None     # Optional: JSON Schema (hard types only)

class FormatExample(BaseModel):
    input_text: str   # Natural language input example
    output_text: str  # Natural language output example
    note: str = ""    # Optional annotation
```

### 3.4 Example-Driven Format Definition (Core Innovation)

**V1.0 key design principle**: Format is primarily defined by natural language `description` and `examples`. JSON Schema is an optional additive constraint (used only for hard types).

Traditional protocols require: define Schema first, then validate against Schema.
V1.0 approach: describe semantics in natural language and examples first; use LLM to judge "does this Signal semantically match the intent of Format X?"

```yaml
# Example: pain.routing.gap Format definition
id: pain.routing.gap
name: Routing Blind-Spot Pain Signal
description: |
  Indicates the system discovered that, when handling a certain task type,
  no suitable processing node exists in the routing network, causing task
  failure or degradation to a low-quality path. This signal means a new
  semantic node needs to be created to cover this blind spot.
examples:
  - input_text: "Task: analyze feishu data; Error: no node can handle feishu_table format"
    output_text: "Routing gap: feishu_table → analysis, ~20 routing attempts all failed, recommend creating new node"
  - input_text: "15 of last 20 steps routed to generic_processor but all failed"
    output_text: "Routing gap detected: generic_processor is unsuitable for current task type, specialized node needed"
hard: false  # Semantic validation — no precise JSON Schema needed
```

### 3.5 Format Inheritance

```
signal
  ├── pain.*
  │   ├── pain.routing.gap
  │   ├── pain.node.timeout
  │   └── pain.evolution.failed
  ├── verdict.*
  │   ├── verdict.pass
  │   └── verdict.fail
  ├── intent.*
  │   └── intent.evolve.*
  ├── completion.*
  │   └── completion.evolution
  └── state.anchor.*  ← hard types (hard=True)
      ├── state.anchor.git_commit
      └── state.anchor.file_hash
```

---

## 4. Hook — The Perception Layer

### 4.1 Definition and Rules

Hook is the system's sense organs. Observe environment, judge trigger conditions, emit Signal list — no decisions, no execution, no state modification.

**Key constraints**:
- `poll()` / `on_event()` must not call LLM
- Must not write any external state (read-only)
- `Signal.text` must be human-readable natural language, not numeric strings

### 4.2 Two Forms

```python
class PeriodicHook(ABC):
    """Periodic sensing — fires every N rounds."""
    async def poll(self, db_path: str, round_num: int) -> list[Signal]: ...
    def should_poll(self, round_num: int) -> bool: ...

class EventHook(ABC):
    """Event-driven sensing — called synchronously when an event occurs."""
    def on_event(self, event: dict) -> list[Signal]: ...
```

### 4.3 CompletionHook — The Loop-Closing EventHook

**CompletionHook** is a specialization of EventHook: observe an execution result Signal, check whether its Format satisfies an Intent's `output_format`. If satisfied, emit a "completion" Signal to close the Consciousness loop.

```python
class CompletionHook(EventHook):
    """Observe execution result; judge whether Intent is fulfilled.

    Trigger condition: observed_signal.format ≈ intent.output_format
    Result: Signal(format="completion.{output_format}", text=execution summary)
    """
    def __init__(self, intent_output_format: str, target_node_id: str): ...
    def on_event(self, event: dict) -> list[Signal]: ...
```

CompletionHook embodies a deep insight: **"realizing something is done" is always an act of observation**. Completion cannot be self-assessed by the executor — it must be determined by an independent observer (Hook). This is both an architectural constraint and a mechanism for preventing self-deception.

---

## 5. Node — The Processing Layer

### 5.1 Two Node Types

```python
class BaseNode(ABC):
    """Ordinary processing node: Signal → Signal transformation."""
    def process(self, signal: Any) -> Any: ...

class ConsciousnessNode(ABC):
    """Consciousness node: Signal → Intent decision."""
    def decide(self, signal: Any, *args, **kwargs) -> Any: ...
    def ready(self, *args) -> bool: ...  # Cooldown control
```

### 5.2 Node Type Signature (Corresponds to V0.x AnchorSpec)

Every Node has an input/output Format signature. V0.x's `AnchorSpec` corresponds to this signature:

```python
class Router(ABC):
    """Pipeline execution interface for Node (runtime binding)."""
    INPUT_KEYS: list[str] | None = None
    OUTPUT_KEYS: list[str] | None = None
    def validate_input(self, input_data: Any) -> Verdict | None: ...
    def validate_output(self, verdict: Verdict) -> Verdict | None: ...
    def run(self, input_data: Any) -> Verdict: ...
```

### 5.3 Consciousness Node Internal Structure (Four-Stage Expansion)

Complex Consciousness nodes can be expanded into four independently evolvable stages:

```
Monitor → Judge → Project(Intent) → [execution outside the loop] → CompletionHook → Monitor
```

| Stage | Responsibility | Evolution Granularity |
|-------|---------------|----------------------|
| Monitor | Aggregate Hook Signals; maintain state semantic summary | Aggregation strategy evolvable |
| Judge | Decide whether to project Intent and its content | **System intelligence ceiling — must evolve independently** |
| Project | Format Intent as execution request | Output format evolvable |
| CompletionHook | Observe results; close the loop | Completion condition evolvable |

**Why Judge must be independent**: The "execution result Signal" produced by CompletionHook is Judge's **external training signal**. Judge projects Intent X; X executes (without Judge's involvement); CompletionHook independently observes the result; CompletionHook produces "did X achieve the goal?" Signal. This is Judge's basis for evolution. When Monitor and Judge are merged, this external signal cannot be directionally fed back to Judge — the system's intelligence ceiling is frozen.

---

## 6. Tool — The Execution Layer

### 6.1 Definition and Rules

Tool is the system's actuators. They operate the external world (filesystem, network, database) and produce observable state changes. Tools do not make semantic judgments, do not call LLM — they only execute deterministic operations.

```python
class Tool(ABC):
    name: str         # Unique tool identifier
    description: str  # Natural language description (for LLM to understand purpose)

    def execute(self, params: dict) -> dict:
        """Execute and return {"success": bool, "output": str, ...}"""
        ...
```

### 6.2 Tool vs V0.x Transformer

V0.x's `Transformer` is a specialization of Tool (focused on Format type conversion):

| V0.x Concept | V1.0 Equivalent |
|-------------|----------------|
| `Transformer(method=RULE)` | Deterministic Tool |
| `Transformer(method=LLM)` | Node (LLM calls belong in Node layer, not Tool) |
| `Transformer(method=HYBRID)` | Node + Tool combination |

---

## 7. Intent — The Volition Layer

### 7.1 Definition

Intent is the special Signal produced by ConsciousnessNode to trigger an execution cycle. Intent's essence is a **type signature**: it declares "I need an execution that accepts Format_A input and produces Format_B output."

Intent does not specify "how to do it" — only "what type of thing to do." The specific execution path is dynamically matched by the semantic router based on the (input_format, output_format) pair.

```python
@dataclass
class Intent:
    format: str = "intent"
    text: str = ""                 # Natural language description of the intent
    node_id: str = ""              # ID of the Consciousness node that emitted this Intent
    meta: dict = field(default_factory=dict)
    input_format: str = ""         # Expected input Format
    output_format: str = ""        # Expected output Format (CompletionHook match target)
    priority: float = 0.5
    deadline_rounds: int = -1      # Timeout in rounds (-1 = no timeout)
```

### 7.2 Relationship to V0.x

| V0.x Concept | V1.0 Equivalent |
|-------------|----------------|
| `AnchorSpec(format_in, format_out)` | `Intent(input_format, output_format)` |
| Predefined Pipeline execution order | Intent → semantic router dynamically matches Node chain |
| `Route(action=RETRY)` | Execution failed → CompletionHook not triggered → Judge re-projects Intent |
| `Route(action=EMIT)` | CompletionHook triggered → loop closed |
| `StateAnchor` (V0.3) | Hard-type Signal (`state.anchor.*`) |
| `Task` (V0.3) | Intent lifecycle instance |

---

## 8. Consciousness Loop — The Execution Model

### 8.1 Minimal Consciousness Loop

```
Hook ──Signal──→ ConsciousnessNode.decide()
                        │
                        ├── None → No trigger (cooldown/threshold not met)
                        │
                        └── Intent ──→ Semantic Router ──→ Node execution chain
                                                                  │
                                                         CompletionHook.on_event()
                                                                  │
                                               Signal(format="completion.*")
                                                                  │
                                          ← feeds back to ConsciousnessNode ←
```

### 8.2 The Singularity Problem and Its Solution

**Problem**: If Judge is a single indivisible node, Judge's quality freezes the system intelligence ceiling, and Judge cannot be externally evaluated (self-evaluation = hallucination).

**Solution**: The execution result Signal produced by CompletionHook is an **external fact**, not Judge's self-assessment.

- Judge projects Intent X
- X is executed (Judge does not participate in execution)
- CompletionHook independently observes the execution result
- CompletionHook produces "did X achieve the goal?" Signal
- This Signal is Judge's training signal (external truth)
- The evolution system can independently optimize Judge's `processing_prompt`

**Conclusion**: The Consciousness loop, via CompletionHook, establishes an observable causal chain between Judge's decisions and their outcomes, making Judge evolvable. System intelligence is not frozen.

### 8.3 Multi-Layer Consciousness Loops (Meta-Evolution)

```
Meta Consciousness Loop (monitors quality of lower-level loops)
    │
    ├── Observes lower CompletionHook output
    ├── Judge: does the lower Consciousness need evolution?
    └── Intent: evolve a lower-level Judge node
           │
    Pain Consciousness Loop (monitors node pain)
           │
    Evolution Consciousness Loop (executes specific evolution)
           │
    Task Execution Consciousness Loop (innermost)
```

Every layer has the same six-primitive structure. Meta-evolution requires no special primitives — it is simply a higher-layer Consciousness node observing lower-layer nodes' CompletionHook output.

---

## 9. Backwards Compatibility: V0.x → V1.0 Mapping

### 9.1 Complete Mapping Table

| V0.x Concept | V1.0 Equivalent | Migration Strategy |
|-------------|----------------|-------------------|
| `FormatSpec` | `FormatSpec` (retained, add `examples` field) | Existing definitions auto-compatible |
| `AnchorSpec` | Node type signature + `FormatSpec` | Anchor decomposed into Node + Format |
| `ValidatorSpec` / `Validator` | `Node.validate_input/output` | Internalized as Node interface |
| `Verdict(kind, output, diagnosis)` | `Signal(format="verdict.*", text=diagnosis)` | Verdict still usable as Signal specialization |
| `Route(action=NEXT/RETRY/EMIT)` | Semantic router decision | From static routing table to dynamic semantic matching |
| `Transformer(RULE)` | Deterministic Tool | Classified by implementation |
| `Transformer(LLM)` | LLM Node | — |
| `OperatorSpec` | `semantic_nodes` table records | Persisted to DB; supports evolution |
| `StateAnchor` | Hard-type Signal (`state.anchor.*`) | See §10 |
| `Task` | Intent lifecycle instance | See §11 |
| `Message Envelope` | Message Envelope (upgraded) | See §12 |
| `LAP-MOP` | MetaAgent Operation Protocol (upgraded) | See §13 |

### 9.2 V0.x Pipeline Migration

V0.x's static Pipelines (predefined node sequences) have two migration paths in V1.0:

**Path A: Remain Static (Conservative Migration)**
Map existing Pipeline directly to a Node execution chain; semantic router always routes to this chain. Behavior is identical to V0.x.

**Path B: Dynamicize (Full Migration)**
Convert Pipeline entry to Intent; let the semantic router dynamically match the best execution path. Gains adaptive capability, but requires the semantic network to accumulate sufficient historical data.

---

## 10. StateAnchor (Retained)

StateAnchor is re-expressed in V1.0 as a **hard-type Signal** (`hard=True` Format):

```python
Signal(
    format="state.anchor.git_commit",   # Hard type
    text="git commit abc123 verified: implemented feature X",
    meta={
        "commit_hash": "abc123",
        "verified_at": "2026-03-28T10:00:00",
        "path": "e:/WindowsWorkspace"
    }
)
```

**StateAnchor's special value**: Provides **objective completion evidence that does not depend on LLM judgment** for CompletionHook. When an Intent's completion condition can be expressed as a StateAnchor, CompletionHook can trigger deterministically — immune to LLM hallucination.

StateAnchor tiers (retained from V0.3):
| Tier | Kind | Completion Condition Reliability |
|------|------|--------------------------------|
| 1 | `git_commit` | Highest (immutable) |
| 2 | `file_hash` | High (content-bound) |
| 3 | `p4_changelist` | Medium (may be continued) |
| 4 | `api_snapshot` | Low (time-bounded) |
| 5 | `agent_output` | ⚠️ Very Low (LLM assertion, not independently verifiable) |

---

## 11. Task and Intent Unified

V0.3's `Task` is the execution instance of a Pipeline. In V1.0, Task corresponds to the **lifecycle** of an Intent:

```
Intent emitted → Semantic router matches → Execution begins (Task.status = running)
                                               ↓
                                       CompletionHook fires (Task.status = completed)
                                               ↓
                              CompletionHook not fired before deadline (Task.status = failed)
```

TaskStatus transitions (retained from V0.3, semantics aligned):
```
pending → running → completed
                 → failed
                 → paused → running   (after human intervention or resource wait)
```

Task remains the entity for recording execution history. The trigger mechanism changes from "call Pipeline.run()" to "ConsciousnessNode emits Intent."

---

## 12. Message Envelope (Upgraded)

V0.3's Message Envelope gains a `signal` field in V1.0 to express payload type uniformly as Signal:

```json
{
  "lap_version": "0.4",
  "envelope_id": "01KM4Z2A...",
  "task_id": "01KM4XZD...",
  "parent_id": "01KM4X...",
  "origin": {
    "kind": "human | agent | system | external_node",
    "identity": "user@example.com | node:sed.feishu_parser"
  },
  "signal": {
    "format": "feishu_state_data",
    "text": "Feishu message om:abc123 read; content is ...",
    "node_id": "sed.feishu_parser",
    "meta": {}
  },
  "state_anchor": {
    "kind": "file_hash",
    "ref": "sha256:abc...",
    "path": "data/feishu_msg.json"
  },
  "visibility": "private | internal | public",
  "payload": { "...": "Backwards-compat: raw payload retained" }
}
```

**V1.0 additions**: `origin.kind` gains `external_node` (for cross-machine interoperability); `signal` field uniformly expresses semantic content (`payload` retained for V0.x compatibility).

---

## 13. MetaAgent Operation Protocol (Upgraded)

V0.3's LAP-MOP operations are remapped as Intents in V1.0:

| V0.3 LAP-MOP Op | V1.0 Intent |
|----------------|------------|
| `CreateNode` | `Intent(input_format="routing.gap", output_format="semantic_node.new")` |
| `MergeNodes` | `Intent(input_format="semantic_node.pair", output_format="semantic_node.merged")` |
| `SplitNode` | `Intent(input_format="semantic_node.overgeneral", output_format="semantic_node.split")` |
| `RecordOutcome` | CompletionHook fires automatically — no explicit operation needed |
| `ProposeType` | `Intent(input_format="format.proposal", output_format="format.registered")` |
| `ObsoleteNode` | Intent produced by Pain Consciousness loop judgment |

All operations' audit trails, confidence thresholds, and `pending_review` lifecycle are retained from V0.3, now naturally implemented via Consciousness loop CompletionHook.

---

## 14. Cross-Machine Interoperability

This section provides the basic framework for cross-machine interoperability. Detailed protocol: see separate document *Semantic Exchange Protocol (SEP) V0.1*.

### 14.1 Core Principles

**External systems can register as any six-primitive implementation**:

| External System Type | Registered As | Communication Pattern |
|--------------------|--------------|----------------------|
| External API service | ExternalTool / ExternalNode | HTTP (pull model) |
| External event stream | ExternalHook | WebSocket/SSE (push model) |
| External LLM service | ExternalNode (LLM type) | HTTP + streaming |
| External format library | FormatProvider | HTTP (declarative) |

### 14.2 Registration Principle

External primitive registration does not require precise Schema — registration provides:
1. **Natural language description**: what this primitive does
2. **Examples**: 3–5 input→output Signal pairs
3. **Endpoint info**: how to access
4. **Visibility declaration**: which visibility levels are supported

The system infers Format from examples and registers a node in the semantic network.

### 14.3 Format Negotiation

When the output Format of a calling node does not precisely match the expected input Format of a called external node:
- Semantic router checks semantic similarity (not exact format match)
- If semantic similarity > threshold, insert LLM Transformer Node to bridge automatically
- If semantic similarity < threshold, return "cannot route" Signal, trigger Consciousness judgment

**Semantic precision supersedes format precision**: exact format match is not required; semantic intent must be understandable.

---

## Appendix A: Core Primitive Interface Summary

```python
# Signal
@dataclass
class Signal:
    format: str; text: str; node_id: str = ""; meta: dict = field(default_factory=dict)

# Hook
class PeriodicHook(ABC):
    async def poll(self, db_path: str, round_num: int) -> list[Signal]: ...
class EventHook(ABC):
    def on_event(self, event: dict) -> list[Signal]: ...

# Node
class BaseNode(ABC):
    def process(self, signal: Any) -> Any: ...
class ConsciousnessNode(ABC):
    def decide(self, signal: Any, *args, **kwargs) -> Any: ...
    def ready(self, *args) -> bool: ...

# Tool
class Tool(ABC):
    name: str; description: str
    def execute(self, params: dict) -> dict: ...

# Format
class FormatSpec(BaseModel):
    id: str; name: str; description: str
    examples: list[FormatExample] = []
    parent_id: str | None = None; hard: bool = False
    schema: dict | None = None

# Intent
@dataclass
class Intent:
    format: str = "intent"; text: str = ""; node_id: str = ""
    meta: dict = field(default_factory=dict)
    input_format: str = ""; output_format: str = ""
    priority: float = 0.5; deadline_rounds: int = -1
```

---

## Appendix B: Six-Primitive Model Completeness Verification

| System Mechanism | Six-Primitive Expression | Verified Complete |
|-----------------|------------------------|-------------------|
| Task execution | Intent(input→output) + CompletionHook | ✅ |
| Pain-driven evolution | Pain Hook → PainJudge(ConsciousnessNode) → Intent → Evolution Node chain → CompletionHook | ✅ |
| Routing gap detection | RoutingGapHook → RoutingGapJudge → Intent(create_node) → CreateNode Tool → CompletionHook | ✅ |
| Meta-evolution | EvoCompletionHook → MetaJudge → Intent(evolve_judge) → Evolution Node chain | ✅ |
| Human review | CompletionHook condition = `human_approval_signal` | ✅ |
| Cross-machine call | ExternalTool/Node registered in semantic network; Intent routes normally | ✅ |

All mechanisms can be expressed losslessly in six primitives.

---

*LAP V0.4 — Language Anchoring Protocol Release — 2026-03-28*
