# LAP Standard Semantic Library

> **Status**: Draft
> **Purpose**: Similar to HTTP's MIME Types, this standard library defines the most common and universal `Format` (Semantic Types) and `Tags` (Semantic Facets) in the LAP protocol. It enables different Agents to reach an out-of-the-box semantic consensus.

---

## 1. Core Format Classification and Evolution

In LAP, we focus on two dimensions: **"What it is"** (Structural Inheritance) and **"How it transforms"** (Semantic Evolution). Every piece of data on the Event Bus must have a clear foundational identity.

### 1.1 Data Classification Tree (Is-A: What it is)

```text
1. Requirement (Intent Layer)
   ├── FeatureRequirement (New feature request)
   ├── BugfixRequirement  (Bug fix request)
   ├── ChatMessage        (Conversational input)
   └── Ticket             (Intent from issue trackers)

2. Spec (Blueprint Layer)
   ├── TaskSpec           (Task with validation standards)
   ├── Doc                (Human-readable documentation)
   └── APIDoc             (Machine-readable API definition)

3. Code (Implementation Layer)
   ├── CodePatch          (Code modifications/Diff)
   └── Binary             (Compiled artifact)

4. Verification (Validation Layer)
   ├── TestPlan           (Strategy for testing)
   ├── TestResult         (Execution report)
   ├── TestVerdict        (Decision from Authoritative Truths)
   └── CISignal           (Pipeline signals)

5. AgentRuntime (Runtime Layer)
   ├── AgentState         (Context in Agent's mind)
   ├── AgentAction        (Decisions, e.g., tool calls)
   └── ToolObservation    (Result from tool execution)
```

### 1.2 Semantic Evolution Path (Derives-From: How it transforms)

Data transforms via Transformers. **Note: Details might be lost during transformation**; therefore, an "Anchor" (Checkpoint) must follow to ensure the output remains faithful to the original intent.
Typical Path: `Requirement => Spec => Code => TestResult`

## 2. Fundamental Format Definitions

### 2.1 Requirement and Specification Layer
*   **`requirement`**: A stateful intent. This is the base class for all types.
*   **`spec`**: Clarifies ambiguous requirements into executable, structured blueprints.
*   **`task-spec`**: `[tags: task.input]` Contains task description + validation methods (e.g., test commands).

### 2.2 Runtime Layer (Agent Loop)
*   **`agent-state`**: Contains the Agent's current instruction, history, and context. It is the runtime representation of a requirement.
*   **`agent-action`**: A single-step decision made by the Agent (e.g., `tool_call`, `think`, `finish`).
*   **`tool-observation`**: The response from the physical world (tools) to the `agent-action`.

### 2.3 Artifact Layer
*   **`code`**: The executable implementation of an intent (source code, configuration).
*   **`code-patch`**: `[tags: task.output]` A collection of modifications made by the Agent (e.g., a diff).
*   **`test-result`**: A report containing passed/failed/skipped states.

## 3. Standard Semantic Tags Reference

In LAP V0.2, Tags define unstructured semantic facets that cross-cut the classification tree.

### 3.1 Domain & Language
*   `domain:frontend` / `domain:backend` / `domain:database` / `domain:devops`
*   `lang:python` / `lang:typescript` / `lang:rust` / `lang:go`

### 3.2 Confidence & Authoritative Truth (Ground Truth)
*   `ground-truth.hard`: Absolute reality. Confidence is always 1.0 (e.g., compiler success, Pytest success).
*   `ground-truth.human`: Human review passed.
*   `validation.syntax`: Initial syntax check passed, but logic not yet verified.
*   `validation.security`: Security scan passed.

### 3.3 Evolution & Self-Healing (Evolution Engine)
*   `evolution.residual`: Marked as "Residual"—data that is self-consistent but rejected by reality, triggering system evolution.
*   `evolution.attribution`: Semantic attribution, indicating if a failure was due to over-generation (MORE), omission (LESS), or logical error (WRONG).

---

*As the protocol evolves, this standard library will be continuously expanded through community proposals.*
