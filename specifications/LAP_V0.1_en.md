# Language Anchoring Protocol (LAP) — V0.1 Specification

> **Status**: Draft / V0.1
> **Date**: 2026-03-14
> **Author**: LAP Protocol Authors
> **Project**: OmniFactory

---

## Table of Contents

1. [Origin of Needs](#1-origin-of-needs)
2. [Core Discoveries](#2-core-discoveries)
3. [Protocol Primitives](#3-protocol-primitives)
4. [Type System](#4-type-system)
5. [How the Protocol Works](#5-how-the-protocol-works)
6. [LAP Translation of Existing Systems](#6-lap-translation-of-existing-systems)
7. [Vision](#7-vision)
8. [Metrics to be Validated](#8-metrics-to-be-validated)

---

## 1. Origin of Needs

### 1.1 The Root Problem

What does the "L" in LLM stand for? **Language**.

An LLM is essentially a probabilistic language generator. It does not guarantee correctness, usability, or safety.

Yet, we've built an entire industry around it. **All these applications fundamentally do one thing: anchor probabilistic outputs into deterministic, reliable artifacts.**

- Structured Output (JSON mode) is anchoring—constraining token sampling.
- Tool Use is anchoring—constraining output to valid function calls.
- Compilers are anchoring—verifying syntax and types.
- Test suites are anchoring—verifying behavioral correctness.
- Human review is anchoring—verifying business intent.
- CI/CD Pipelines are anchoring—verifying deployment conditions.

**They are all different instances of the same action. But no one has named this action, and no one has defined a protocol for it.**

### 1.2 Fragmentation of Existing Tools

| Tool | Layer of Anchoring | Limitations |
|------|--------------------|-------------|
| Outlines / SGLang | Token-level syntax | Structure only, no semantics |
| Instructor / Pydantic | JSON schema validation | Single layer only, no chained verdicts |
| Guardrails AI | Composable validators | A library, not a protocol |
| DSPy | Signatures + assertions | Academic focus; boolean assertions |
| NeMo Guardrails | Dialogue policies | Limited to conversational scenarios |

**Each tool solves a fragment. No one defines a unified protocol layer.**

LAP fills this void.

---

## 2. Core Discoveries

### 2.1 Discovery 1: The Atomic Structure of Anchoring

All anchoring operations can be decomposed into a binary structure:

```
Anchor = (Format, Validator → Verdict → Route)
```

- **Format**: Defines the input structure—"what shape of thing should the LLM output."
- **Validator**: Judges if the output passes—"does this meet the constraints."
- **Route**: Decides the next step—"where to go if it passes/fails."

### 2.2 Discovery 2: Agent Systems as an Anchor Counting Problem

The reliability of an Agent system is determined by the **quantity and quality of anchors**:

```
0 Anchors = Naked LLM Output     — Purely probabilistic
1 Anchor  = Human Check          — Reliable but unscalable
2 Anchors = Agent Loop           — Minimum autonomous unit
N Anchors = Production Pipeline  — Approaching determinism
```

**Two anchors constitute the minimum autonomous unit**:

```
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

### 2.3 Discovery 3: Anchors can be Hard or Soft

| | Hard Anchor | Soft Anchor |
|---|---|---|
| Nature | Deterministic, provable | Probabilistic, unprovable |
| Examples | Compilers, JSON Schema, Tests | LLM-as-judge, Human review |
| Guarantee | Same input → Same result | Same input → Different results |
| Role | Gatekeeper | Decision maker |

**Industry Trend = Replacing/augmenting soft anchors with hard anchors.**

### 2.4 Discovery 4: Format is a Semantic Type, not a Structure Definition

Format is not a structural constraint; it carries **semantics**. It describes "what this thing actually is."

In an Agent loop, data is always a **Requirement** changing states:

```
Input:             Unverified requirement (raw)
Output with Tool:  In-progress requirement
Output w/o Tool:   Resolved requirement
```

Code, docs, tests—they are all Formats, morphological variations of a Requirement:

```
Requirement → Spec → Code → TestResult → Deployment
   "Intent"   "Plan" "Impl" "Test Report" "Runtime"
```

**They undergo evolution and transformation.** Code is not a Requirement, but it is transformed from one. During each transformation, **information often becomes "narrower" or loses background details.**

### 2.5 Discovery 5: A Type Pipeline with "Quality Control"

When Format is a type and Anchor is a function, we get a **Type System with clear transformation rules**:

```
Format          = Semantic Type (What it is)
Anchor          = Function with signatures (Transforms A to B, with validation)
Transformer     = Transformation Engine (LLM-driven auto-translation/writing)
Pipeline        = Program (A complete processing assembly line)
Type Checking   = Equivalent to "compilation"; catches wiring errors early
```

**Crucial Correction: Distinguishing "Identity (Is-A)" from "Evolution (Derives-From)"**

*   **Classification (Is-A)**: Expresses "whose child it is." e.g., `PythonCode` belongs to `Code`.
*   **Evolution (Derives-From)**: Expresses sequence in the pipeline. e.g., `Code` is transformed from `Requirement`. **Code is NOT a Requirement.**

---

## 3. Protocol Primitives

LAP consists of five primitives.

### 3.1 Format — Semantic Type

**Format is the soul of LAP.** It answers: "What is this thing flowing through the pipeline?"

### 3.2 Verdict — Decision Result

Verdict is not a boolean. It carries **Diagnosis**—the key to the feedback loop. When a FAIL occurs, the diagnosis describes "why," allowing the LLM to self-correct.

### 3.3 Anchor — Checkpoint

Anchor is the atomic execution unit. It answers:
1. **What does the input look like?** → `format_in`
2. **How to judge?** → `validator`
3. **Where to go after judgment?** → `routes`

### 3.4 Transformer — Morphological Transformer

Transformer is the engine for data "transformation" (e.g., Requirement → Code).

**Key Insight: Programming, document writing, and test design are all just Transformers in LAP.** They are type conversions between Formats, driven by LLM.

### 3.5 Pipeline — Type-Safe Composition

Pipeline is the "Program" of LAP. Its key constraint is **Type Safety**. Wiring errors are caught at "compile-time" (when building the pipeline).

---

## 4. Type System

### 4.1 Type Compatibility Rules

```
COMPATIBLE(A, B) =
    A == B                           -- Direct connection
    OR A <: B                        -- A is a sub-type of B (Upward casting)
    OR EXISTS Transformer(A → B)     -- Explicit conversion available
```

### 4.2 Compatibility Principle: Downward Compatibility (<:)

```
PythonCode belongs to the Code category.
This means:
  If a generic Code is needed, passing a PythonCode is safe.
  If a PythonCode is specifically required, passing a generic Code will fail.
```

### 4.3 "Data Loss" and "Creative Freedom" during Transformation

**Transformation is essentially "Information Thinning."** e.g., from Requirement to Code, subjective background is discarded, solidified into rigid logic.

There is a dilemma: **"To follow the script or not?"** Usually, we want code to strictly follow requirements. But if you want a "creative" Agent, deviation is what you seek.

LAP's approach: **Don't force AI to be a rigid translator, but mandate that all transformations pass through subsequent "Authoritative Truth" checkpoints.**

---

## 5. How the Protocol Works

(Static Phase: Building the Pipeline; Dynamic Phase: Executing the Pipeline)

---

## 6. LAP Translation of Existing Systems

(ChatGPT, Function Calling, SWE-Agent, Guardrails, CI/CD)

---

## 7. Vision

(OmniFactory's foundation, Dual Protocol to MCP, Large Language Programming Model)

---

## 8. Metrics to be Validated

(Completeness, Type Safety, Transformer Feasibility, Overhead, Readability, Interoperability)

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Anchor** | A **Checkpoint** on the pipeline. Turns AI guesses into deterministic results. |
| **Format** | The **Identity Tag** of data. V0.1: Defined by inheritance. |
| **Verdict** | The conclusion of a Checkpoint. Includes PASS/FAIL/PARTIAL + Diagnosis. |
| **Validator** | The logic inside a Checkpoint. Split into Hard (Machine) and Soft (AI). |
| **Route** | "Where to go based on results." |
| **Transformer** | Data **Morpher**. Translates one identity to another (e.g., Requirement to Code). |
| **Pipeline** | A complete assembly line of Checkpoints and Transformers. |
| **Authoritative Truth (Ground Truth)** | **Inviolable Reality Baseline**. e.g., Compiler, Tests, Git state. |
| **Soft Anchoring** | Probabilistic judgment (LLM-as-judge). |
| **Hard Anchoring** | Deterministic judgment (Compiler, JSON Schema). |
