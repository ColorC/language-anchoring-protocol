# Language Anchoring Protocol (LAP)

**A humble attempt at a universal semantic contract and processing protocol for AI agent workflows.**

[![Status: Draft](https://img.shields.io/badge/Status-Draft_V0.2-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)]()
[中文文档 (Chinese)](README_zh.md)

*We urgently need professional feedback and community validation. See the "Seeking Professional Validation" section.*

## 1. What is LAP?

Is LAP a protocol? Yes.
Is it in its final, complete form? Not yet. 

However, its core definition is very clear: **When data enters a processing node, it must conform to a specific semantic format; when it exits, it must conform to another specific semantic format.**

In LAP, every step of an AI workflow is treated as an **"Anchor"**. It binds the probabilistic output of an LLM to a deterministic format with specific semantics.
```text
Anchor = (Format_In, Validator → Verdict → Route) → Format_Out
```

### 1.1 Core Traits
*   **Atomization:** The protocol atomizes semantics and semantic contracts into indivisible processing units.
*   **Universality:** A requirement is a requirement, regardless of where it comes from (a chat, a Jira ticket, a GitHub issue).
*   **Neural Network Compatibility:** With atomic operations, routing capabilities, and high human-readability, LAP operates on *semantics* rather than mathematical computation or weights. 

## 2. The Vision: Event Bus & Semantic Contracts

Current explicit graph mappings are often too rigid for truly autonomous agents. I believe the best architectural form for this is an **Event Bus**. 

LAP serves as the semantic type system that flows over this Event Bus. It doesn't dictate *how* an agent thinks; it dictates *what semantic contracts* the agent's inputs and outputs must adhere to. This allows different agents, created by different people, to collaborate seamlessly on the same bus, mutually verifying outputs and evolving at a systemic level.

Given these traits, LAP has the potential (just a potential, though perhaps a necessary one) to become a reasonable carrier for **Semantic Neural Networks**. 
*> Note: Semantic Neural Networks can be viewed as a semantic alternative to Logical/Symbolic Neural Networks (LNNs). While their nodes are not as rigidly deterministic as traditional LNNs, LLMs allow for a smooth, probabilistic transition between these semantic states.*

## 3. Origin and Exploration

The creation of LAP comes from a personal journey of frustration. I experimented with Langflow, LangSmith (LangGraph), referenced n8n and Dify, explored the Feishu Open Platform and Anycross, and even started writing my own LangGraphFlow. I also closely studied projects like OpenHands.

A question kept arising: **Why are there so many expressions of AI workflows, yet a complete lack of a universal contract?**

I needed a unified interface that could treat requirements, architectural designs, code, review comments, and commit histories as variations of the same underlying substance. Currently, choosing a workflow tool means heavy vendor lock-in. Moreover, most existing node-based flowcharts are static mappings of explicit processes; they are rarely flexible enough to allow agents to freely "think and write".

While traditional flowcharts have always lacked universal contracts, the era of Large Language Models has unified the core processing object: **Language**. Because the object is unified, we should have a universal contract.

**This is not something that should have a "moat."** It is far too universal. Anyone's understanding of Standard Operating Procedures (SOPs) and semantic objects should be able to serve as nourishment for this ecosystem. High-quality, self-adaptive, automated AI cluster services should not be the exclusive privilege of a few tech giants.

## 4. Seeking Professional Validation

**To be completely sincere: I do not have 100% confidence in this yet.**

This architectural concept was driven by personal pain points. While it solved many routing and architectural coupling issues in my own experiments (OmniFactory), I deeply understand that for something to be a true "Protocol," it must withstand rigorous scrutiny from the engineering and academic communities.

I urgently need validation from professionals (architects, agent researchers, AI infrastructure developers):
* Will this type-based routing using `Format` and `Verdict` lead to deadlocks or state explosions in highly complex engineering scenarios?
* Is the idea of this being a carrier for "Semantic Neural Networks" a reasonable extrapolation, or a pipe dream?
* Do we need to introduce more timing controls or strong consistency primitives on the actual Event Bus?

If these topics interest you, please feel free to open an issue or start a discussion.

## 5. Specifications

Detailed specifications are available in the `specifications/` directory (currently in Chinese, translations pending):

*   [LAP V0.1 Specification](specifications/LAP_V0.1_zh.md) - Foundational theory and type system.
*   [LAP V0.2 Specification](specifications/LAP_V0.2_zh.md) - Advanced routing and multi-agent Event Bus coordination.

## 6. Reference Implementation

To prove this isn't just theory, the first reference implementation of the LAP protocol (including the Event Bus, Pipeline Engine, and a Meta-Evolution Engine) is being developed in the [OmniFactory](https://github.com/your-username/omnifactory) repository.
