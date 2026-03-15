# Language Anchoring Protocol (LAP)

**The Dual Protocol of MCP for Output Verification and Routing in LLM Architectures.**

[![Status: Draft](https://img.shields.io/badge/Status-Draft_V0.2-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)]()
[中文文档 (Chinese)](README_zh.md)

## 1. The Core Problem

We have built an entire industry around Large Language Models (LLMs)—code generation, conversational systems, autonomous agents, and automated workflows. However, the "L" in LLM stands for **Language**. Fundamentally, an LLM is a probabilistic generator; it provides no inherent guarantees of correctness, usability, or safety.

Every agentic workflow and LLM application is ultimately doing one thing: **Anchoring probabilistic outputs into deterministic, reliable artifacts.**

*   **JSON Mode** is anchoring (constraining the token sampling space).
*   **Tool Use** is anchoring (constraining output to valid function signatures).
*   **Compilers and Test Suites** are anchoring (verifying syntax and behavior).
*   **Human-in-the-loop** is anchoring (verifying intent).

While the **Model Context Protocol (MCP)** standardized the *input* side (how LLMs access external tools and data), the *output* side remains completely fragmented. Tools like Guardrails AI, DSPy, and Pydantic validation solve specific fragments, but there is no universal protocol for how LLM outputs should be verified and routed.

**LAP fills this void.**

## 2. What is LAP?

The Language Anchoring Protocol (LAP) is a meta-protocol that treats LLM agent pipelines as a **Semantic Type System**. It defines how probabilistic outputs are systematically transformed, verified, and routed through a series of "Anchors" until they collapse into a deterministic result.

### 2.1 The Atomic Primitive: The Anchor

All anchoring operations can be decomposed into an atomic binary structure:
```text
Anchor = (Format, Validator → Verdict → Route)
```
*   **Format**: The expected semantic type of the input (e.g., "BugSpec", "SourceCode", "TestResult").
*   **Validator**: The mechanism checking if the output meets constraints. Can be **Hard** (deterministic, like a compiler) or **Soft** (probabilistic, like LLM-as-a-judge).
*   **Verdict**: The result (`PASS`, `FAIL`, `PARTIAL`) which explicitly carries *Diagnosis* information.
*   **Route**: Where to send the artifact next based on the Verdict (e.g., jump back to the LLM with the diagnosis for self-correction, or proceed to deployment).

### 2.2 Formats as a Type System

In LAP, "Formats" are not just JSON Schemas; they are **Semantic Types**. 

Data flowing through an agent pipeline is fundamentally the same entity—a **Requirement**—transitioning through different states:
```text
Requirement (Base Intent)
├── Spec        (Structured Intent)
│   ├── Code        (Executable Intent)
│   ├── TestPlan    (Verifiable Intent)
│   └── Doc         (Readable Intent)
```

In LAP, programming, writing docs, or generating tests are simply **Type Transformations** (driven by LLMs) from one format to another. LAP ensures **Type Safety** at the pipeline construction phase, preventing invalid routes (e.g., sending a `TestResult` directly to an Anchor expecting a `Spec` without a `Transformer`).

## 3. Why Build on LAP?

1.  **True Neurosymbolic Bridging:** LAP provides a standardized way to constrain neural generation (Soft Anchors/Transformers) with symbolic verification (Hard Anchors).
2.  **Turing-Complete Routing with Diagnostics:** Unlike simple retry loops, LAP's Verdicts carry standardized diagnoses, enabling complex routing, multi-agent collaboration, and systemic self-healing.
3.  **Meta-Evolution:** Because the pipeline is typed and event-driven, LAP enables systems to track where "Residuals" (failures) occur and automatically mutate prompts or constraints to heal the architecture over time.

## 4. Specifications

Detailed specifications are available in the `specifications/` directory:

*   [LAP V0.1 Specification (Chinese)](specifications/LAP_V0.1_zh.md) - The foundational theory and type system.
*   [LAP V0.2 Specification (Chinese)](specifications/LAP_V0.2_zh.md) - Advanced routing and multi-agent coordination.
*(English translations are currently in progress).*

## 5. Reference Implementation

LAP is not just a theory. The reference implementation of the protocol, including the Event Bus, Pipeline Engine, and the Meta-Evolution Engine, can be found in the [OmniFactory](https://github.com/your-username/omnifactory) repository.

---

*The era of ad-hoc prompt engineering and hardcoded retry loops is ending. It is time for a type-safe protocol for the output layer.*
