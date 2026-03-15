# Language Anchoring Protocol (LAP)

**A humble attempt at a universal semantic contract and processing protocol for AI agent workflows.**

[![Status: Draft](https://img.shields.io/badge/Status-Draft_V0.2-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)]()
[中文文档 (Chinese)](README_zh.md)

## 1. Origin and Pain Points

The creation of LAP comes from a personal journey of frustration and exploration. I experimented with Langflow, LangSmith (LangGraph), referenced n8n and Dify, explored the Feishu Open Platform and Anycross, and even started writing my own "LangGraphFlow". I also closely studied projects like OpenHands.

During this process, a question kept arising: **Why are there so many expressions of AI workflows, yet a complete lack of a universal contract?**

I needed a unified interface that could treat requirements, architectural designs, source code, review comments, and commit histories as variations of the same underlying substance, regardless of their source. Currently, choosing a workflow tool means heavy vendor lock-in. Moreover, most existing node-based flowcharts are static mappings of explicit processes; they are rarely flexible enough to allow agents to freely "think and write" (most only offer limited, predefined agent processing functions).

While traditional flowcharts have always lacked universal contracts, the era of Large Language Models has unified the core processing object: **Language**. Because the object is unified, I believe there *should* be a universal contract.

This is not something that should have a "moat." It is far too universal. Anyone's understanding of Standard Operating Procedures (SOPs) and semantic objects should be able to serve as nourishment for this ecosystem. High-quality, self-adaptive, automated AI cluster services should not be the exclusive privilege of large enterprises. 

Thus, LAP was born: a universal type contract and processing protocol, designed specifically for Event-Bus architectures, serving AI clusters, and optimized for macroscopic semantic processing, evolution, and learning.

## 2. What is LAP?

Is LAP a protocol? Yes.
Is it in its final, complete form? Not yet. 

However, its core definition is very clear: **When data enters a processing node, it must conform to a specific semantic format; when it exits, it must conform to another specific semantic format.**

### 2.1 Core Traits
*   **Atomization:** The protocol atomizes semantics and semantic contracts.
*   **Universality:** A requirement is a requirement, regardless of where it comes from (a chat, a Jira ticket, a GitHub issue).
*   **Neural Network Compatibility:** With atomic operations, routing capabilities, and high human-readability, LAP operates on *semantics* rather than mathematical computation or weights. 

This gives LAP the potential (and it is just a potential, though perhaps a necessary one) to become a reasonable carrier for **Semantic Neural Networks**. 

*Note: Semantic Neural Networks can be viewed as a semantic alternative to Logical/Symbolic Neural Networks (LNNs). While their nodes are not as rigidly deterministic as traditional LNNs, LLMs allow for a smooth, probabilistic transition between these semantic states.*

### 2.2 The Anchor Concept
LAP treats every step of an AI workflow as an "Anchor," which binds the probabilistic output of an LLM to a deterministic format.
```text
Anchor = (Format_In, Validator → Verdict → Route) → Format_Out
```

## 3. The Vision: Event Bus + Semantic Contracts

Current explicit graph mappings are too rigid. I believe the best architectural form for true autonomous agents is an **Event Bus**. 

LAP serves as the semantic type system that flows over this Event Bus. It doesn't dictate *how* an agent thinks; it dictates *what semantic contracts* the agent's inputs and outputs must adhere to. This allows different agents, created by different people, to collaborate seamlessly on the same bus, evolving and learning through a unified language of intent, specification, and execution.

## 4. Specifications

Detailed specifications are available in the `specifications/` directory (currently in Chinese, translations pending):

*   [LAP V0.1 Specification](specifications/LAP_V0.1_zh.md) - Foundational theory and type system.
*   [LAP V0.2 Specification](specifications/LAP_V0.2_zh.md) - Advanced routing and multi-agent Event Bus coordination.

## 5. Reference Implementation

To prove this isn't just theory, the first reference implementation of the LAP protocol (including the Event Bus, Pipeline Engine, and a Meta-Evolution Engine) is being developed in the [OmniFactory](https://github.com/your-username/omnifactory) repository.
