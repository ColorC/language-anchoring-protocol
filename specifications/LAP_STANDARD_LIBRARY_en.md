# LAP Standard Semantic Library

> **Status**: Draft
> **Purpose**: Similar to HTTP's MIME Types, this standard library defines the most common and universal `Format` (Semantic Types) and `Tags` (Semantic Facets) in the LAP protocol. It enables different Agents to reach an out-of-the-box semantic consensus.

---

## 1. Core Format Classification and Flow

In LAP, we strictly distinguish between "Structural Inheritance (Is-A)" and "Semantic Derivation (Derives-From)". All data flowing across the Event Bus belongs to a base class and transitions across classes via Transformers.

### 1.1 Structural Inheritance Tree (Is-A)

```text
1. Requirement (Base Intent)
   ├── FeatureRequirement (Feature addition)
   ├── BugfixRequirement  (Bug fix)
   ├── ChatMessage        (Conversational intent)
   └── Ticket             (Issue tracker intent)

2. Spec (Structured Specification)
   ├── TaskSpec           (Task spec with validation)
   ├── Doc                (Human-readable document)
   └── APIDoc             (Machine-readable API spec)

3. Code (Executable Logic)
   ├── CodePatch          (Code patch / Diff)
   └── Binary             (Compiled artifact)

4. Verification (Validation & Reports)
   ├── TestPlan           (Testing strategy)
   ├── TestResult         (Test execution report)
   ├── TestVerdict        (External hard-anchored Ground Truth)
   └── CISignal           (CI/CD signal)

5. AgentRuntime (Agent State Base)
   ├── AgentState         (Context / History)
   ├── AgentAction        (Decision / Tool Call)
   └── ToolObservation    (Tool feedback)
```

### 1.2 Semantic Derivation Path (Derives-From)

Pipelines define state transitions via Transformers (which entail potential semantic loss, requiring verification via the `semantic.faithful` tag later):
`Requirement => Spec => Code => TestResult`

## 2. Fundamental Format Definitions

### 2.1 Requirement and Specification Layer
*   **`requirement`**: A stateful intent. This is the base class for all types.
*   **`spec`**: Clarifies ambiguous requirements into executable, structured specifications.
*   **`task-spec`**: `[tags: task.input]` Contains task description + validation methods (e.g., test commands). Typically used for Benchmarks or deterministic task distribution.

### 2.2 Runtime Layer (Agent Loop)
*   **`agent-state`**: Contains the Agent's current instruction, history, and context. It is the runtime representation of a requirement.
*   **`agent-action`**: A single-step decision made by the Agent based on the state (e.g., `tool_call`, `think`, `finish`).
*   **`tool-observation`**: The physical world's (tool's) response to the `agent-action`.

### 2.3 Artifact Layer
*   **`code`**: The executable implementation of an intent (source code, configuration).
*   **`code-patch`**: `[tags: task.output]` A collection of modifications made by the Agent to a repository (e.g., a diff).
*   **`test-result`**: A report containing passed/failed/skipped states.

## 3. Standard Semantic Tags Reference

In LAP V0.2, Tags are used to define unstructured semantic facets that cross-cut the inheritance tree.

### 3.1 Domain & Language
*   `domain:frontend` / `domain:backend` / `domain:database` / `domain:devops`
*   `lang:python` / `lang:typescript` / `lang:rust` / `lang:go`

### 3.2 Confidence & Ground Truth
*   `ground-truth.hard`: Absolute physical truth. Confidence is always deemed 1.0 (e.g., compiler passes, external Pytest passes).
*   `ground-truth.human`: Human review passed.
*   `validation.syntax`: Passed initial syntax validation, but not yet logically validated.
*   `validation.security`: Passed code security scanning.

### 3.3 Semantic Fidelity

*   `semantic.faithful`: **Semantic Lossless / Faithful**. Indicates that this data (e.g., Code) has been verified by an Anchor to perfectly and faithfully implement the intent of its upstream source (e.g., a Requirement). No unprompted additions, no omissions. This is the ultimate tag to defend against LLM hallucinations or "outputting the same generic code regardless of input."

### 3.4 Evolution & Self-Healing (Evolution Engine)
*   `evolution.residual`: Marked as a "Residual"—data that is self-consistent within the pipeline but rejected by the physical world, triggering system evolution.
*   `evolution.attribution`: Semantic attribution result, indicating whether a failure was due to over-generation (MORE), omission (LESS), or logical error (WRONG).

---

*As the protocol evolves, this standard library will be continuously expanded through community proposals.*