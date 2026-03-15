# Language Anchoring Protocol (LAP)

**LLM 架构中“输出验证与路由”的底层协议（MCP的对偶协议）。**

[![Status: Draft](https://img.shields.io/badge/Status-Draft_V0.2-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)]()
[English Documentation](README.md)

## 1. 核心问题

围绕着大语言模型（LLM），我们建立了一个庞大的产业——代码生成、对话系统、自主 Agent 以及自动化工作流。然而，LLM 中的“L”代表的是 **Language（语言）**。从根本上说，LLM 是一个概率生成器；它不提供任何关于正确性、可用性或安全性的内在保证。

每一个 Agent 工作流和 LLM 最终都在做同一件事：**将概率性输出“锚定（Anchoring）”为确定性、可靠的产物。**

*   **JSON 模式** 是一种锚定（约束 Token 采样空间）。
*   **工具调用 (Tool Use)** 是一种锚定（将输出约束为合法的函数签名）。
*   **编译器和测试套件** 是一种锚定（验证语法和行为）。
*   **人工审查 (Human-in-the-loop)** 是一种锚定（验证意图）。

虽然 **MCP（模型上下文协议）** 标准化了 **输入侧**（LLM 如何访问外部工具和数据），但 **输出侧** 仍然完全处于碎片化状态。像 Guardrails AI、DSPy 和 Pydantic 校验等工具解决了特定片段的问题，但针对“LLM 产出应该如何被标准化验证并路由”，目前并没有一个通用的协议。

**LAP 填补了这一空白。**

## 2. LAP 是什么？

语言锚定协议 (LAP) 是一个元协议 (Meta-Protocol)，它将 LLM Agent 的流水线视为一个 **“语义类型系统” (Semantic Type System)**。它定义了概率输出如何通过一系列“锚点（Anchors）”被系统地转换、验证并路由，直到它们坍缩为一个确定性的结果。

### 2.1 原子原语：锚点 (The Anchor)

所有的锚定操作都可以被分解为一个不可分割的原子二元结构：
```text
Anchor = (Format, Validator → Verdict → Route)
```
*   **Format（格式/类型）**：期望输入的语义类型（例如："BugSpec", "SourceCode", "TestResult"）。
*   **Validator（验证器）**：检查输出是否满足约束的机制。可以是 **硬性 (Hard)**（确定性的，如编译器）或 **软性 (Soft)**（概率性的，如 LLM 作为裁判）。
*   **Verdict（判定）**：判定结果（`PASS`, `FAIL`, `PARTIAL`），并明确携带 **诊断信息 (Diagnosis)**。
*   **Route（路由）**：根据判定结果，决定下一步将产物发送到哪里（例如：带着诊断信息跳回 LLM 节点进行自我修正，或者推进到部署节点）。

### 2.2 作为类型系统的 Format

在 LAP 中，“Format”不仅仅是 JSON Schema，它们是 **语义类型 (Semantic Types)**。

流经 Agent 流水线的数据从根本上讲是同一个实体——**需求 (Requirement)**——经历着不同状态的转换：
```text
Requirement (意图基类)
├── Spec        (结构化的意图)
│   ├── Code        (可执行的意图)
│   ├── TestPlan    (可验证的意图)
│   └── Doc         (可读的意图)
```

在 LAP 中，编程、写文档或生成测试，仅仅是由 LLM 驱动的、从一种格式到另一种格式的 **类型转换 (Type Transformations)**。LAP 在流水线构建阶段确保 **类型安全 (Type Safety)**，防止非法的路由（例如：在没有经过 Transformer 的情况下，将 `TestResult` 直接发送给期望接收 `Spec` 的锚点）。

## 3. 为什么要基于 LAP 构建？

1.  **真正的神经符号桥接 (Neurosymbolic Bridging)：** LAP 提供了一种标准化的方式，用符号逻辑（硬锚点，如测试/编译）去约束和引导神经网络的生成（软锚点/转换器）。
2.  **携带诊断信息的图灵完备路由：** 与简单的重试循环不同，LAP 的 Verdict 携带标准化的诊断信息，从而支持复杂的路由、多 Agent 协作以及系统的自我修复。
3.  **元进化 (Meta-Evolution)：** 由于流水线是强类型且事件驱动的，LAP 允许系统追踪“残差（Residuals，即失败案例）”发生的位置，并自动变异 Prompt 或约束条件，从而随着时间的推移不断修复和进化架构本身。

## 4. 规范文档

详细的协议规范位于 `specifications/` 目录下：

*   [LAP V0.1 核心规范 (中文)](specifications/LAP_V0.1_zh.md) - 基础理论与类型系统。
*   [LAP V0.2 核心规范 (中文)](specifications/LAP_V0.2_zh.md) - 高级路由与多 Agent 协同。

## 5. 参考实现

LAP 不仅仅是一个理论框架。协议的首个参考实现（包含事件总线 Event Bus、流水线引擎 Pipeline Engine 以及元进化引擎 Meta-Evolution Engine），将作为核心引擎包含在 [OmniFactory](https://github.com/your-username/omnifactory) 项目中发布。

---

*硬编码的重试循环和临时 Prompt Engineering 的时代即将结束。是时候为输出层建立一个类型安全的协议了。*
