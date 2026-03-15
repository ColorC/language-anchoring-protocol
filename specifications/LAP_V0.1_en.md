
## 5. Protocol Execution

### 5.1 Static Phase: Pipeline Construction

```text
1. User/System declares a set of Anchors and Transformers
2. Declare the connections (edges) between them
3. Type checker verifies the type compatibility of each edge:
   - Compatible → Pass
   - Incompatible but convertible → Automatically insert Transformer
   - Incompatible and unconvertible → Throw Error
4. Output: Type-safe Pipeline definition
```

### 5.2 Dynamic Phase: Pipeline Execution

```text
1. Input data enters from the entry node, carrying a Format type tag
2. Current node (Anchor) executes:
   a. Verify if input matches format_in (Hard check)
   b. Call Validator to judge
   c. Yield Verdict (PASS / FAIL / PARTIAL)
3. Look up routing table based on Verdict:
   - PASS  → Advance to next node (or EMIT to exit)
   - FAIL  → Handle according to route (RETRY / JUMP / HALT)
   - PARTIAL → Continue or branch
4. If the next node requires a type conversion, pass through a Transformer
5. Repeat until Pipeline reaches exit (EMIT) or terminates (HALT)
```

### 5.3 Runtime Events

Every step during Pipeline execution generates an event (aligned with OmniFactory`s FactoryEvent):

```text
ANCHOR_ENTER     — Entering an anchor
ANCHOR_VERDICT   — Anchor yields a judgment
ANCHOR_ROUTE     — Routing decision made
TRANSFORM_BEGIN  — Type conversion begins
TRANSFORM_END    — Type conversion completes
PIPELINE_EMIT    — Pipeline emits final result
PIPELINE_HALT    — Pipeline terminates abnormally
```

### 5.4 Example: Two-Anchor Agent Loop

Describing a standard Agent loop (what all current Agent frameworks do) using LAP:

```yaml
pipeline:
  id: "agent-loop"
  name: "Standard Agent Loop"
  entry: "anchor-llm"

  formats:
    - id: "run-state"
      name: "AgentRunState"
      description: "Unfinished requirement + history of action observations"
      parent: "requirement"

    - id: "action"
      name: "AgentAction"
      description: "LLM`s decision output (tool_call / think / finish)"
      parent: "requirement"

    - id: "observation"
      name: "ToolObservation"
      description: "Observation results after tool execution"
      parent: "requirement"

  anchors:
    - id: "anchor-llm"
      name: "LLM Decision (Soft)"
      format_in: "run-state"
      format_out: "action"
      validator:
        kind: SOFT
        description: "LLM decides the next action based on current state"
      routes:
        PASS:    { action: EMIT }              # finish/reject → Exit
        PARTIAL: { action: NEXT, target: self } # think → Record, re-enter
        FAIL:    { action: NEXT, target: "anchor-tool" } # tool_call → Needs hard anchor

    - id: "anchor-tool"
      name: "Tool Execution (Hard)"
      format_in: "action"
      format_out: "observation"
      validator:
        kind: HARD
        description: "Verify tool call validity, execute tool, return result"
      routes:
        PASS: { action: JUMP, target: "anchor-llm" }  # Success → Back to LLM
        FAIL: { action: JUMP, target: "anchor-llm" }  # Failure → Also back to LLM (with diagnosis)

  transformers:
    - id: "obs-to-state"
      from_format: "observation"
      to_format: "run-state"
      method: RULE
      description: "Append observation results to AgentRunState.history"
```

Notice that both PASS and FAIL for `anchor-tool` route back to `anchor-llm`—because whether the tool succeeds or fails, the LLM needs to see the result and make the next decision. **The difference lies in the diagnosis carried by the Verdict: when successful, it is the observation result; when failed, it is the error message.**

---

## 6. Translating Existing Systems to LAP

### 6.1 ChatGPT Conversation = Single-Anchor Pipeline

```yaml
pipeline:
  id: "chatgpt"
  entry: "anchor-human"

  anchors:
    - id: "anchor-human"
      format_in: "llm-response"
      format_out: "validated-response"
      validator:
        kind: SOFT
        description: "Human reads and judges if the LLM response is satisfactory"
      routes:
        PASS: { action: EMIT }
        FAIL: { action: RETRY, feedback: "User`s correction instruction" }
```

One anchor, one human. The most primitive LAP instance.

### 6.2 OpenAI Function Calling = Two-Anchor Pipeline

```yaml
pipeline:
  id: "function-calling"
  entry: "anchor-llm"

  anchors:
    - id: "anchor-llm"
      format_in: "conversation"
      format_out: "function-call-or-text"
      validator: { kind: SOFT, description: "LLM decides whether to call a function" }
      routes:
        PASS: { action: EMIT }                           # Pure text reply
        FAIL: { action: NEXT, target: "anchor-schema" }  # Function call

    - id: "anchor-schema"
      format_in: "function-call"
      format_out: "validated-call"
      validator: { kind: HARD, description: "JSON Schema validates function parameters" }
      routes:
        PASS: { action: EMIT }    # Parameters valid → Execute
        FAIL: { action: RETRY }   # Parameters invalid → Resample
```

### 6.3 SWE-Agent (Code Repair) = Multi-Anchor Pipeline

```yaml
pipeline:
  id: "swe-agent"
  entry: "anchor-planner"

  anchors:
    - id: "anchor-planner"
      format_in: "issue"              # GitHub Issue (Ticket <: Requirement)
      format_out: "action"
      validator: { kind: SOFT, description: "LLM plans repair strategy" }
      routes:
        PASS:    { action: NEXT, target: "anchor-submit" }
        FAIL:    { action: NEXT, target: "anchor-tool" }
        PARTIAL: { action: NEXT, target: self }

    - id: "anchor-tool"
      format_in: "action"
      format_out: "observation"
      validator: { kind: HARD, description: "Execute bash/edit commands" }
      routes:
        PASS: { action: JUMP, target: "anchor-planner" }
        FAIL: { action: JUMP, target: "anchor-planner" }

    - id: "anchor-submit"
      format_in: "code-patch"
      format_out: "pr"
      validator: { kind: HARD, description: "git diff format validation + submit PR" }
      routes:
        PASS: { action: NEXT, target: "anchor-ci" }
        FAIL: { action: JUMP, target: "anchor-planner" }

    - id: "anchor-ci"
      format_in: "pr"
      format_out: "test-result"
      validator: { kind: HARD, description: "CI runs test suite" }
      routes:
        PASS: { action: EMIT }                           # Tests pass → Complete
        FAIL: { action: JUMP, target: "anchor-planner" } # Tests fail → Back to LLM

  transformers:
    - id: "issue-to-context"
      from_format: "issue"
      to_format: "run-state"
      method: LLM
      description: "Parse Issue, extract reproduction steps and code locations"
```

Notice that SWE-Agent has two more hard anchors (git + CI) than a basic Agent. **For every additional hard anchor, the reliability of the system ascends to a new level.**

### 6.4 Guardrails AI = Validator Chain

```yaml
pipeline:
  id: "guardrails"
  entry: "anchor-format"

  anchors:
    - id: "anchor-format"
      format_in: "llm-output"
      format_out: "parsed-output"
      validator: { kind: HARD, description: "JSON parsing + Schema validation" }
      routes:
        PASS: { action: NEXT, target: "anchor-toxicity" }
        FAIL: { action: RETRY, feedback: "schema error message" }

    - id: "anchor-toxicity"
      format_in: "parsed-output"
      format_out: "safe-output"
      validator: { kind: SOFT, description: "Toxicity detection (LLM-as-judge)" }
      routes:
        PASS: { action: NEXT, target: "anchor-factuality" }
        FAIL: { action: RETRY, feedback: "Content contains inappropriate statements" }

    - id: "anchor-factuality"
      format_in: "safe-output"
      format_out: "verified-output"
      validator: { kind: SOFT, description: "Factuality verification (RAG retrieval)" }
      routes:
        PASS: { action: EMIT }
        FAIL: { action: RETRY, feedback: "The following claims could not be verified: ..." }
```

Guardrails AI`s validator chain = a **serial multi-anchor pipeline** in LAP. However, Guardrails lacks a type system, lacks Transformers, and lacks the ability to route to different branches.

### 6.5 CI/CD Pipeline = Pure Hard Anchor Pipeline

```yaml
pipeline:
  id: "cicd"
  entry: "anchor-build"

  anchors:
    - id: "anchor-build"
      format_in: "code"
      format_out: "binary"
      validator: { kind: HARD, description: "Compiler" }
      routes:
        PASS: { action: NEXT, target: "anchor-test" }
        FAIL: { action: HALT, feedback: "Compilation error" }

    - id: "anchor-test"
      format_in: "binary"
      format_out: "test-result"
      validator: { kind: HARD, description: "Test suite" }
      routes:
        PASS: { action: NEXT, target: "anchor-security" }
        FAIL: { action: HALT, feedback: "Test failed" }

    - id: "anchor-security"
      format_in: "binary"
      format_out: "security-report"
      validator: { kind: HARD, description: "Security scan" }
      routes:
        PASS: { action: NEXT, target: "anchor-deploy" }
        FAIL: { action: HALT, feedback: "Security vulnerability" }

    - id: "anchor-deploy"
      format_in: "binary"
      format_out: "deployment"
      validator: { kind: HARD, description: "Deployment health check" }
      routes:
        PASS: { action: EMIT }
        FAIL: { action: HALT, feedback: "Deployment failed, rollback" }
```

CI/CD is a **pure hard anchor pipeline**—there are no soft anchors whatsoever. This is the anchoring pipeline humans built before LLMs existed. LAP`s contribution is allowing soft anchors (LLMs) to naturally insert into any position of this pipeline.

---

## 7. Vision

### 7.1 Short-term: Protocol Foundation for OmniFactory

LAP provides OmniFactory with:
- Formalized description of the Agent step loop (two-anchor pipeline)
- Type-safe composition for multi-Agent collaboration
- A unified event model for pipeline observability
- Natural mounting points for shadow interventions (inserting an Intervention Anchor between any two Anchors)

### 7.2 Mid-term: The Dual Protocol of MCP

```text
MCP = Input side standardization (How LLMs access external capabilities)
LAP = Output side standardization (How LLM artifacts are verified and routed)
```

MCP answers: "What tools can the LLM use?"
LAP answers: "How should the LLM`s output be validated?"

The two are complementary, covering the complete surface area of LLM interactions with the external world.

### 7.3 Long-term: Large Language Programming Model

LAP is not just a protocol—it is a **Programming Paradigm**:

- **Format is a type**: Describes the semantics of the data.
- **Anchor is a function**: Receives a type, produces a type, carries validation logic.
- **Transformer is a type conversion**: LLM-driven semantic conversion.
- **Pipeline is a program**: Type-safe function composition.
- **Type Checking is a compiler**: Catches errors during pipeline construction.

Under this paradigm:
- "Programming" = Declaring Transformers between Formats
- "Testing" = Adding hard anchors into the pipeline
- "Debugging" = Checking which Anchor`s Verdict in the pipeline did not meet expectations
- "Refactoring" = Reorganizing the connections between Anchors and Transformers
- "Requirement Analysis" = Defining the entry Format and exit Format

**The user only needs to declare "from this type to that type", and the system automatically infers what Transformers and Anchors are needed in between—this is the true form of Natural Language Programming.**

---

## 8. Metrics to be Validated

LAP V0.1 is a theoretical framework. Before entering V0.2, its validity must be verified through the following experiments:

### 8.1 Primitive Completeness

**Question**: Are the five primitives (Format, Verdict, Anchor, Transformer, Pipeline) sufficient to describe all known LLM anchoring scenarios?

**Validation Method**: Attempt to describe the following scenarios using LAP and check for inexpressible cases:

| Scenario | Complexity | Validation Focus |
|----------|------------|------------------|
| JSON Structured Output | Lowest | Single anchor hard judgment |
| ChatGPT + Human Review | Low | Single anchor soft judgment + RETRY route |
| ReAct Agent | Medium | Two-anchor loop |
| SWE-Agent + CI | High | Multi-anchor + Multi-Transformer |
| Multi-Agent Collab | Highest | Pipeline nesting, type inference |

**Pass Standard**: All scenarios are describable, and the description is more precise than natural language and more concise than code.

### 8.2 Type System Validity

**Question**: Can type checking catch real configuration errors during pipeline construction?

**Validation Method**:
1. Intentionally construct a type-unsafe pipeline (e.g., connect TestResult directly to Coder).
2. Check if the type checker throws an error.
3. Check if the error message is instructive ("Need to insert Transformer: TestResult → Spec").

**Pass Standard**: 100% of type errors are caught; 0% of valid pipelines are falsely reported.

### 8.3 Transformer Feasibility

**Question**: What are the success rates and costs of LLM-driven type conversions in practice?

**Validation Method**: Benchmark the following Transformers:

| Transformer | Target Success Rate | Cost Constraint |
|-------------|---------------------|-----------------|
| ChatMessage → Spec | > 80% | < $0.01/call |
| Spec → Code | > 60% | < $0.10/call |
| Code → TestPlan | > 70% | < $0.05/call |
| Code → Doc | > 90% | < $0.02/call |

**Pass Standard**: Single-call success rate of core Transformers > 60%; > 90% when combined with RETRY routing.

### 8.4 Protocol Overhead

**Question**: Do LAP type checking and event emissions introduce unacceptable runtime overhead?

**Validation Method**: Compare execution time of an Agent loop with and without LAP.

**Pass Standard**: LAP overhead < 1% of total execution time (since LLM calls take seconds, while LAP operations take microseconds).

### 8.5 Readability

**Question**: Is a LAP pipeline definition easier to understand than equivalent code/configuration?

**Validation Method**: Have engineers unfamiliar with LAP read:
1. Python code of an Agent loop
2. Equivalent LAP Pipeline YAML definition

Ask them to answer: "Under what conditions will this pipeline fail?"

**Pass Standard**: The accuracy rate of the LAP group > Code group.

### 8.6 Interoperability with Existing Ecosystems

**Question**: Can LAP serve as a "description layer" over existing tools without requiring them to be rewritten?

**Validation Method**: Write LAP adapters for the following existing tools:
- Guardrails AI → LAP Anchor
- DSPy Module → LAP Anchor
- MCP Tool → LAP Anchor (format_in = tool params, validator = tool execution)
- pytest → LAP Anchor (format_in = code, validator = test suite)

**Pass Standard**: Adapter code < 50 lines; no modification to original tool code.

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Anchor** | The atomic execution unit of LAP. `(Format_in, Validator, Routes) → Format_out`. Anchors probabilistic outputs into deterministic artifacts. |
| **Format** | The semantic type of data flowing through the pipeline. Describes not only structure, but semantics ("what is this"). |
| **Verdict** | The output of a Validator. `PASS / FAIL / PARTIAL` + diagnostic information. |
| **Validator** | The component executing the anchoring judgment. Divided into Hard (deterministic) and Soft (probabilistic). |
| **Route** | The mapping from a judgment result to the next action. `NEXT / RETRY / JUMP / EMIT / HALT`. |
| **Transformer** | Type converter between Formats. Typically LLM-driven. A special form of soft anchoring. |
| **Pipeline** | A directed, type-safe composition of Anchors and Transformers. The "program" of LAP. |
| **Hard Anchoring** | Deterministic judgment. Compilers, JSON Schema, test suites. Provable. |
| **Soft Anchoring** | Probabilistic judgment. LLM-as-judge, human review. Unprovable. |
| **Semantic Inheritance** | The subtype relationship between Formats. Code <: Spec <: Requirement. Subtypes maintain the intent semantics of the parent type but change the expression structure. |

## Appendix B: Relationship with Existing Protocols

```text
              ┌──────────────────────────────────────────┐
              │          Application Layer                │
              │  Agent / Code Gen / Chat / Automation     │
              ├──────────────────────────────────────────┤
              │    LAP (Language Anchoring Protocol)      │  ← This Protocol
              │    Output Verification + Type-Safe Route  │
              ├──────────────────────────────────────────┤
              │    MCP (Model Context Protocol)           │
              │    Input Standardization (Tool/Resource)  │
              ├──────────────────────────────────────────┤
              │    LLM API (OpenAI / Anthropic / ...)    │
              │    Model Inference Interface              │
              ├──────────────────────────────────────────┤
              │    Transport Layer (HTTP / WebSocket)     │
              └──────────────────────────────────────────┘
```

---

*LAP V0.1 — 2026-03-14 — Draft*
