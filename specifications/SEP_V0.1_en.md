# Semantic Exchange Protocol (SEP) V0.1
## Six-Primitive Cross-Machine Interoperability

> **Status**: Draft / V0.1
> **Date**: 2026-03-28
> **Based on**: LAP V0.4 + Six-Primitive Semantic Interface Specification V1.0
> **Role**: Defines how external systems plug in as any six-primitive type to join the semantic node mesh — enabling cross-machine, cross-organization semantic-level interoperability

---

## Core Design Philosophy

### Semantic Precision Supersedes Format Precision

Traditional interoperability protocols (REST/RPC/gRPC) are built on **format contracts**: caller and callee must agree on precise data structures, and any format deviation is an error.

SEP is built on **semantic contracts**: participants agree on "the semantic intent of this operation," and format is an implementation detail negotiable at runtime.

In LLM-dense systems:
- Format validation failure → requires human intervention
- Semantic understanding failure → also requires human intervention
- **Format mismatch but semantics understandable** → LLM can bridge automatically, system continues

Therefore, SEP treats format constraints as an optional optimization, not a mandatory prerequisite.

### Register by Example, Not by Schema

External nodes do not need to provide a JSON Schema or OpenAPI specification when registering. What they need:
- Natural language description: what this primitive does
- 3–5 examples: concrete input Signal → output Signal pairs

The system infers Format from examples and registers the node in the semantic network. This makes the registration process LLM-friendly and human-friendly while retaining enough semantic information for the router to use.

---

## Table of Contents

