# Language Anchoring Protocol (LAP) — V0.2 Specification

> **Status**: Draft / V0.2
> **Date**: 2026-03-15
> **Author**: LAP Protocol Authors
> **Project**: OmniFactory
> **Changes**: Added Semantic Tag System, Entry Guards, Confidence semantics, and Format Type Precision on top of V0.1.

---

## Table of Contents

1. [Origin of Needs](#1-origin-of-needs)
2. [Core Discoveries](#2-core-discoveries)
3. [Protocol Primitives](#3-protocol-primitives)
4. [Type System](#4-type-system)
5. [Semantic Tag System](#5-semantic-tag-system) *(New in V0.2)*
6. [Unverified Inputs and Entry Guards](#6-unverified-inputs-and-entry-guards) *(New in V0.2)*
7. [How the Protocol Works](#7-how-the-protocol-works)
8. [LAP Translation of Existing Systems](#8-lap-translation-of-existing-systems)
9. [Best Practices](#9-best-practices) *(New in V0.2)*
10. [Vision](#10-vision)
11. [Metrics to be Validated](#11-metrics-to-be-validated)

---

## 1. Origin of Needs

### 1.1 The Root Problem

What does the "L" in LLM stand for? **Language**.

An LLM is essentially a probabilistic language generator. It does not guarantee correctness, usability, or safety.

Yet, we've built an entire industry around it. **All these applications fundamentally do one thing: anchor probabilistic outputs into deterministic, reliable artifacts.**

- Structured Output (JSON mode) is anchoring—constraining token sampling.
- Tool Use / Function Calling is anchoring—constraining output to valid function calls.
- Compilers are anchoring—verifying syntax and types.
- Test suites are anchoring—verifying behavioral correctness.
- Human review is anchoring—verifying business intent.
- CI/CD Pipelines are anchoring—verifying deployment conditions.

**They are all different instances of the same pattern.** Related work such as Design by Contract (Eiffel, 1986), Guardrails AI, and DSPy have addressed aspects of this pattern. LAP attempts to unify these operations under a single typed framework.

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

### 2.3 Discovery 3: Hard vs. Soft Anchors —— "Who has the final say?"

On the pipeline, we distinguish between two types of checks:

| | Hard Anchor —— **Authoritative Truth** | Soft Anchor —— **Semantic Guess** |
|---|---|---|
| Nature | **Absolute Truth**. Determined by machines; black or white results. | **Subjective Judgment**. Determined by AI or humans; probabilistic. |
| Examples | Compiler, JSON Schema, Tests, Git state | LLM-as-judge, Human code review, Visual check |
| Guarantee | Same input → Same result | Same input → Different results |
| Role | **Gatekeeper**. Protects the system's baseline. | **Decision Maker**. Guides the path forward. |

**Core Insight: The upper bound of system confidence always depends on how much "Authoritative Truth" you introduce.**

- Simply "the AI thinks the code is good" is not enough.
- It must pass through "the compiler says no syntax errors" and "Pytest says logic is correct"—these two layers of **Reality Baselines**.
- **Industry Trend**: Continuously supporting "soft guesses" with "hard validations."

### 2.4 Discovery 4: Format is a Semantic Type, not a Structure Definition

Format is not a structural constraint; it carries **semantics**. It describes "what this thing actually is."

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

**Crucial Correction: Distinguishing "Identity (Is-A)" from "Transformation (Derives-From)"**

TypeScript added types to JavaScript's chaos. LAP adds "transformation rules" and a "quality control network" to the chaos of LLM workflows.

### 2.6 Discovery 6: Semantic Types Need "Facet Tags" *(New in V0.2)*

Inheritance only says "what it is." **Semantic Tags** tell us "what state it's in."

```
Format.id    = Identity (e.g., code-diff)
Format.tags  = Facets (e.g., reviewed, security)
(id, tags)   = Complete Identity
```

### 2.7 Discovery 7: Unverified Input is a "Hidden Risk" *(New in V0.2)*

V0.1 implicitly trusted inputs. V0.2 introduces the **Entry Guard (Security Checkpoint)** pattern. All raw data must pass "security" and get a "verified" tag before entering the flow.

---

## 3. Protocol Primitives

### 3.1 Format — Semantic Type *(V0.2 Enhanced)*

Format answers: "What exactly is this thing running on the assembly line?"

#### Dual Identity of Format

Like a person having a "Job" (Classification) and "Certificates" (Tags):

| Dimension | Expression | Analog | Purpose |
|-----------|------------|--------|---------|
| Identity | `id` + `parent` | Class/Struct | Dictates the structure |
| Attributes | `tags` | Interface/Trait | Dictates the verified state |

---

## 9. Best Practices *(New in V0.2)*

### 9.5 Semantic Distance and Pipeline Stability

**Semantic Distance = Gap between the actual data and the claimed Format.**

The goal of the **Entry Guard** is to compress the semantic distance to zero at the entrance.

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Anchor** | A **Checkpoint** on the pipeline. Turns AI guesses into deterministic results. |
| **Format** | The **Identity Tag** of data. V0.2: Defined by (Identity, Facets). |
| **Verdict** | The conclusion of a Checkpoint (PASS/FAIL/PARTIAL + Diagnosis). |
| **Validator** | Logic inside a Checkpoint. Split into Hard (Machine) and Soft (AI). |
| **Route** | "Where to go based on results." |
| **Transformer** | Data **Morpher**. Translates one identity to another (e.g., Requirement to Code). |
| **Pipeline** | A complete assembly line of Checkpoints and Transformers. |
| **Authoritative Truth (Ground Truth)** | **Inviolable Reality Baseline**. e.g., Compiler, Tests, Git state. |
| **Semantic Tags** | **Facet Tags** of data. e.g., "security-verified", "frontend-domain". |
| **Entry Guard** | **Security Checkpoint** for raw data, ensuring it is verified before entering. |
| **Confidence** | How sure the Checkpoint is about the result (Hard is always 1.0). |
