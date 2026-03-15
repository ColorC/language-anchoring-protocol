
# Language Anchoring Protocol (LAP) — V0.2 Specification

> **Status**: Draft / V0.2
> **Date**: 2026-03-15
> **Author**: LAP Protocol Authors
> **Project**: OmniFactory
> **Changes**: Added Semantic Tag System (inherent properties), Three-Layer Information Mechanism, Unverified Inputs & Entry Guards, Confidence three-state semantics, Necessary Condition Verification Methodology, and Format Type Precision on top of V0.1.

---

## Table of Contents

1. [The Core Problem](#1-the-core-problem)
2. [Core Discoveries](#2-core-discoveries)
3. [Protocol Primitives](#3-protocol-primitives)
4. [Type System](#4-type-system)
5. [Semantic Tag System](#5-semantic-tag-system) *(New in V0.2)*
6. [Unverified Inputs and Entry Guards](#6-unverified-inputs-and-entry-guards) *(New in V0.2)*
7. [Protocol Execution](#7-protocol-execution)
8. [Translating Existing Systems to LAP](#8-translating-existing-systems-to-lap)
9. [Best Practices](#9-best-practices) *(New in V0.2)*
10. [Ground Truth Surface](#10-ground-truth-surface) *(New in V0.2)*
11. [Vision](#11-vision)
12. [Metrics to be Validated](#12-metrics-to-be-validated)

---

## 1. The Core Problem

### 1.1 The Root Issue

What does the "L" in LLM (Large Language Model) stand for? **Language**.

The essence of an LLM is a probabilistic language generator—given an input sequence, it outputs a probability distribution for the next token. It does not guarantee that the output will be correct, usable, or safe.

Yet, we have built an entire industry around LLMs: code generation, conversational systems, autonomous Agents, content creation... **Everything these applications do fundamentally boils down to one thing—anchoring probabilistic outputs into deterministic, reliable artifacts.**

- Structured Output (JSON mode) is anchoring—constraining the token sampling space.
- Tool Use / Function Calling is anchoring—constraining output to valid function calls.
- Compilers are anchoring—verifying syntax and type correctness.
- Test suites are anchoring—verifying behavioral correctness.
- Human review is anchoring—verifying the artifact meets business intent.
- CI/CD Pipelines are anchoring—verifying the artifact meets deployment conditions.

**They are all different instantiations of the exact same action. But no one has named this action, and no one has defined a protocol for it.**

### 1.2 The Fragmentation of Existing Tools

| Tool | Layer of Anchoring | Limitations |
|------|--------------------|-------------|
| Outlines / SGLang | Token-level syntax constraints | Only handles structure, not semantics; requires logit access |
| Instructor / Pydantic | JSON schema validation + retries | Only single-layer validation; no chained verdicts |
| Guardrails AI | Composable validator chains | Python binding; a library, not a protocol |
| DSPy | Signatures + assertions + auto-optimization | Academic focus; assertions are boolean |
| NeMo Guardrails | Dialogue behavioral policies | Limited strictly to conversational scenarios |

**Each tool solves one fragmented piece. No one has defined a unified protocol layer.**

This is like before HTTP existed, when every company used its own method to transfer documents over a network.
This is like before LSP existed, when every editor used its own method to communicate with language tools.
This is like before MCP existed, when every Agent framework used its own method to access tools.

**MCP standardized the input side (how LLMs access tools). The output side (how LLM artifacts are verified and routed) remains a void.**

LAP fills this void.

### 1.3 Direct Trigger

While building OmniFactory (an AI-native software factory), we needed multiple Agents to collaborate on software engineering tasks over an event bus. Every decision step of every Agent needed to be observed, verified, and potentially intervened upon. We discovered: An Agent`s step loop is fundamentally the alternation of two anchors—an LLM decision (Soft Anchor) and Tool execution (Hard Anchor). This discovery, starting from a specific scenario, gradually abstracted into a universal protocol.

---

## 2. Core Discoveries

### 2.1 Discovery 1: The Atomic Structure of Anchoring

All anchoring operations can be decomposed into a binary structure:

```text
Anchor = (Format, Validator → Verdict → Route)
```

- **Format**: Defines the input structure of the validator—"what shape of thing should the LLM output."
- **Validator**: Judges whether the output passes—"does this output meet the constraints."
- **Route**: Decides the next step based on the verdict—"where to go if it passes, where to go if it fails."

This is the indivisible atomic unit. Any smaller subdivision will lose the complete semantics of anchoring.

### 2.2 Discovery 2: Agent Systems are an Anchor Counting Problem

The reliability of an Agent system is fundamentally determined by **the quantity and quality of anchors**:

```text
0 Anchors = Naked LLM Output     — Purely probabilistic, unreliable
1 Anchor  = Human Check          — Reliable but unscalable
2 Anchors = Agent Loop           — Minimum autonomous unit
N Anchors = Production Pipeline  — Approaching determinism
```

**Two anchors constitute the minimum autonomous unit**—fewer than two anchors cannot form an autonomous loop:

```text
┌──────────────────┐          ┌──────────────────┐
│   Anchor_LLM     │          │   Anchor_Tool    │
│   (Soft Anchor)  │ ──tool──▶│   (Hard Anchor)  │
│                  │ ◀──obs── │                  │
│ LLM judges:      │          │ Tool judges:     │
│ "What to do next"│          │ "Is call valid?" │
│                  │          │ "What is output?"│
└───────┬──────────┘          └──────────────────┘
        │ finish
        ▼
    Pipeline Exit
```

This explains why there were no true Agents before 2023: not because the models weren`t strong enough, but because function calling (the second anchor) hadn`t been standardized yet.

### 2.3 Discovery 3: Anchors can be Hard or Soft

| | Hard Anchor | Soft Anchor |
|---|---|---|
| Nature | Deterministic judgment, provable | Probabilistic judgment, unprovable |
| Examples | JSON Schema, compilers, tests | LLM-as-judge, human review |
| Guarantee | Same input always yields same result | Same input may yield different results |
| Role | Gatekeeper | Decision maker |

**The industry evolution trend = continuously replacing/augmenting soft anchors with hard anchors**:
- "The LLM thinks the code is right" (Soft) → Pytest passes (Hard)
- "The LLM thinks it is safe" (Soft) → Security scan passes (Hard)

### 2.4 Discovery 4: Format is a Semantic Type, not a Structure Definition

This is the most critical discovery.

Format is not a structural constraint like a "JSON Schema." Format carries **semantics**—it describes not "what the fields are called," but "what this thing actually is."

In an Agent loop, the data flowing through the pipeline is semantically always the exact same thing—a **Requirement**—it just changes states:

```text
Input:             Unverified requirement (raw requirement)
Output with Tool:  In-progress requirement
Output w/o Tool:   Resolved or unsolvable requirement
```

By extension, code, documentation, tests, and deployment artifacts—they are all Formats, different morphological variations of a Requirement after passing through different anchors:

```text
Requirement → Spec → Code → TestResult → Deployment
   "Intent"   "Spec" "Impl" "Test Report" "Runtime"
```

**A derivation and transition relationship exists between them.** Code is not a Requirement, but Code is an implementation derived from a Requirement. During each state transition (e.g., from requirement to code), **semantic collapse and potential loss** occurs. This means—

### 2.5 Discovery 5: This is a Type System and Flow Graph

When Format is a type and Anchor is a function, what we get is not a simple protocol—but a **Type System with clear transformation rules**:

```text
Format          = Semantic Type
Anchor          = Function with type signatures (Format_in → Format_out)
Transformer     = Type Converter (LLM-driven implicit/explicit conversion, carrying semantic loss risks)
Pipeline        = Program (Type-safe function composition)
Type Checking   = Compile-time error detection
```

**Profound Correction: Distinguishing "Inheritance" from "Derivation"**

In the original concept, it was easy to confuse "inheritance" with "flow/derivation". Under LAP`s strict definition:

*   **Inheritance (Is-A, Structural Inheritance)**: Expresses a containment relationship. For example: `PythonCode` inherits from `Code`; `ArtRequirement` inherits from `Requirement`. The subclass fully contains the semantics of the parent class.
*   **Derivation (Derives-From, Semantic Transition)**: Expresses the causal relationship within the pipeline. For example: `Code` derives from `Requirement`. `Code` **is not** a `Requirement`; it has discarded the "Why" (why do this) of the requirement and retained only the "How" (how to do this).

**TypeScript added a type system to JavaScript`s untyped chaos. LAP adds a semantic flow network based on inheritance and derivation rules to the untyped chaos of LLM pipelines.**

### 2.6 Discovery 6: Semantic Types Require Semantic Dimensions *(New in V0.2)*

V0.1`s type system only has one dimension—the inheritance chain (`Code <: Spec <: Requirement`). But semantics in reality have **multiple orthogonal dimensions**:

```text
A "code-diff" could be:
  - From Git, or from SVN             → Source dimension
  - About frontend, or backend        → Domain dimension
  - Reviewed, or unreviewed           → State dimension
  - Security-related, or perf-related → Intent dimension
```

**An inheritance chain can only express "what it is" (is-a), it cannot express "what domain it belongs to" or "what state it is in".** If we encoded all dimensions into the type name (`git-frontend-reviewed-security-code-diff`), the type system would explode.

Solution: **Semantic Tags**—introducing composable tag dimensions orthogonally to the inheritance chain.

```text
Format.id    = Structural identity (what it is)
Format.tags  = Semantic dimensions (what it belongs to, state)
(id, tags)   = The complete type identity
```

### 2.7 Discovery 7: Unverified Input is a Blind Spot for Type Safety *(New in V0.2)*

A pipeline claims to accept a `code-diff` as input. But who verified that the passed-in data is actually a `code-diff`?

In Rust, this problem has a clear answer:

```rust
// Unverified raw input — just a String
struct RawInput(String);

// Verified type — can only be constructed via validate()
struct Email(String);

impl RawInput {
    fn validate(self) -> Result<Email, ValidationError> { ... }
}

// Impossible to construct an Email directly without bypassing validation
```

**In LAP V0.1, this guarantee did not exist.** Any data could claim to be any Format, and the pipeline would believe it, until some downstream node crashed because the data did not meet expectations.

This is the biggest blind spot in type safety. V0.2 introduces the **Entry Guard** pattern to solve it.

---

## 3. Protocol Primitives

LAP consists of exactly five primitives. No more, no less.

### 3.1 Format — Semantic Type *(Enhanced in V0.2)*

```json
Format = {
    id:                       Unique identifier (Structural identity)
    name:                     Human-readable name
    description:              Natural language semantic description (the root of "Language Anchoring")
    parent:                   Parent type ID (Inheritance chain, null = root)
    schema:                   Optional structural constraints (JSON Schema)
    examples:                 Example instances

    # New in V0.2
    tags:                     List of semantic tags (Inherent semantic dimensions of this type)
    semantic_preconditions:   Preconditions to become this type (Human readable)
    required_tags:            Tags that the input data must already possess (Machine checkable)
}
```

**Format is the soul of LAP.** It answers: "What is this thing flowing through the pipeline?"

#### The Dual Identity of Format

A Format`s complete identity consists of two parts:

| Dimension | Expression | Analogy | Purpose |
|-----------|------------|---------|---------|
| Structural Identity | `id` + `parent` inheritance chain | Rust`s `struct` | "What is the structure of this thing" |
| Semantic Dimension | `tags` | Rust`s `trait` | "What semantic space does this belong to" |

For **Humans**: `id` and `name` should clearly describe the full meaning of the type.
For **Computers**: `(id, tags)` as a whole is the unique identifier, and type matching checks both dimensions.

#### Semantic Preconditions

`semantic_preconditions` describes the conditions data must satisfy to be eligible to be called this type:

```yaml
format:
  id: "reviewed-code-diff"
  parent: "code-diff"
  tags: ["reviewed"]
  semantic_preconditions:
    - "The diff has been reviewed by at least one reviewer"
    - "Review comments are attached in the review_comments field"
  required_tags: ["vcs-verified"]   # Input must first be confirmed to come from a valid VCS
```

`required_tags` is **machine-checkable**—PipelineChecker can verify at compile time whether upstream validators have granted these tags. `semantic_preconditions` is **human-readable**—guiding validator implementers on what to check.

#### Format Inheritance Tree (Strict Is-A Relationship)

```text
Requirement (Root type: "A stateful intent")
├── FeatureRequirement   "Functional requirement"
└── BugfixRequirement    "Fix requirement"

Code (Source code)
├── PythonCode           "Python source code"
└── BashScript           "Bash script"

Document (Documentation)
├── Spec                 "Structured specification"
└── APIDoc               "Machine+Human-readable interface description"
```

The transition relationship, however, is defined by Transformers in the Pipeline: `Requirement => Spec => Code`.

### 3.2 Verdict — Judgment Result *(Enhanced in V0.2)*

```json
Verdict = {
    kind:           PASS | FAIL | PARTIAL
    output:         The approved artifact (if PASS) or intermediate state (if PARTIAL)
    diagnosis:      Failure diagnostic information (if FAIL/PARTIAL)
    details:        Structured judgment details

    # New in V0.2
    confidence:     Confidence of semantic matching (0.0 ~ 1.0, optional)
    granted_tags:   List of semantic tags granted by this judgment
}
```

A Verdict is not a boolean. It carries **diagnostic information**—this is the key to the feedback loop. When a FAIL occurs, the diagnosis describes "why it failed." This information is routed back to the LLM, enabling it to self-correct in a targeted manner.

#### Judgment Result Semantics

| Kind | Meaning | Analogy |
|------|---------|---------|
| PASS | Output meets constraints, anchoring successful | Compiled successfully |
| FAIL | Output fails constraints, needs external handling | Compilation failed + error trace |
| PARTIAL | Partially meets constraints, can continue | Warning, but non-blocking |

#### V0.2: Semantic Confidence (confidence)

`confidence` quantifies the validator`s degree of certainty in semantic matching:

```text
confidence = 1.0  → Deterministic judgment (Hard Anchors are always 1.0)
confidence = 0.9  → High confidence (LLM Classifier: "This is almost certainly an API doc")
confidence = 0.5  → Doubtful (LLM: "This could be a requirement doc or a design doc")
confidence = 0.2  → Low confidence (LLM: "This doesn`t look like a requirement doc, but is barely parsable")
```

**A Hard Anchor`s confidence is always 1.0**—it either passes or fails, with no gray area.
**A Soft Anchor`s confidence reflects semantic distance**—downstream nodes can make decisions based on this (e.g., HALT if below threshold).

#### V0.2: Granted Tags (granted_tags)

`granted_tags` declares which semantic dimensions have been confirmed by this validation:

```yaml
# A validator checking "whether the input comes from a valid VCS"
verdict:
  kind: PASS
  confidence: 1.0
  granted_tags: ["vcs-verified"]   # I confirmed this data comes from a valid VCS

# A validator checking "whether the code change belongs to the frontend domain"
verdict:
  kind: PASS
  confidence: 0.85
  granted_tags: ["domain.frontend"]  # I am 85% certain this is a frontend code change
```

Tags **accumulate** in the pipeline—the more validators data passes through, the more verified semantic dimensions it carries.

### 3.3 Anchor

```json
Anchor = {
    id:          Unique identifier
    name:        Human-readable name
    format_in:   Input type (Format ID)
    format_out:  Output type (Format ID)
    validator:   Validator specification {
        kind:        HARD | SOFT
        description: Natural language description
    }
    routes: {
        PASS:    Route (Next step)
        FAIL:    Route (Failure handling)
        PARTIAL: Route (Partial handling)
    }
}
```

An Anchor is the atomic execution unit in LAP. It answers three questions:
1. **What does the input look like?** → `format_in`
2. **How is it judged?** → `validator`
3. **Where does it go after judgment?** → `routes`

Anchors have type signatures: `format_in → format_out`. This makes type checking possible.

### 3.4 Transformer — Type Converter

```json
Transformer = {
    id:          Unique identifier
    name:        Human-readable name
    from_format: Source type (Format ID)
    to_format:   Target type (Format ID)
    method:      Conversion method (LLM | RULE | HYBRID)
    description: Natural language logic description
}
```

When the output and input types of two Anchors do not match directly but a semantic transition relationship exists, a Transformer is needed to convert the type.

**The key characteristic of a Transformer: It is driven by an LLM.** Type conversions in traditional type systems (like `parseInt`) are deterministic. Type conversions in LAP are probabilistic—because semantic conversion is exactly what LLMs do best.

```text
Transformer: ChatMessage → Spec
    "User says `fix the login bug` → Structured BugSpec"
    method: LLM
    This conversion itself is a Soft Anchor.

Transformer: Spec → Code
    "Convert requirement spec into executable code"
    method: LLM
    This conversion is "Programming".

Transformer: Code → Doc
    "Convert code into documentation"
    method: LLM | RULE (Some deterministic generation via AST extraction)
    method = HYBRID.
```

**Profound insight: Programming, writing documentation, and designing tests—which are considered "creative work" in traditional software engineering—are just Transformers under the LAP framework.** They are type conversions between Formats, driven by an LLM acting as a universal conversion engine.

### 3.5 Pipeline — Type-Safe Composition *(Enhanced in V0.2)*

```json
Pipeline = {
    id:          Unique identifier
    name:        Human-readable name
    description: Pipeline purpose description
    nodes:       List of Anchors and Transformers
    edges:       Connections between nodes (must be type-safe)
    entry:       Entry node ID

    # New in V0.2
    group:       Group the pipeline belongs to (shares event space within the group)
    tags:        Pipeline-level semantic tags (automatically inherited by all events)
}
```

A Pipeline is a directed compositional graph of Anchors and Transformers—the "program" of LAP.

**The critical constraint of a Pipeline: Type Safety.** The `format_out` of the source node for every edge must be compatible with the `format_in` of the target node. Incompatible connections will be rejected at "compile time" (when the pipeline is built).

**V0.2: The Pipeline`s `tags` are automatically injected into all events.** When a pipeline emits an event, the event`s tags field will automatically contain the pipeline`s tags + the `granted_tags` accumulated as data flowed through validators. This allows Event Bus consumers to precisely filter events within specific semantic scopes.

---

## 4. Type System

### 4.1 Type Compatibility Rules

```sql
COMPATIBLE(A, B) =
    A == B                           -- Direct connection (short-circuit)
    OR A <: B                        -- A is a subtype of B, auto-upcast
    OR EXISTS Transformer(A → B)     -- Explicit conversion available
```

When `COMPATIBLE(A, B)` is false, the pipeline build fails. This is the "compiler" of LAP.

### 4.2 Subtype Relationship (<:)

The subtype relationship is determined by the Format`s inheritance chain and must follow strict semantic containment (Is-A):

```text
PythonCode <: Code
Means:
  Where Code is required, PythonCode can be passed in (PythonCode is a kind of Code)
  Where PythonCode is required, a generic Code cannot be passed in
```

This is a **covariant** subtype: a subtype can replace a parent type, but not vice versa.

### 4.3 V0.2: Tag Compatibility Rules

V0.2 adds **tag compatibility** checking on top of structural compatibility:

```sql
TAG_COMPATIBLE(data_tags, required_tags) =
    required_tags ⊆ data_tags
    -- The tags accumulated by the data must cover all tags required by the target
```

The complete type check becomes:

```sql
FULLY_COMPATIBLE(source, target) =
    COMPATIBLE(source.format_out, target.format_in)     -- Structural compatibility
    AND TAG_COMPATIBLE(accumulated_tags, target.required_tags)  -- Tag coverage
```

Tag compatibility is **path-sensitive**—it depends on what `granted_tags` the data has accumulated by the time it reaches a certain node, rather than just looking at a single edge.

### 4.4 Transformer as Semantic Conversion (Entailing Loss)

When a type undergoes a substantial state transition in the pipeline (e.g., derivation), a Transformer must be inserted:

```text
Logical conversion flow (Dependency based):
  Requirement → Spec      (Requirement Analysis)
  Spec → Code             (Programming Implementation)
  Code → TestResult       (Test Execution)
```

**Key Insight: Transformer operations are fundamentally lossy transitions.**
From `Requirement` to `Code`, the macro business context in the requirement is discarded, collapsing into concrete code logic.
This leads to the **"Semantic Customizability Paradox"** encountered when LAP deals with LLM hallucinations: If we strictly mandate "must be faithful to the input", does an Agent responsible for brainstorming and diverging count as a violator? Obviously not, because it is "faithful" to its mission of divergence.

Therefore, in advanced LAP practices, "faithfulness to the original requirement (or expected logic)" should not be downgraded to a simple `loss_error` field, but should be **unified into the evaluation system of `confidence` (semantic confidence) and become a historical constraint spanning the entire lifecycle**.

If an Agent claims to have output `Code`, it must pass an Anchor specifically comparing the "original requirement" with the "new code" (i.e., a Ground Truth check based on the source input). Without this "strong correspondence based on input", any derived artifact (even if its format is perfectly correct) is semantically questionable (e.g., the Agent might output the same preset code for any requirement to trick the format check). Only by passing this comparison will its `confidence` be maintained at a high level.

### 4.5 Type Inference

In some scenarios, the Pipeline can automatically infer which Transformers need to be inserted:

```text
User declares: ChatMessage ──▶ Deployment
System infers:
  ChatMessage ──[T1]──▶ Spec ──[T2]──▶ Code ──[A1]──▶ TestResult
       T1: ChatMessage→Spec           T2: Spec→Code      │
       (Requirement Understanding)    (Programming)      ▼
                                              Deployment ◀─[A2]
                                              A2: Code×TestResult→Deployment
                                              (Deployment)
```

**This is the true meaning of "Natural Language Programming"—it`s not about making the LLM write code, but letting the user declare the starting and ending types, while the system automatically infers the intermediate conversion chain.**

---

## 5. Semantic Tag System *(New in V0.2)*

### 5.1 Why We Need Tags

The inheritance chain answers "what this thing **is**" (is-a relationship):

```text
code-diff <: requirement    — A "code-diff" is a kind of "requirement"
```

But the inheritance chain cannot answer:
- Which system does this `code-diff` **come from**? (Git? SVN?)
- Which domain does this `code-diff` **belong to**? (Frontend? Backend? DB?)
- What has this `code-diff` **been verified for**? (Format valid? Source trusted? Domain confirmed?)

If we encoded all dimensions into the type name, the number of types would explode exponentially:

```text
# Unfeasible approach
git-frontend-reviewed-security-code-diff
svn-backend-unreviewed-performance-code-diff
svn-fullstack-reviewed-bugfix-code-diff
...
```

The Tag System uses orthogonal dimensions to solve this problem.

### 5.2 Tag Design Principles

**Dot-separated hierarchical naming**, referencing Java package naming and logger naming:

```text
source.git          — Source: Git
source.svn          — Source: SVN
domain.frontend     — Domain: Frontend
domain.backend      — Domain: Backend
domain.infra        — Domain: Infrastructure
lang.python         — Language: Python
lang.en             — Language: English
```

Dot-separated hierarchies support **prefix matching**: subscribing to `domain.*` can match all domain tags.

### 5.3 Four Relationships of Tags

```text
Narrowing:
  tags=["source.git"] → tags=["source.git", "domain.frontend"]
  More tags → more precise semantics

Widening:
  tags=["source.git", "domain.frontend"] → tags=["source.git"]
  Fewer tags → broader semantics

Composition:
  ["source.git"] ∪ ["domain.frontend"] = ["source.git", "domain.frontend"]
  Union of two orthogonal dimensions

Intersection:
  ["source.git", "domain.frontend"] ∩ ["source.git", "intent.bugfix"] = ["source.git"]
  Shared semantic dimensions
```

**Core Rule: More tags = narrower type = more precise semantics.**

This aligns with the direction of the inheritance chain: subtypes are more specific than parent types. Tags are the orthogonal complement to the inheritance chain.

### 5.4 Three-Layer Information Mechanism: Separation of Concerns

LAP V0.2 distinguishes three information-carrying mechanisms, **each with its own responsibility, non-interchangeable**:

| Mechanism | Answers | Phase | Example |
|-----------|---------|-------|---------|
| Format Chain (is-a) | What transformations has the data undergone? | Compile-time | `raw-doc → english-doc → translated-doc` |
| Tags | The **inherent semantic attributes** of the data | Compile+Runtime | `source.git`, `domain.frontend`, `lang.en` |
| Event trace | Which nodes did it pass through, and what were the results? | Runtime | `ANCHOR_VERDICT at language_guard: PASS` |

**Key distinction: Tags only store inherent attributes, not procedural traces.**

```text
Inherent attributes (Should be a Tag):
  source.git       — Data comes from Git (Attribute of the data itself)
  domain.frontend  — Belongs to frontend domain (Attribute of the data itself)
  lang.en          — Language is English (Attribute of the data itself)

Procedural traces (Should NOT be a Tag):
  context.enriched — "Has been enriched with context" → Responsibility of Format chain
                     (enriched-diff is-a code-diff already expresses this)
  refs.extracted   — "References extracted" → Responsibility of Format preconditions
  status.reviewed  — "Reviewed" → Responsibility of event trace
                     (ANCHOR_VERDICT at review_checker: PASS already records this)
```

**Why shouldn`t procedural traces be put in Tags?**

1. **Redundancy**: The Format type chain already records "what transformations data has undergone." `enriched-diff` inheriting from `code-diff` intrinsically represents history.
2. **Fragility**: Procedural tags are tightly coupled to pipeline structure. Renaming a node requires changing a batch of tags.
3. **Semantic Ambiguity**: `context.enriched` loses too much info—enriched by what context? using what method? The event trace has the complete answer.

**How is the "history" of data traced?**

```text
Question: "What processing has this translated document undergone?"

Answer (via Format type chain):
  translated-document is-a validated-document is-a raw-document
  → It is a verified and translated document.

Answer (via Event trace):
  1. format_guard: PASS (document parsable)
  2. language_guard: PASS (confirmed English)
  3. translator: PASS, confidence=None (LLM translation)
  4. quality_checker: PASS (integrity check passed)
  → Complete processing history, including the results and confidence of every step.
```

The three layers handle their own concerns; there is no need to repeat the information already carried by the Format chain and event trace in Tags.

### 5.5 Tags and the Event Bus

The tag system naturally unifies with Event Bus `subscribe` filtering:

```python
# Only consume "Frontend code changes from Git" events
bus.subscribe(
    group="frontend-team",
    consumer="reviewer-1",
    tags=["source.git", "domain.frontend"],
)
```

Matching rule: **The event`s tags must contain all the tags specified by the subscription** (AND semantics).

Tag sources have two layers, merged and injected into events:

| Source | Example | Description |
|--------|---------|-------------|
| Pipeline.tags | `["myproject.pipeline.review"]` | Pipeline-level inherent tags |
| Format.tags | `["source.git", "domain.frontend"]` | Type-level inherent tags |

When an event is emitted, tags from both layers are merged into the event`s `tags` field. Tags reflect the inherent semantic attributes of the data, not procedural traces.

### 5.6 PipelineChecker`s Tag Checking

Compile-time checks are expanded to two dimensions:

```text
For each edge (source_node → target_node):

  1. Structural Check (V0.1):
     Is source.format_out compatible with target.format_in? (is-a relationship)

  2. Tag Compatibility Check (V0.2):
     Are the tags of target.format_in a subset of (or equal to)
     the tags of source.format_out?

     If target requires tags not covered by source → Warning:
     "Node `code_analyzer` requires tags [`domain.frontend`] for input type,
      but the upstream output type`s tags do not contain this tag."
```

This is a **compile-time semantic safety check**—catching tag incompatibilities in type definitions before the pipeline actually runs.
Tags are inherent properties of Format types, not procedural traces accumulated at runtime.

---

## 6. Unverified Inputs and Entry Guards *(New in V0.2)*

### 6.1 The Problem: Implicit Semantic Assumptions

Consider a document translation pipeline:

```yaml
pipeline:
  entry: "translator"
  nodes:
    - id: "translator"
      format_in: "english-doc"
      format_out: "chinese-doc"
```

This pipeline assumes the input is an English document. But who verified this? If a French document is passed in:
- The data structure received by `translator` might be perfectly correct (it is text).
- But there is a **semantic mismatch**—it is not English.
- The translator might output a messy mix of English and French.
- Downstream nodes have no mechanism to detect this issue.

**The root cause of the bug: The pipeline trusted unverified input.**

### 6.2 Rust`s Solution: Newtype Pattern

Rust forces the distinction between "unverified" and "verified" through its type system:

```rust
// Unverified — just a string
struct RawDocument(String);

// Verified English document — can only be constructed via validate()
struct EnglishDocument(String);

impl RawDocument {
    fn validate(self) -> Result<EnglishDocument, ValidationError> {
        if detect_language(&self.0) != Language::English {
            return Err(ValidationError::WrongLanguage);
        }
        Ok(EnglishDocument(self.0))
    }
}

// Translate function only accepts EnglishDocument, not RawDocument
fn translate(doc: EnglishDocument) -> ChineseDocument { ... }
```

**`EnglishDocument` cannot be constructed without `validate()`, and the compiler enforces this.**

### 6.3 LAP`s Solution: Entry Guard Pattern

LAP V0.2 introduces the **Entry Guard** pattern—the entry node of every pipeline should be a **Type Guard**, responsible for narrowing unverified inputs into verified types.

```yaml
# Anti-pattern: Directly trusting input
pipeline:
  entry: "translator"           # Assumes input is already an English document

# Correct pattern: Entry Guard
pipeline:
  entry: "language_guard"       # First verifies the input language

  nodes:
    - id: "language_guard"
      kind: ANCHOR
      format_in: "raw-document"        # Accepts: Unverified document
      format_out: "english-document"   # Outputs: Verified English document
      validator:
        kind: HARD
        description: "Detect document language, verify it is English"
      routes:
        PASS: { action: NEXT, target: "translator" }
        FAIL: { action: HALT, feedback: "Input is not an English document" }

    - id: "translator"
      kind: ANCHOR
      format_in: "english-document"    # Requires: Verified English document
      format_out: "chinese-document"
```

**Comparison of two paths of semantic narrowing:**

```text
Path A (Wrong): raw-document ──────────────────▶ translator
                ↑ Semantic assumption is implicit, no verification

Path B (Right): raw-document ──▶ language_guard ──▶ translator
                ↑ Unverified     ↑ Explicit verify  ↑ Verified input
```

### 6.4 Layering of Entry Guards

Entry Guards can be **multi-layered**. A document processing pipeline might need step-by-step verification:

```text
raw-document                          (Unverified Input)
    │
    ▼ [format_guard]  Verify format validity
validated-document                    tags=["format.valid"]
    │
    ▼ [language_guard]  Verify it is English
english-document                      tags=["format.valid", "lang.en"]
    │
    ▼ [domain_classifier]  Determine document domain
english-legal-document                tags=["format.valid", "lang.en", "domain.legal"]
    │
    ▼ [translator]  Begin translation
chinese-legal-document                tags=["lang.zh", "domain.legal"]
```

Each guard layer narrows the data from one Format type to a more precise subtype. Tags are inherent attributes of Format types—once data enters the `english-document` type, it inherently carries the `lang.en` tag; it does not need to be "granted" at runtime. This results in:
- **Single responsibility for each validator**—checks only one dimension.
- **Precise failure points**—"Invalid format" and "Not English" are different errors.
- **Composability**—Need French translation? Just swap `language_guard` for a French detector.

- **Each validator has a single responsibility**—checks only one dimension.
- **Precise failure points**—"Invalid format" and "Not English" are different errors.
- **Composability**—Need French translation? Just swap `language_guard` for a French detector.

### 6.5 Confidence and Semantic Distance

When an entry guard is a soft anchor (like an LLM classifier), `confidence` quantifies the uncertainty of semantic matching:

```text
Scenario: LLM determines if a document belongs to the "Legal Domain"

Calibrated, High Confidence:
  verdict: PASS, confidence=0.95
  → Downstream translator can safely use the legal terminology dictionary.

Calibrated, Low Confidence:
  verdict: PASS, confidence=0.4
  → Downstream translator should fallback to general dictionary, or request human confirmation.

Uncalibrated (Pre-experiment):
  verdict: PASS, confidence=None
  → Default routing, marked as pending calibration.
```

**Confidence allows the pipeline to quantify semantic risks and make corresponding decisions.** In V0.1, the uncertainty of soft anchoring was a black box—PASS was PASS, with no degrees. V0.2`s confidence opens this black box.

Note that `confidence=None` means "uncalibrated"—before experimental data is available, honestly expressing "I don`t know the accuracy" rather than fabricating a number.

Pipelines can set **threshold-based routing** based on confidence:

```yaml
routes:
  PASS:
    - condition: "confidence >= 0.8"
      action: NEXT
      target: "specialized_processor"
    - condition: "confidence >= 0.5"
      action: NEXT
      target: "general_processor"
    - condition: "confidence < 0.5"
      action: HALT
      feedback: "Semantic match too low, cannot proceed"
```

### 6.6 Alignment with the Event Bus

Events produced by entry guards naturally carry semantic tags:

```text
Event 1: ANCHOR_VERDICT at format_guard
  format_out: validated-document (tags: ["format.valid"])
  confidence: 1.0

Event 2: ANCHOR_VERDICT at language_guard
  format_out: english-document (tags: ["format.valid", "lang.en"])
  confidence: 1.0

Event 3: ANCHOR_VERDICT at domain_classifier
  format_out: english-legal-document (tags: ["format.valid", "lang.en", "domain.legal"])
  confidence: None (uncalibrated)
```

Event bus consumers can precisely subscribe by the inherent tags of Formats:
- Subscribe `tags=["format.valid"]` → Receive all validly formatted document events
- Subscribe `tags=["lang.en", "domain.legal"]` → Receive only English legal document events
- Tags come from Format type definitions, not accumulated at runtime.

---

## 7. Protocol Execution

### 7.1 Static Phase: Pipeline Construction

```text
1. User/System declares a set of Anchors and Transformers
2. Declare connections (edges) between them
3. Type checker verifies:
   a. Structural compatibility: format_out → format_in of every edge (V0.1)
   b. Tag compatibility: Does format_out`s tags cover downstream format_in`s tags? (V0.2)
   c. Entry Guard: Does the entry node accept unverified input? (V0.2 Warning)
4. Output: Type-safe + Semantically-safe Pipeline definition
```

### 7.2 Dynamic Phase: Pipeline Execution

```text
1. Input data enters via entry node, carrying Format type (with inherent tags)
2. Current node (Anchor) executes:
   a. Verify if input matches format_in (Hard check)
   b. Call Validator to judge
   c. Yield Verdict (PASS / FAIL / PARTIAL)
   d. V0.2: Verdict carries confidence (None / 1.0 / calibrated value)
3. Look up routing table based on Verdict:
   - PASS  → Advance to next node (or EMIT to exit)
   - FAIL  → Handle according to route (RETRY / JUMP / HALT)
   - PARTIAL → Continue or branch
4. Data acquires new inherent tags via Format type conversion (defined by format_out`s tags)
5. If the next node requires a type conversion, pass through a Transformer
6. Repeat until Pipeline reaches exit (EMIT) or terminates (HALT)
7. Every step`s Verdict is written to the event trace for retroactive tracing
```

### 7.3 Runtime Events

Every step during Pipeline execution generates an event (aligned with OmniFactory`s FactoryEvent):

```text
ANCHOR_ENTER     — Entering an anchor
ANCHOR_VERDICT   — Anchor yields a judgment (V0.2: contains confidence)
ANCHOR_ROUTE     — Routing decision made
TRANSFORM_BEGIN  — Type conversion begins
TRANSFORM_END    — Type conversion completes
PIPELINE_EMIT    — Pipeline emits final result
PIPELINE_HALT    — Pipeline terminates abnormally
```

### 7.4 Example: Two-Anchor Agent Loop

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

### 7.5 Example: Document Processing Pipeline with Entry Guards *(New in V0.2)*

```yaml
pipeline:
  id: "doc-translation"
  name: "Document Translation Pipeline"
  tags: ["translation", "nlp"]
  entry: "input_guard"

  formats:
    - id: "raw-document"
      parent: "requirement"
      description: "Unverified document input"
      tags: []
      semantic_preconditions: []

    - id: "validated-document"
      parent: "raw-document"
      description: "Document with valid format and confirmed language"
      tags: ["format.valid", "lang.en"]
      semantic_preconditions:
        - "Document format is parsable (non-binary/non-corrupted)"
        - "Document language has been detected and confirmed as English"

    - id: "translated-document"
      parent: "validated-document"
      description: "Document that has completed translation"
      tags: ["lang.zh"]
      semantic_preconditions:
        - "Translation generated by translation engine"
        - "Source language confirmed as English"

  nodes:
    # Entry Guard: Verify document format and language
    - id: "input_guard"
      kind: ANCHOR
      format_in: "raw-document"
      format_out: "validated-document"
      validator:
        kind: HARD
        description: "Check if document is parsable, detect language"
      routes:
        PASS:
          action: NEXT
          target: "translator"
        FAIL:
          action: HALT
          feedback: "Document unparsable or language unsupported"

    # Translator: Relies on validation results from entry guard
    - id: "translator"
      kind: ANCHOR
      format_in: "validated-document"    # required_tags declared by format
      format_out: "translated-document"
      validator:
        kind: SOFT
        description: "LLM-driven translation"
      routes:
        PASS: { action: NEXT, target: "quality_checker" }
        FAIL: { action: RETRY, max_retries: 2 }

    # Quality Check: Hard anchor
    - id: "quality_checker"
      kind: ANCHOR
      format_in: "translated-document"
      format_out: "translated-document"
      validator:
        kind: HARD
        description: "Check translation integrity (non-empty, reasonable length, no gibberish)"
      routes:
        PASS: { action: EMIT }
        FAIL: { action: HALT }
```

**Note the position of `input_guard`**—it sits before `translator`, ensuring the translator never receives malformed formats or documents of unknown languages. Without an entry guard, the translator might receive a binary file and output garbage.

---

## 8. Translating Existing Systems to LAP

### 8.1 ChatGPT Conversation = Single-Anchor Pipeline

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

### 8.2 OpenAI Function Calling = Two-Anchor Pipeline

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

### 8.3 SWE-Agent (Code Repair) = Multi-Anchor Pipeline

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

### 8.4 Guardrails AI = Validator Chain

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

### 8.5 CI/CD Pipeline = Pure Hard Anchor Pipeline

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

### 8.6 V0.2 Perspective: Enhancing CI/CD with Tags *(New)*

Using V0.2`s tag system, we can add semantic dimensions to a CI/CD pipeline:

```yaml
pipeline:
  id: "cicd-enhanced"
  tags: ["ci", "production"]
  entry: "input_guard"

  nodes:
    # V0.2: Entry Guard — Verify commit validity
    - id: "input_guard"
      format_in: "code-commit"
      format_out: "verified-commit"
      validator:
        kind: HARD
        description: "Verify signatures, check committer permissions, confirm branch policies"
      routes:
        PASS:
          action: NEXT
          target: "anchor-build"
          # format_out`s tags include ["author.verified", "branch.valid"]
        FAIL:
          action: HALT
          feedback: "Commit invalid (Invalid signature / No permission / Policy violation)"

    - id: "anchor-build"
      # ... (Same as 8.5, but now we can trust the input has been verified)
```

**Without an entry guard**: The compiler might compile a malicious commit from stolen credentials.
**With an entry guard**: Invalid commits are rejected before compilation.

---

## 9. Best Practices *(New in V0.2)*

### 9.1 Format Naming Conventions

**For Humans: The name should fully describe the semantics of the type**

```text
Good naming:
  "verified-code-commit" — Humans instantly know this is a "verified code commit"
  "translated-legal-doc" — Humans instantly know this is a "translated legal doc"

Bad naming:
  "input-v2"  — What input? What does v2 mean?
  "processed" — Processed by what?
  "data"      — The most uninformative name
```

**For Computers: `(id, tags)` as a whole is the unique identifier**

```yaml
# Two types with the same structure but different semantics
format:
  id: "code-diff"
  tags: ["source.git", "domain.frontend"]

format:
  id: "code-diff"
  tags: ["source.svn", "domain.backend"]

# Structure is the same (both code-diff), semantics are different (different tags)
# Computers distinguish via tags, humans distinguish via naming + description
```

### 9.2 Entry Guard Principles

**The first node of every pipeline should be an entry guard.**

```text
Principle: The entry node of a pipeline should accept the broadest input type,
           and narrow it to the exact type expected by downstream nodes via explicit validation.

Reason: Inputs in the real world are ALWAYS "unverified"—
        They might be malformed, out of domain, untrusted source, or just not the expected thing at all.
        Intercepting these issues at the first node is much better than inexplicably crashing in the middle of the pipeline.
```

Entry Guard Best Practices:

| Rule | Description |
|------|-------------|
| Accept broadest type | `format_in` should be `raw-*` or untagged base types |
| Output narrow type | `format_out` should be a specific type with tags |
| Use hard anchors | Entry guards should prefer HARD validators (deterministic) |
| Fail fast | FAIL → HALT, do not attempt to RETRY on invalid input |
| Precise typing | `format_out``s inherent tags should precisely reflect the verified semantic dimensions |

### 9.3 Tag Design Guidelines

**Tags should only contain inherent semantic attributes—what the data "is", not "what it has gone through".**

```text
Inherent attributes (Good tags):
  "source.git"       — Data comes from Git (attribute of data)
  "lang.en"          — Language is English (attribute of data)
  "domain.frontend"  — Belongs to frontend domain (attribute of data)

Procedural traces (Bad tags):
  "context.enriched" — "Enriched" → Format chain already expresses this (enriched-diff is-a code-diff)
  "refs.extracted"   — "Refs extracted" → Format semantic preconditions declare this
  "status.reviewed"  — "Reviewed" → Event trace records this (ANCHOR_VERDICT at reviewer: PASS)
  "structure.valid"  — "Structure valid" → Format conversion itself implies this

Uninformative:
  "input"            — Has no semantics
  "v2"               — Version number is not a semantic dimension
  "probably.english" — Probabilistic judgments should not be tags (use confidence instead)
```

**Judgment Criteria: If you remove a certain node in the pipeline, does this tag still hold meaning?**
- `source.git` → Meaningful (The data indeed comes from Git, regardless of pipeline structure)
- `context.enriched` → Meaningless (Without the enricher node, this tag does not exist)

### 9.4 Confidence Usage Guide

Confidence has three semantic states:

| Value | Meaning | Source |
|-------|---------|--------|
| `None` | **Uncalibrated** — Don`t know if it is accurate | Soft anchors before experiments strictly use `None` |
| `1.0` | **Deterministic** — True by definition, not a measurement | Hard anchors (Compilers, Schema validation) |
| `0.xx` | **Calibrated** — Sourced from experimental data or a posteriori | Soft anchors with calibration data |

**Key Principle: Do not fabricate confidence numbers without experimental data.**

```text
Wrong approach:
  confidence = 0.8  ← Written by gut feeling, no calibration data support

Right approach:
  confidence = None  ← Honestly expressing "I don`t know if it is accurate"
  # After collecting (confidence, actual_correct) data pairs, fill in the calibrated value
```

Routing strategies after having calibration data:

| Scenario | Confidence | Handling Method |
|----------|------------|-----------------|
| Hard Anchor | Always `1.0` | No extra handling needed |
| Calibrated, High Conf. | ≥ 0.8 | Normal flow |
| Calibrated, Med Conf. | 0.5 ~ 0.8 | Fallback to general processing or human confirmation |
| Calibrated, Low Conf. | < 0.5 | HALT or RETRY with different prompt |
| Uncalibrated | `None` | Process per default route, mark as pending calibration |

### 9.5 Semantic Distance and Pipeline Stability

**Definition: Semantic Distance = The gap between the input data`s actual semantics and the Format`s claimed semantics.**

```text
Semantic Distance = 0: Perfect match
  Input claims to be "english-doc", and is actually an English document.

Semantic Distance > 0: Deviation exists
  Input claims to be "english-doc", but is actually a mix of English and Chinese.

Semantic Distance >> 0: Severe mismatch
  Input claims to be "english-doc", but is actually an image.
```

**Pipeline stability is inversely proportional to the semantic distance at the entry point.** If there is a large semantic deviation at the entry, this deviation will be **amplified** in the pipeline—every subsequent node operates on wrong semantic assumptions, causing the error to snowball.

The role of an Entry Guard is to **compress the semantic distance to 0 (or as close to 0 as possible) at the pipeline entry**. This is why the Entry Guard is the most important practice in LAP V0.2.

### 9.6 Necessary Condition Verification Methodology (Contrapositive + Counterexample Driven)

**Verification Rules = Necessary Conditions.** Validators check "the necessary conditions to be a good output", not the sufficient conditions.

#### Ideal vs. Reality

```text
Ideal: Verification rules are necessary and sufficient conditions
  "Satisfying these conditions ⟺ definitely a good output"
  → Almost impossible to achieve in reality (semantic space is too large)

Reality: Approximate using a combination of necessary conditions
  "If it does not satisfy C, it is definitely NOT a good output" (Contrapositive)
  → Each additional necessary condition eliminates one class of bad outputs.
  → The intersection of necessary conditions progressively approximates necessary and sufficient conditions.
```

#### Contrapositive Thinking Method

When designing each verification rule, you must think from the perspective of the **contrapositive**, not forward assumption:

```text
Forward Assumption (Wrong thinking):
  "If it brings code changes, the summary should mention specific files"
  → Reasoning inside an already wrongly narrowed assumption space
  → Might miss valid cases like "pure config changes, no code but has a summary"

Contrapositive (Right thinking):
  "If there is no summary, is it definitely NOT a good requirement doc?"
  → Yes, a requirement doc without a summary is definitely incomplete.
  → Conclusion: Summary being required is a valid necessary condition.
```

#### Counterexample Verification Flow

Every candidate necessary condition must pass a counterexample test before acceptance:

```text
Step 1: Propose candidate rule C
Step 2: Ask the contrapositive: "If C is not satisfied, is it definitely not a good output?"
Step 3: Search for counterexamples: Does a situation exist where "C is false but output is correct"?
Step 4: Verdict:
  Found counterexample → C is not a necessary condition, discard or revise.
  No counterexample → C is a necessary condition, accept.
```

#### Practical Case: Code Review Requirement Validator

The following shows the complete analysis process for candidate verification rules (using a Code Review pipeline as an example):

**Accepted Rules (Passed counterexample check):**

| Rule | Contrapositive Question | Counterexample Exists? | Conclusion |
|------|-------------------------|------------------------|------------|
| commit_id required | No commit_id → definitely bad review? | No | ✓ Accept |
| summary required | No summary → definitely bad review? | No | ✓ Accept |
| changes non-empty | No changes at all → definitely bad review? | No | ✓ Accept |
| Every change must have change_type | No change type → definitely bad review? | No | ✓ Accept |
| change_type within valid enum | Type not in enum → definitely wrong? | No | ✓ Accept |

**Rejected Rules (Counterexample exists):**

| Rule | Contrapositive Question | Counterexample | Conclusion |
|------|-------------------------|----------------|------------|
| Every change must link to source file | Change not linked to source file → definitely wrong? | Pure config change: only modified YAML/JSON, no source files. | ✗ Reject |
| Function name must appear in diff | Function name not in diff → definitely wrong? | Config level change: only modifying environment variables or permissions. | ✗ Reject |
| old_value must be literal | old_value is not literal → definitely wrong? | Natural language description: "Old logic: Timeout after 3 retries" | ✗ Reject |

#### Common Pitfalls

**Trap 1: Reasoning inside wrong type assumptions**

```text
Scenario: InputGuard is named "code-commit" but actually only passes commits with .py files
Problem: Validator analyzes under the assumption "code-commit = definitely has Python files"
Result: "Every change must link to a .py file" seems to have no counterexamples
        (because in the assumption space, indeed every commit has .py files)
Truth: The assumption space itself is wrong—a code-commit could be a pure config/doc change.
```

**Solution: Isolated analysis.** Look only at the validator`s own `format_in` / `format_out` definition; do not introduce behavioral assumptions of upstream nodes.

**Trap 2: Confusing "Faithful Check" with "Direct Filtering"**

```text
Faithful Check (Correct): "If A is not satisfied, it is definitely not a good B"
  → Validator checks necessary conditions, does not presuppose conclusion.

Direct Filtering (Dangerous): "If A is satisfied, it is a good B"
  → Validator is making a sufficiency judgment, might let bad outputs pass if they coincidentally match.
```

**Trap 3: Direction of upstream/downstream necessary conditions**

```text
Correct Direction: Upstream necessary conditions ⊇ Downstream necessary conditions
  Entry guard checks: "Is a valid Git commit" (Broad)
  Final validator: "commit_id required + summary required + changes non-empty + ..." (Narrow)
  → Upstream only filters the obviously unqualified; downstream progressively tightens.

Wrong Direction: Upstream is stricter than downstream
  Entry guard checks: "Must contain .py source file" (Narrow)
  Final validator: "changes can include config file modifications" (Broad)
  → Contradiction! The entry guard already excluded inputs the downstream considers valid.
```

### 9.7 Format Type Precision

**Format type names must honestly reflect the actual semantic scope.**

If a validator actually filters a subset, the type name must reflect this subset. Otherwise, all downstream reasoning is built on a faulty foundation.

```text
Scenario: InputGuard actually filters "Commits containing Python source files"
Wrong naming: code-commit  ← Implies containing all code commits
Right naming: python-code-commit  ← Honestly reflects the scope

Alternatively: Modify InputGuard so it truly accepts all code commits
Right naming: code-commit  ← Now the name matches the behavior
```

**Test Method: What happens to downstream if input outside this type`s claimed scope is let in?**

- If downstream can process normally → Type name is too narrow, should be broadened.
- If downstream crashes → Type name is correct.
- If downstream can process but yields bad results → Needs to be split into two types.

---

## 10. Ground Truth Surface

In complex concurrent scenarios or extremely long event streams, how do we ensure the system does not fall into meaningless state explosions or concurrent dirty writes? LAP turns these traditional "engineering problems" into pure "semantic omissions."

All inconsistencies or infinite retries are fundamentally because the pipeline lacks a definitive **Ground Truth**.

In the LAP space, the absolute upper bound of system confidence (1.0) can only originate from strict external truths. We call this the **Ground Truth Surface**. It includes four sources:
1. **Code-source Truth**: State of existing codebases, Git commit history.
2. **Human-source Truth**: Public internet information, human-in-the-loop reviews.
3. **Physical-source Truth**: Sensor data, hard feedback from actuators.
4. **Logical-source Truth**: Mathematical theorems, compilers, strict AST parsers.

**Core Argument: All soft anchoring (LLMs) is approaching and ultimately collapsing into hard anchoring (Ground Truth).**
In a well-designed LAP pipeline, the terminus of the pipeline must be one or more hard anchors connected to the ground truth surface (e.g., a Git state checker verifying no dirty writes, and all tests passing). If this anchor yields a FAIL, it will inevitably carry a very high-confidence Diagnosis, forcing the upstream LLM to semantically readjust.

---

## 11. Vision

### 11.1 Short-term: Protocol Foundation for OmniFactory

LAP provides OmniFactory with:
- Formalized description of the Agent step loop (two-anchor pipeline)
- Type-safe composition for multi-Agent collaboration
- A unified event model for pipeline observability
- Natural mounting points for shadow interventions (inserting an Intervention Anchor between any two Anchors)
- V0.2: Precise event filtering driven by semantic tags
- V0.2: Entry guards ensuring semantic safety of pipeline inputs

### 11.2 Mid-term: The Dual Protocol of MCP

```text
MCP = Input side standardization (How LLMs access external capabilities)
LAP = Output side standardization (How LLM artifacts are verified and routed)
```

MCP answers: "What tools can the LLM use?"
LAP answers: "How should the LLM`s output be validated?"

The two are complementary, covering the complete surface area of LLM interactions with the external world.

### 11.3 Long-term: Large Language Programming Model

LAP is not just a protocol—it is a **Programming Paradigm**:

- **Format is a type**: Describes the semantics of the data (V0.2: Structural identity + Semantic tags).
- **Anchor is a function**: Receives a type, produces a type, carries validation logic.
- **Transformer is a type conversion**: LLM-driven semantic conversion.
- **Pipeline is a program**: Type-safe function composition.
- **Type Checking is a compiler**: Catches errors during pipeline construction (V0.2: Includes tag coverage checking).

Under this paradigm:
- "Programming" = Declaring Transformers between Formats
- "Testing" = Adding hard anchors into the pipeline
- "Debugging" = Checking which Anchor`s Verdict in the pipeline did not meet expectations
- "Refactoring" = Reorganizing the connections between Anchors and Transformers
- "Requirement Analysis" = Defining the entry Format and exit Format
- V0.2: "Type safety" = Not only structural matching, but inherent tag compatibility + necessary condition verification.

**The user only needs to declare "from this type to that type", and the system automatically infers what Transformers and Anchors are needed in between—this is the true form of Natural Language Programming.**

---

## 12. Metrics to be Validated

LAP V0.2 adds the following validation items on top of the 8 metrics in V0.1:

### 12.1 V0.1 Metrics (Retained)

| Metric | Pass Standard |
|--------|---------------|
| Primitive Completeness | Five primitives can describe all known LLM anchoring scenarios |
| Type System Validity | 100% of type errors caught, 0% false positives |
| Transformer Feasibility | Core Transformer single-call success rate > 60%, > 90% with RETRY |
| Protocol Overhead | LAP overhead < 1% of total execution time |
| Readability | LAP YAML description is better than equivalent Python code |
| Interoperability | Existing tool adapter < 50 lines, no modification to original tool |

### 12.2 New Metrics in V0.2

#### Tag System Validity

**Question**: Can tag compatibility checking find type incompatibilities at compile time?

**Validation Method**:
1. Build a pipeline where a node`s `format_in` requires the tag `["domain.frontend"]` but the upstream `format_out` does not contain this tag.
2. Check if PipelineChecker issues a warning.
3. Check if the warning disappears after correcting the Format definition.

**Pass Standard**: 100% of tag incompatibilities are detected.

#### Entry Guard Effectiveness

**Question**: Do entry guards effectively reduce unexpected failures in downstream nodes?

**Validation Method**:
1. Prepare 100 inputs, where 30% are malformed/out of domain.
2. Compare pipeline behavior with/without entry guards:
   - Without guards: Count which nodes FAIL due to unexpected input.
   - With guards: Count the number intercepted right at the entry.

**Pass Standard**: With entry guards, downstream node FAILs caused by "unexpected input" are reduced by > 90%.

#### Confidence Calibration

**Question**: Does a soft anchor`s confidence value correlate with its actual accuracy?

**Validation Method**:
1. Collect (confidence, actual_correct) data pairs from an LLM classifier.
2. Plot a calibration curve: Is the actual correct rate around 80% for predictions with confidence=0.8?

**Pass Standard**: Brier Score < 0.15 (well calibrated).

#### Relationship between Semantic Distance and Pipeline Success Rate

**Question**: Does semantic distance at the entry truly affect the final output quality of the pipeline?

**Validation Method**:
1. Manually label the "true semantic distance" of a batch of inputs.
2. Run the pipeline, record final output quality scores.
3. Analyze correlation.

**Pass Standard**: Semantic distance and output quality show significant negative correlation (r < -0.5).

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Anchor** | The atomic execution unit of LAP. `(Format_in, Validator, Routes) → Format_out`. Anchors probabilistic outputs into deterministic artifacts. |
| **Format** | The semantic type of data flowing through the pipeline. V0.2: Complete identity defined jointly by `(id, tags)`. |
| **Verdict** | The output of a Validator. `PASS / FAIL / PARTIAL` + diagnostic info. V0.2: Contains `confidence` and `granted_tags`. |
| **Validator** | The component executing the anchoring judgment. Divided into Hard (deterministic) and Soft (probabilistic). |
| **Route** | The mapping from a judgment result to the next action. `NEXT / RETRY / JUMP / EMIT / HALT`. |
| **Transformer** | Type converter between Formats. Typically LLM-driven. A special form of soft anchoring. |
| **Pipeline** | A directed, type-safe composition of Anchors and Transformers. The "program" of LAP. V0.2: Contains `group` and `tags`. |
| **Hard Anchoring** | Deterministic judgment. Compilers, JSON Schema, test suites. Provable. confidence = 1.0. |
| **Soft Anchoring** | Probabilistic judgment. LLM-as-judge, human review. Unprovable. confidence < 1.0. |
| **Semantic Inheritance** | The subtype relationship between Formats. Code <: Spec <: Requirement. Subtypes maintain intent semantics but change structure. |
| **Semantic Tags** *(V0.2)* | Orthogonal semantic dimensions of Formats. Dot-separated hierarchical naming. More tags = narrower type. |
| **Entry Guard** *(V0.2)* | Design pattern for pipeline entry nodes. Accepts unverified input, narrows to verified type via explicit validation. |
| **Semantic Distance** *(V0.2)* | The gap between the input data`s actual semantics and the Format`s claimed semantics. |
| **Granted Tags** *(V0.2)* | Semantic dimensions declared in the Verdict, confirmed by the current validation. Accumulates in the pipeline. |
| **Confidence** *(V0.2)* | Value from 0.0~1.0 in Verdict, quantifying validator`s certainty. Hard anchors are always 1.0. |

## Appendix B: Relationship with Existing Protocols

```text
              ┌──────────────────────────────────────────┐
              │          Application Layer                │
              │  Agent / Code Gen / Chat / Automation     │
              ├──────────────────────────────────────────┤
              │    LAP (Language Anchoring Protocol)      │  ← This Protocol
              │    Output Verification + Semantic Routing │
              │    V0.2: Tags + Entry Guard + Confidence  │
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

## Appendix C: V0.1 → V0.2 Change Summary

| Change | V0.1 | V0.2 |
|--------|------|------|
| Format Identity | `id` (Inheritance chain) | `(id, tags)` dual dimensions |
| Format Fields | id, name, description, parent, schema | Added tags, semantic_preconditions, required_tags |
| Verdict Fields | kind, output, diagnosis, details | Added confidence, granted_tags |
| Pipeline Fields | id, name, description, nodes, edges, entry | Added group, tags |
| Type Check | Structural compatibility | Structural compatibility + Tag coverage |
| Input Handling | Implicit trust | Entry Guard pattern (Explicit validation) |
| Semantic Uncertainty | Black box (PASS/FAIL binary) | confidence quantification + threshold routing |
| Discoveries count | 5 | 7 (Added: Semantic dimensions, Unverified input) |
| Best Practices | None | 5 rules (Naming / Entry Guard / Tag design / confidence / Semantic distance) |

---

*LAP V0.2 — 2026-03-15 — Draft*
