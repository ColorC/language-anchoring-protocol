# Language Anchoring Protocol (LAP) — V0.3 Specification

> **Status**: Draft / V0.3
> **Date**: 2026-03-20
> **Author**: LAP Protocol Authors
> **Project**: OmniFactory
> **Changes from V0.2**: Added seven new protocol primitives addressing gaps discovered
> through Explorer V4 experiments and software engineering design review.
> All additions are **additive** — V0.2 pipelines continue to work unchanged.

---

## Table of Contents

1. [New Primitive: StateAnchor — Physical World State](#1-new-primitive-stateanchor)
2. [New Primitive: Task — Stateful Execution Instance](#2-new-primitive-task)
3. [New Primitive: Message Envelope — Transport-Agnostic Protocol Carrier](#3-new-primitive-message-envelope)
4. [Visibility & Privacy: Public/Internal/Private Separation](#4-visibility--privacy)
5. [Response Modes: Single-Point vs Full-Trace](#5-response-modes)
6. [Provenance Fields: Intent Step Traceability](#6-provenance-fields)
7. [MetaAgent Operation Protocol (LAP-MOP)](#7-metaagent-operation-protocol-lap-mop)
8. [Updated Standard Library Tags](#8-updated-standard-library-tags)

---

## 1. New Primitive: StateAnchor

### 1.1 Motivation

**Discovered through Explorer V4 Experiment** (2026-03-20):

An agent claimed to have produced `feishu_message_output` (a semantic type label).
Subsequent tasks used this label as a task entry point — but no file or retrievable
entity with that name existed. The agent spent all 25 allowed steps searching for
a file that was never created, then failed.

**Root Cause**: LAP V0.1/V0.2 defined "semantic types" of data, but never defined
"the physical state of the world when this pipeline executes." This caused two
fundamentally different objects to be conflated:

- `agent_output` — a semantic label that an LLM claims to have produced (only valid
  within the current trace context)
- `state_anchor` — an independently verifiable physical fact (git hash, file digest,
  version control number)

### 1.2 Definition

A **StateAnchor** is an independently verifiable reference point in the physical world:

```
StateAnchor = {
    kind:        StateKind     -- reliability tier (see below)
    ref:         str           -- the identifier ("abc123" / "sha256:..." / "CL:12345")
    path:        str | None    -- file path or service URL
    verified_at: datetime      -- when this anchor was last confirmed
    is_mutable:  bool          -- can external actors change this? (e.g., user edits on top of a P4 CL)
    trace_id:    str           -- which agent trace produced/observed this anchor
}
```

### 1.3 StateKind Reliability Tiers

| Tier | Kind | Reliability | Notes |
|------|------|-------------|-------|
| 1 (highest) | `git_commit` | Immutable | Once pushed, content never changes |
| 2 | `file_hash` | Content-bound | SHA-256 of file contents; path can change |
| 3 | `p4_changelist` | Server truth | User may continue editing on top of it → `is_mutable=True` |
| 3 | `svn_revision` | Server truth | Same as P4; check `is_mutable` |
| 4 | `api_snapshot` | Time-bounded | External service state at a point in time; has TTL |
| 5 (lowest) | `agent_output` | ⚠️ Ephemeral | LLM claimed it produced this. **Never use as a Pipeline entry point.** |

### 1.4 The Core Promotion Rule

An `agent_output` anchor may be **promoted** to `file_hash` if and only if:

1. The agent wrote output to a specific file path.
2. A Hard Anchor (e.g., file existence check + sha256 computation) has verified the file.
3. The newly computed sha256 becomes the new `ref`, and `kind` is changed to `FILE_HASH`.

```
BEFORE: StateAnchor(kind=AGENT_OUTPUT, ref="feishu_message_output", ...)
         — agent claims it produced this, unverified

AFTER:  StateAnchor(kind=FILE_HASH, ref="sha256:abc...", path="data/feishu_msg.json", ...)
         — file actually exists and matches the claimed output
```

### 1.5 StateSnapshot

A **StateSnapshot** is a collection of StateAnchors captured at the start of a `run_agent` call:

```json
{
  "task_id": "01KM...",
  "trace_id": "01KM...",
  "assertion": "HARD",
  "anchors": [
    {"kind": "git_commit", "ref": "abc123", "path": "e:/WindowsWorkspace"},
    {"kind": "file_hash", "ref": "sha256:...", "path": "data/feishu_v1_state.json"}
  ]
}
```

`assertion` declares the overall trustworthiness of the snapshot:
- `"HARD"` — all anchors have been independently verified
- `"SOFT"` — user-asserted or LLM-inferred, not independently verified

---

## 2. New Primitive: Task

### 2.1 Motivation

LAP V0.1/V0.2 defined `Pipeline` (a static blueprint) and `Anchor` (an execution unit),
but had no concept of a **Task** — the stateful runtime instance of a Pipeline execution.

Without a Task primitive:
- There is no standard way to represent "pause and wait for human review"
- There is no standard way to represent "this task consists of sub-tasks"
- Success/failure cannot be propagated back to the route graph
- Task history is not cumulative across restarts

### 2.2 Definition

```
Task = {
    task_id:        str              -- ULID, globally unique
    parent_task_id: str | None       -- for sub-tasks; None = root task
    origin:         TaskOrigin       -- who initiated: human | explorer | meta_agent
    pipeline_id:    str              -- which Pipeline blueprint this task runs
    state_snapshot: StateSnapshot    -- physical world state at task start
    status:         TaskStatus       -- pending | running | paused | completed | failed
    result:         str | None       -- final agent output (if completed)
    trace_id:       str | None       -- linked intent trace ID
    created_at:     datetime
    completed_at:   datetime | None
}
```

**TaskStatus transitions**:
```
pending → running → completed
                 → failed
                 → paused → running   (after human review)
```

### 2.3 Task Lineage

Tasks form a tree via `parent_task_id`. This allows:
- **Explorer sessions**: all tasks spawned by one Explorer instance share a `session_task_id` as their `parent_task_id`
- **Human escalations**: when an agent cannot proceed, it creates a `paused` task, and a human resumes it
- **Meta-agent fan-out**: a planning task spawns multiple execution sub-tasks in parallel

---

## 3. New Primitive: Message Envelope

### 3.1 Motivation

LAP currently operates entirely as in-process function calls. There is no definition
of what a LAP message looks like when transmitted over a network. This prevents:
- HTTP/WebSocket/file-based transport of LAP messages
- Cross-organization collaboration on shared Pipelines
- Privacy-preserving message forwarding (stripping private fields before external delivery)

### 3.2 The LAP Message Envelope

A **transport-agnostic envelope** that wraps any LAP payload for transmission:

```json
{
  "lap_version": "0.3",
  "envelope_id": "01KM4Z2A...",
  "task_id":     "01KM4XZD...",
  "parent_id":   "01KM4X...",
  "origin": {
    "kind":     "human | agent | system",
    "identity": "user@example.com | agent:explorer-v4 | cron"
  },
  "visibility": "private | internal | public",
  "format_id":   "feishu_state_data",
  "format_tags": ["ground-truth.file", "domain:feishu"],
  "state_anchor": {
    "kind": "file_hash",
    "ref":  "sha256:abc...",
    "path": "data/feishu_v1_state.json"
  },
  "payload": { ... },
  "signature": null
}
```

### 3.3 Transport Bindings

The envelope is transport-agnostic. Bindings for specific transports:

| Transport | Usage | Endpoint Pattern |
|-----------|-------|-----------------|
| **HTTP REST** | External requests, public API | `POST /lap/v1/task` |
| **WebSocket** | Streaming responses, live monitoring | `ws://host/lap/v1/stream/{task_id}` |
| **File / IPC** | Local inter-process, offline queue | `lap_inbox/` directory poll |
| **SQLite (existing)** | Single-machine, SQLiteBus | In-process via `FactoryEvent` |

The existing `SQLiteBus` + `FactoryEvent` constitutes the File/IPC binding.
`RedisBus` (already reserved in SDK contract) is the intended HTTP/WebSocket backend.

---

## 4. Visibility & Privacy

### 4.1 Three Visibility Levels

Every Message Envelope carries a `visibility` field:

| Level | Meaning | Forwarding Rules |
|-------|---------|-----------------|
| `private` | Sensitive data; must not cross trust boundaries | Strip before any external delivery |
| `internal` | Organization-internal; not for public APIs | Strip payload, return type summary only |
| `public` | Safe to expose in full | Return as-is |

### 4.2 Projection Rules (for External Responses)

When a response crosses a trust boundary (e.g., an external HTTP client requests a full trace):

```
ProjectedResponse(msg, visibility_level):
  if msg.visibility == "private":
      → replace payload with {"_redacted": true, "format_id": msg.format_id}
  elif msg.visibility == "internal":
      → replace payload with {"_summary": msg.format_id, "step_count": ...}
  else:
      → return full payload
```

This implements the two response modes described in Section 5.

### 4.3 Examples of Each Level

| Data | Level | Rationale |
|------|-------|-----------|
| API keys / OAuth tokens | `private` | Must never leave the originating system |
| Internal file paths (`E:\WindowsWorkspace\...`) | `private` | Leaks directory structure |
| Agent reasoning steps | `internal` | Useful for same-org debugging, not public |
| Task status (pending/completed) | `public` | Safe to expose |
| Final task result (if non-sensitive) | `public` | Context-dependent |

---

## 5. Response Modes

### 5.1 Single-Point Response

Returns only the task's final state without internal trace:

```json
{
  "task_id": "01KM...",
  "status": "completed",
  "result_format": "feishu_state_data",
  "result_summary": "message_id=om:abc123",
  "verdict": "PASS",
  "steps_taken": 4,
  "visibility": "public"
}
```

Use when: the caller only needs the outcome, not the reasoning path.

### 5.2 Full-Trace Response

Returns the complete execution history, projected to the requested visibility level:

```json
{
  "task_id": "01KM...",
  "status": "completed",
  "visibility_projection": "internal",
  "semantic_path": [
    "user_request → feishu_state_data → recall_result"
  ],
  "trace": [
    {
      "step": 0,
      "tool": "think",
      "action_class": "acquire",
      "input_types": ["user_request"],
      "output_types": ["feishu_state_data"],
      "desc": "Read feishu_v1_state.json to get message_id",
      "type_source": "llm_infer",
      "route_node_id": "...",
      "route_decision": "MERGE"
    }
  ]
}
```

Use when: debugging, Critic analysis, or building a semantic map of what happened.

---

## 6. Provenance Fields

### 6.1 Motivation

In V0.1/V0.2, each intent step recorded **what** happened (`input_types`, `output_types`,
`action_class`), but not **why we believe the types are correct** or **who triggered this step**.

Without provenance:
- It is impossible to distinguish a type label that was reliably matched from historical
  data vs. one the LLM invented wholesale.
- Critic/debugging systems cannot tell which steps were initiated by a human vs. Explorer.
- Route graph merges cannot be traced back to the specific trace that caused them.

### 6.2 New Fields on Intent Steps (V0.3)

Added to `intent_steps` table and to `IntentTracer`:

| Field | Type | Values | Meaning |
|-------|------|--------|---------|
| `type_source` | str | `llm_infer`, `history_match`, `user_explicit` | How the semantic type was determined |
| `type_confidence` | float | 0.0–1.0 (−1 = unknown) | Confidence in the type assertion |
| `parent_task_id` | str | ULID or empty | Which Task spawned this trace |
| `origin` | str | `human`, `explorer`, `meta_agent` | Who initiated the trace |
| `route_node_id` | str | ULID or empty | Which route_node this step was merged into (backfilled by RouteClassifier) |
| `route_decision` | str | `NEW`, `MERGE`, `NOISE`, or empty | RouteClassifier's decision for this step (backfilled) |

### 6.3 Backfill Protocol

`route_node_id` and `route_decision` are empty at record time and backfilled by
`RouteClassifier` after the trace is processed. `IntentTracer.record_route_decision()`
is the designated method for this write-back.

---

## 7. MetaAgent Operation Protocol (LAP-MOP)

### 7.1 Motivation

The Explorer currently writes directly to `route_graph.db` on every classification.
This means:
- There is no audit trail of **why** a node was created or merged
- There is no mechanism for human or higher-level review of graph operations
- Automatic merges can silently destroy precision that took many traces to build up

### 7.2 Graph Operation Primitives

LAP-MOP defines the standard set of operations a MetaAgent may propose on the route graph:

| Op | Args | Effect |
|----|------|--------|
| `CreateNode` | `(input_types, output_types, action_class, desc, tool_name, evidence_trace_id)` | Add a new `IntentNode` to the route graph |
| `MergeNodes` | `(node_id_a, node_id_b, canonical_desc, evidence_trace_ids)` | Merge two semantically equivalent nodes |
| `SplitNode` | `(node_id, split_criteria, new_nodes)` | Split an over-general node into more precise ones |
| `RecordOutcome` | `(node_id, success, trace_id)` | Update a node's `success_rate` EMA |
| `ProposeType` | `(type_name, definition, examples, evidence_trace_id)` | Register a new semantic type  |
| `LinkTypes` | `(parent_type, child_type, relationship)` | Declare a type hierarchy relationship |
| `ObsoleteNode` | `(node_id, reason, evidence_trace_id)` | Mark a node as deprecated (not deleted) |

### 7.3 Operation Lifecycle

Every LAP-MOP operation goes through:

```
proposed → [confidence >= auto_accept_threshold] → accepted
         → [confidence < threshold]              → pending_review → accepted | rejected
```

All operations are persisted regardless of acceptance status, creating a full audit log.

### 7.4 Evidence Requirements

Every LAP-MOP operation must carry:
- `evidence_trace_id`: the trace ID that triggered this proposal
- `confidence`: 0.0–1.0 (operations above threshold are auto-accepted)
- `proposed_by`: `'llm'` | `'embedding_auto'` | `'human'`

---

## 8. Updated Standard Library Tags

Additions to LAP Standard Library for V0.3:

### 8.1 State & Provenance Tags

| Tag | Meaning |
|-----|---------|
| `state.git_anchored` | Format instance tied to a specific git commit |
| `state.file_anchored` | Format instance verified by file hash |
| `state.agent_output` | ⚠️ Ephemeral; produced by an agent, not independently verified |
| `provenance.llm_infer` | Type label was inferred by LLM (default) |
| `provenance.history_match` | Type label was matched from route graph history |
| `provenance.user_explicit` | Type label was explicitly declared by a human |

### 8.2 Task & Origin Tags

| Tag | Meaning |
|-----|---------|
| `origin.human` | Initiated by a human |
| `origin.explorer` | Initiated by an Explorer agent session |
| `origin.meta_agent` | Initiated by a MetaAgent planning step |
| `visibility.private` | Contains sensitive information; do not expose |
| `visibility.internal` | Usable within organization; project before external delivery |
| `visibility.public` | Safe to expose in full |

---

## Appendix: Glossary Additions (V0.3)

| Term | Definition |
|------|------------|
| **StateAnchor** | An independently verifiable reference point in the physical world (git hash, file digest, etc.) used to ground a Pipeline's assumptions about environmental state. |
| **StateSnapshot** | Collection of StateAnchors captured at task start; makes Pipeline execution reproducible. |
| **Task** | A stateful runtime instance of a Pipeline execution, with lifecycle (pending/running/paused/completed/failed) and parent-child relationships. |
| **Message Envelope** | Transport-agnostic wrapper for any LAP payload when transmitted over network or IPC. |
| **Visibility** | Three-level privacy classification (private/internal/public) controlling how data may be forwarded across trust boundaries. |
| **LAP-MOP** | MetaAgent Operation Protocol — standard operations for proposing modifications to the route graph with audit trail and acceptance lifecycle. |
| **Provenance** | The record of *how* a semantic type label was determined (LLM inference vs. history match vs. explicit declaration). |