1. [Participant Types](#1-participant-types)
2. [Registration Protocol](#2-registration-protocol)
3. [Discovery Protocol](#3-discovery-protocol)
4. [Signal Exchange Protocol](#4-signal-exchange-protocol)
5. [Format Negotiation](#5-format-negotiation)
6. [Hook Subscription Protocol](#6-hook-subscription-protocol)
7. [Trust Model](#7-trust-model)
8. [Distributed Node Mesh](#8-distributed-node-mesh)
9. [Complete Examples](#9-complete-examples)
10. [Comparison with Traditional Protocols](#10-comparison-with-traditional-protocols)

---

## 1. Participant Types

SEP allows external systems to join as any six-primitive type:

### 1.1 ExternalNode

An external system acting as a Node: receives a Signal, processes it (may invoke external LLM), returns a Signal.

```
ExternalNode characteristics:
- Has semantic description and examples
- Accepts Signal input, returns Signal output
- Can be stateless (each call independent) or stateful (maintains session)
- HTTP endpoint (synchronous) or WebSocket endpoint (streaming)
```

Typical use cases:
- External LLM services (transforms Signal into LLM prompt, returns response as Signal)
- Domain-specialist services (legal analysis, medical coding, code review)
- Data transformation services (deterministic Format A → Format B conversion)

### 1.2 ExternalTool

An external system acting as a Tool: performs deterministic operations, produces external world changes.

```
ExternalTool characteristics:
- Operates external world (database, filesystem, third-party API)
- Deterministic execution (same input → same output)
- Does not call LLM
- Returns {"success": bool, "output": str, "state_anchor": {...}}
```

Typical use cases:
- Database write services
- File storage services
- Third-party platform APIs (Feishu message sending, GitHub issue creation)
- Compile/test execution services

### 1.3 ExternalHook

An external system acting as a Hook: proactively pushes Signals to the node mesh.

```
ExternalHook characteristics:
- Proactive push (not passive response)
- Monitors external events; injects Signal into mesh when conditions are met
- WebSocket/SSE stream (push model)
- Does not call LLM; does not modify external state
```

Typical use cases:
- CI/CD systems (push Signal on build failure)
- Monitoring alerts (push Signal when metric exceeds threshold)
- User behavior events (push Signal when user submits code)
- External data changes (database change notifications)

### 1.4 FormatProvider

An external system that provides domain Format definitions for other nodes in the mesh.

```
FormatProvider characteristics:
- Provides FormatSpec definitions (with description and examples)
- Can batch-register all Formats for a domain
- Can provide Format inheritance relationships
- HTTP endpoint (declarative, read-only)
```

Typical use cases:
- Industry standard semantic type libraries (medical HL7, financial FIBO)
- Company-internal domain Format registry
- Open-source semantic type communities

---

## 2. Registration Protocol

### 2.1 Registration Request

External primitives send a registration request to any SEP node's `/sep/v1/register` endpoint.

**Request format (HTTP POST)**:

```json
{
  "primitive_type": "node | tool | hook | format_provider",
  "identity": {
    "name": "feishu-message-analyzer",
    "description": "Analyzes semantic content of Feishu messages, extracting structured information (tasks, decisions, action items)",
    "version": "1.2.0",
    "maintainer": "team-collab@example.com"
  },
  "examples": [
    {
      "input": {
        "format": "feishu.message.raw",
        "text": "[URGENT] PR #123 needs review and merge by tomorrow"
      },
      "output": {
        "format": "task.structured",
        "text": "Task: review and merge PR #123; Deadline: tomorrow; Priority: urgent; Assignee: unspecified"
      }
    },
    {
      "input": {
        "format": "feishu.message.raw",
        "text": "Confirmed: this sprint focuses on login flow optimization, other requirements deferred"
      },
      "output": {
        "format": "decision.structured",
        "text": "Decision: sprint scope = login flow optimization; deferred requirements = all others; decision-maker = unknown"
      }
    }
  ],
  "endpoint": {
    "url": "https://feishu-analyzer.internal/sep/process",
    "transport": "http",
    "timeout_seconds": 30,
    "streaming": false
  },
  "visibility": ["public", "internal"],
  "capabilities": {
    "max_signal_length": 8000,
    "languages": ["zh", "en"],
    "llm_powered": true
  }
}
```

**Note**: No required JSON Schema; no OpenAPI specification required. Examples are the contract.

### 2.2 Registration Response

```json
{
  "status": "registered",
  "node_id": "ext.feishu-message-analyzer.01KM...",
  "inferred_formats": {
    "input": ["feishu.message.raw", "feishu.message.*"],
    "output": ["task.structured", "decision.structured"]
  },
  "semantic_summary": "Analyzes Feishu message content, extracting tasks, decisions, action items as structured semantics",
  "mesh_nodes": ["node.local:7890", "node.peer1:7891"],
  "registered_at": "2026-03-28T10:00:00Z",
  "expires_at": "2026-04-28T10:00:00Z",
  "heartbeat_interval_seconds": 300
}
```

- `node_id` is this external primitive's globally unique identifier in the semantic mesh
- `inferred_formats` is the Format inferred by the system from examples (not a hard constraint — used as routing reference)
- Registration validity: 30 days by default; renewed via heartbeat

### 2.3 Registration Lifecycle

```
Registration request → Semantic inference (LLM analyzes examples) → Node mesh registration
    ↓
Periodic heartbeat (POST /sep/v1/heartbeat every N minutes)
    ↓
Heartbeat timeout → Node marked inactive (not deleted; history preserved)
    ↓
Re-registration → Restored to active (node_id unchanged)
```

---

## 3. Discovery Protocol

### 3.1 Intent Query (Semantic Discovery)

Callers do not look up nodes by name — they query by **semantic intent**:

**Request (HTTP GET /sep/v1/discover)**:

```json
{
  "intent": "Analyze a natural language text and extract tasks and action items it contains",
  "input_format_hint": "feishu.message.*",
  "output_format_hint": "task.*",
  "visibility_required": "internal",
  "min_confidence": 0.6
}
```

**Response**:

```json
{
  "candidates": [
    {
      "node_id": "ext.feishu-message-analyzer.01KM...",
      "name": "feishu-message-analyzer",
      "semantic_similarity": 0.92,
      "inferred_input_formats": ["feishu.message.raw"],
      "inferred_output_formats": ["task.structured"],
      "description": "Analyzes Feishu message content, extracting tasks, decisions, action items as structured semantics",
      "endpoint_url": "https://feishu-analyzer.internal/sep/process",
      "last_seen": "2026-03-28T09:55:00Z"
    },
    {
      "node_id": "sed.task_extractor.01KM...",
      "name": "sed.task_extractor (local sedimented node)",
      "semantic_similarity": 0.78,
      "description": "Task extraction node sedimented from agent execution traces",
      "endpoint_url": "local://sed.task_extractor"
    }
  ]
}
```

Discovery is **semantic matching**, not name lookup. No exact Format ID match is required.

### 3.2 Format Query

Query the definition and examples of a Format (for understanding and compatibility assessment):

```
GET /sep/v1/formats/{format_id}
GET /sep/v1/formats?query=feishu+message&domain=collaboration
```

---

## 4. Signal Exchange Protocol

### 4.1 Signal Envelope

All SEP messages are wrapped in LAP V0.4's **Message Envelope**. SEP adds a `sep_metadata` field:

```json
{
  "lap_version": "0.4",
  "envelope_id": "01KM...",
  "task_id": "01KM...",
  "origin": {
    "kind": "external_node",
    "identity": "node:sed.routing_gap_judge"
  },
  "signal": {
    "format": "feishu.message.raw",
    "text": "[URGENT] PR #123 needs review and merge by tomorrow",
    "node_id": "sed.routing_gap_judge",
    "meta": {
      "source_channel": "feishu_group_12345",
      "message_id": "om:abc123"
    }
  },
  "visibility": "internal",
  "sep_metadata": {
    "target_node_id": "ext.feishu-message-analyzer.01KM...",
    "routing_confidence": 0.92,
    "fallback_node_ids": ["sed.task_extractor.01KM..."],
    "timeout_seconds": 30,
    "require_state_anchor": false
  }
}
```

### 4.2 External Node Response Format

External nodes return the same envelope format; the `signal` field contains the processing result:

```json
{
  "lap_version": "0.4",
  "envelope_id": "01KM...(new ID)",
  "task_id": "01KM...(same task_id)",
  "origin": {
    "kind": "external_node",
    "identity": "node:ext.feishu-message-analyzer"
  },
  "signal": {
    "format": "task.structured",
    "text": "Task: review and merge PR #123; Deadline: tomorrow; Priority: urgent; Assignee: unspecified",
    "node_id": "ext.feishu-message-analyzer.01KM...",
    "meta": {
      "confidence": 0.95,
      "extracted_items": 1,
      "source_message_id": "om:abc123"
    }
  },
  "state_anchor": null,
  "visibility": "internal"
}
```

### 4.3 The Format Tolerance Principle

External nodes **must** implement format tolerance:

```
Format tolerance = do not reject a request when the Signal's semantics are understandable,
even if the format ID does not precisely match

Specifically:
- When receiving Signal.format="feishu.message.thread", if the node's description
  covers Feishu messages, attempt to process it
- Must NOT return "format not supported" error solely because the format ID string
  does not exactly match
- May indicate in the response "processed as feishu.message.raw, confidence 0.80"
```

Format tolerance is the core difference between SEP and traditional APIs: semantic understanding determines whether to process; format tags are a reference, not a gate.

---

## 5. Format Negotiation

### 5.1 Automatic Negotiation Flow

When the router sends a Signal to an external node but the output Format does not precisely match the target Format:

```
Step 1: Semantic similarity check
  router.semantic_similarity(
    source_format="task.structured",
    target_format="task.action_item"
  ) → 0.85

Step 2: If similarity > threshold (default 0.70)
  Automatically insert LLM Transformer Node
  Transformer receives Signal(format="task.structured", text=...)
  Transformer produces Signal(format="task.action_item", text=...)

Step 3: If similarity < threshold
  Return Signal(format="routing.gap",
    text="Cannot find semantic bridge between task.structured and task.action_item")
  Triggers RoutingGapJudgeNode → may create a new specialized node
```

### 5.2 Manual Format Declaration

External nodes can proactively declare the actual produced Format in the response (if different from requested):

```json
{
  "signal": {
    "format": "task.structured",
    "text": "...",
    "meta": {
      "intended_format": "task.structured",
      "actual_format_note": "Best effort to match task.action_item semantics, but more accurately labeled as task.structured"
    }
  }
}
```

The router will use this declaration for subsequent format inference learning.

### 5.3 Format Example Exchange

When two nodes first connect, they can exchange each other's Format examples to better understand each other's semantic boundaries:

```
GET /sep/v1/formats/examples?node_id=ext.feishu-message-analyzer.01KM...

Returns all input/output example pairs this node provided during registration
```

---

## 6. Hook Subscription Protocol

### 6.1 ExternalHook Registration

ExternalHook establishes a persistent connection to the SEP node's `/sep/v1/hook/subscribe` endpoint via WebSocket:

```json
POST /sep/v1/hook/register
{
  "primitive_type": "hook",
  "hook_type": "event",
  "identity": {
    "name": "ci-failure-hook",
    "description": "Monitors CI/CD pipelines; emits Signal on build or test failure"
  },
  "signal_formats": ["ci.build.failed", "ci.test.failed"],
  "examples": [
    {
      "event": "build_failed",
      "output_signal": {
        "format": "ci.build.failed",
        "text": "Build failed: main branch, commit abc123, error: 42 TypeScript compilation errors"
      }
    }
  ],
  "push_endpoint": "wss://ci-hook.internal/sep/push",
  "visibility": "internal"
}
```

### 6.2 Signal Push

ExternalHook pushes envelopes to the SEP node when events occur; no response is awaited:

```
WebSocket message (ExternalHook → SEP node):
{
  "envelope_id": "01KM...",
  "signal": {
    "format": "ci.build.failed",
    "text": "Build failed: main branch, commit abc123, 42 TypeScript compilation errors",
    "node_id": "ext.ci-failure-hook"
  },
  "visibility": "internal"
}
```

Upon receipt, the SEP node injects the Signal into the semantic mesh for consumption by ConsciousnessNodes subscribed to this Format.

### 6.3 Trigger Condition Declaration

ExternalHook may declare trigger conditions (for router filtering) to reduce unnecessary Signal propagation:

```json
"trigger_conditions": {
  "natural_language": "Only fires on actual errors, never on success",
  "signal_frequency": "event_driven",
  "estimated_daily_signals": 50,
  "cooldown_seconds": 60
}
```

---

## 7. Trust Model

### 7.1 Trust Levels

SEP does not use traditional API Key authentication as the primary trust mechanism — because API Keys are part of the format contract, and SEP prioritizes semantic contracts. Trust is established through **capability declaration + StateAnchor verification**:

| Trust Level | Verification Method | Use Case |
|------------|--------------------|---------|
| **public** | No verification; accept directly | Public Format definition queries, discovery API |
| **internal** | Network-layer isolation (same VPC/intranet) | Intra-organization inter-node Signal exchange |
| **verified** | StateAnchor verification | Cross-organization, high-value Signal exchange |
| **reviewed** | Human confirmation per operation | Sensitive operations (writing to production DB, etc.) |

### 7.2 StateAnchor as Trust Credential

For cross-organization Signal exchange, external nodes can provide a StateAnchor to prove the authenticity of their output:

```json
"state_anchor": {
  "kind": "file_hash",
  "ref": "sha256:abc...",
  "path": "s3://company-data/analysis_result.json",
  "verified_at": "2026-03-28T10:00:00Z"
}
```

Recipients can independently verify this StateAnchor to establish trust in the Signal's content — without needing to trust the sender's identity.

### 7.3 Capability Declaration Transparency

All registered external primitives must declare:
- Whether they call LLM (`llm_powered: true/false`)
- Whether they modify external state (`has_side_effects: true/false`)
- Data retention policy (`data_retention: "none" | "session" | "persistent"`)
- Visibility support range (`visibility: ["public", "internal"]`)

These declarations are used for router risk assessment, not as technical constraints — external nodes can declare anything, but mismatch between declaration and behavior reduces trust score.

---

## 8. Distributed Node Mesh

### 8.1 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Semantic Node Mesh                      │
│                                                         │
│   ┌──────────────┐     ┌──────────────┐                 │
│   │  Local LSR   │◄────►  Peer LSR    │                 │
│   │ (Local       │     │ (remote org) │                 │
│   │ Semantic     │     └──────────────┘                 │
│   │ Router)      │              │                       │
│   └──────┬───────┘              │                       │
│          │                      ▼                       │
│   ┌──────┴──────┐      ┌──────────────┐                 │
│   │ Local nodes │      │ External     │                 │
│   │ (sed.*, evo.*) │   │ nodes (ext.*) │                │
│   └─────────────┘      └──────────────┘                 │
└─────────────────────────────────────────────────────────┘
         ▲                         ▲
         │                         │
   ┌─────┴──────┐          ┌───────┴────────┐
   │ExternalHook│          │ ExternalNode   │
   │(push Signal)│         │(receive/return │
   └────────────┘          │ Signal)        │
                           └────────────────┘
```

### 8.2 Local Semantic Router (LSR)

Every SEP-participating node runs an LSR responsible for:
- Managing locally registered primitives (local nodes + external nodes registered to this LSR)
- Receiving Intents and matching optimal nodes (local first, then querying Peers)
- Forwarding Signals to local or remote nodes
- Maintaining node health state (heartbeat monitoring)

```
LSR routing decision:
1. Receive Intent(input_format, output_format)
2. Query local semantic network (semantic_network.db)
3. If no local match, query Peer LSRs
4. Rank candidate nodes by semantic similarity
5. Send Signal to top candidate node
6. If candidate fails, try next (degraded routing)
```

### 8.3 Peer Links

LSRs discover each other via Peer links:

```json
POST /sep/v1/peer/link
{
  "peer_endpoint": "https://other-org.internal/sep",
  "peer_name": "data-team-cluster",
  "shared_visibility": ["internal"],
  "sync_formats": true
}
```

Once established:
- Both sides sync public/internal Format definitions
- Cross-peer Intent routing becomes possible
- Peer relationship is symmetric; no central node

---

## 9. Complete Examples

### Scenario: External Feishu Analysis Service Joining

**Step 1: External service registration**

```bash
curl -X POST https://local-lsr/sep/v1/register \
  -H "Content-Type: application/json" \
  -d '{
    "primitive_type": "node",
    "identity": {
      "name": "feishu-task-extractor",
      "description": "Extracts structured task information from Feishu messages"
    },
    "examples": [
      {
        "input": {"format": "feishu.message.raw", "text": "Code review needed by tomorrow"},
        "output": {"format": "task.structured", "text": "Task: code review; Deadline: tomorrow; Status: pending"}
      }
    ],
    "endpoint": {"url": "https://feishu-extractor.svc/process", "transport": "http"}
  }'
```

**Step 2: Routing within semantic mesh**

A ConsciousnessNode inside the system emits an Intent:

```python
Intent(
    text="Analyze latest Feishu messages; extract today's to-do tasks",
    input_format="feishu.message.raw",
    output_format="task.structured",
    priority=0.7
)
```

LSR queries the semantic network, finds the matching external node (similarity 0.94), sends Signal:

```json
{
  "signal": {
    "format": "feishu.message.raw",
    "text": "15 new messages received, including: tomorrow standup moved to 10:30; PR #456 needs review; new requirements doc uploaded",
    "node_id": "hook.feishu_poller"
  },
  "sep_metadata": {"target_node_id": "ext.feishu-task-extractor.01KM..."}
}
```

**Step 3: External node processes and returns**

```json
{
  "signal": {
    "format": "task.structured",
    "text": "Today's to-do (3 items): 1. Attend 10:30 standup; 2. Review PR #456; 3. Read new requirements doc; All priority: medium",
    "node_id": "ext.feishu-task-extractor.01KM...",
    "meta": {"item_count": 3, "confidence": 0.91}
  }
}
```

**Step 4: CompletionHook fires**

Signal.format="task.structured" matches Intent.output_format="task.structured"; CompletionHook fires, Intent completes, Consciousness loop closes.

---

### Scenario: Format Negotiation Bridge

Caller expects `task.action_item`; external node outputs `task.structured`:

```
Semantic similarity check:
  task.structured ↔ task.action_item → 0.82 (exceeds threshold 0.70)

Automatically insert LLM Transformer:
  Input:  Signal(format="task.structured", text="Today's to-do (3 items): ...")
  Output: Signal(format="task.action_item", text="Action items: □ 10:30 standup □ Review PR #456 □ Read requirements doc")

Routing continues without human intervention
```

---

## 10. Comparison with Traditional Protocols

| Dimension | REST/RPC | MCP (Model Context Protocol) | SEP (This Protocol) |
|-----------|---------|------------------------------|---------------------|
| Registration | OpenAPI / Protobuf Schema | Tool name + JSON Schema | Natural language description + examples |
| Discovery | Service name + endpoint URL | Exact tool name match | Semantic intent query |
| Format constraint | Mandatory (Schema mismatch = error) | Mandatory (JSON Schema) | Soft (semantically understandable = acceptable) |
| On format mismatch | Returns 4xx error | Returns error | LLM auto-bridges |
| Trust mechanism | API Key / OAuth | — | StateAnchor + capability declaration |
| State tracking | No standard | No standard | Task + Intent lifecycle |
| Push model | Webhook (fixed format) | — | ExternalHook (Signal envelope) |
| Best suited for | High-determinism, low LLM density | Tool-calling scenarios | LLM-dense, semantically variable scenarios |

**SEP vs MCP**: MCP solves "how LLMs access tools" (input side). SEP solves "how cross-machine LLM systems interoperate at the semantic layer" (semantic routing side). They are complementary, not mutually exclusive. MCP Tools can be wrapped as SEP ExternalTools to participate in the semantic mesh.

---

## Appendix A: SEP Endpoint Specification

### Endpoints LSR Must Implement

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sep/v1/register` | POST | Register external primitive |
| `/sep/v1/heartbeat` | POST | Heartbeat renewal |
| `/sep/v1/discover` | GET/POST | Semantic discovery query |
| `/sep/v1/formats/{id}` | GET | Query Format definition |
| `/sep/v1/signal` | POST | Send Signal to target node |
| `/sep/v1/hook/register` | POST | Register ExternalHook |
| `/sep/v1/hook/subscribe` | WS | ExternalHook push connection |
| `/sep/v1/peer/link` | POST | Establish Peer link |
| `/sep/v1/health` | GET | LSR health status |

### Endpoints External Node Must Implement

An ExternalNode needs only one processing endpoint (declared during registration):

```
POST {endpoint.url}
  Body: LAP V0.4 Message Envelope (with signal field)
  Response: LAP V0.4 Message Envelope (with signal field)
  HTTP Status: 200 (success) | 422 (semantically unprocessable) | 503 (node unavailable)
```

**Important**: External nodes should NOT return `400 Bad Request` (format error). Instead, return `422 Unprocessable Entity` (semantically unprocessable) with explanation in response signal.text. This embodies "semantic precision supersedes format precision."

---

## Appendix B: Minimal Viable Registration

Register a valid ExternalNode with the minimum required information:

```json
{
  "primitive_type": "node",
  "identity": {
    "name": "my-text-summarizer",
    "description": "Compresses long text into a 3–5 sentence summary"
  },
  "examples": [
    {
      "input": {"format": "text.long", "text": "(long text example...)"},
      "output": {"format": "text.summary", "text": "(summary example)"}
    }
  ],
  "endpoint": {"url": "http://localhost:8080/summarize", "transport": "http"}
}
```

Minimal registration is sufficient to participate in the semantic mesh. As usage accumulates, the system learns more precise Format inference from actual Signal interactions.

---

*Semantic Exchange Protocol (SEP) V0.1 — Six-Primitive Cross-Machine Interoperability — 2026-03-28*
