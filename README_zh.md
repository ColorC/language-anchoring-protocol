# Language Anchoring Protocol (LAP)

**一次旨在为 AI 集群和 Agent 工作流构建通用语义契约与处理协议的探索。**

[![Status: Draft](https://img.shields.io/badge/Status-Draft_V0.2-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)]()
[English Documentation](README.md)

*我迫切需要社区的专业反馈与校验，详见“寻求专业验证”章节。*

## 1. LAP 到底是什么？

它是一个协议（Protocol）吗？——是的。
它是最终的完整形态吗？——我感觉还没有。

但是，它的核心定义非常明确：**数据到达某个处理节点时，必须符合某个特定的语义；数据从某个处理节点输出时，必须符合另一个特定的语义。**

简单来说，它就像是 AI 工作流里的**“进出口标准”**：它规定了数据**进来时**得是什么样，**出去时**必须变成什么样，确保 AI 的处理过程不再是“盲跑”。

在 LAP 中，我们将这个节点称为**锚点（Anchor）**。它的作用是把大语言模型（LLM）不确定的、概率性的输出，像抛锚一样固定在下游要求的确定性结构与语义上。
```text
Anchor = (Format_In, Validator → Verdict → Route) → Format_Out
```

### 1.1 核心特性
*   **语义与语义契约原子化：** 将复杂的处理流拆解为不可分割的语义转换。
*   **极致的通用性：** 甭管哪来的需求，只要是“需求（Requirement）”就可以进入处理管线。
*   **可读性和宏观神经网络潜力：** 它具备原子化操作和路由能力，并且具有极高的可读性。它基于“语义”而非纯粹的计算或权重运行。

### 1.2 架构对比：为什么我们需要 LAP？

为了更直观地理解 LAP 解决的问题，我们来对比一下传统 Agent、普通事件总线 Agent 和 LAP 驱动的 Agent 的架构差异。

#### 1. 传统 Agent (硬编码循环)
传统 Agent（如早期的 ReAct 实现）通常被包裹在一个巨大的 `while` 循环和无数的 `if/else` 中。业务逻辑、错误处理和解析逻辑高度耦合，一旦出错很难排查，也无法轻易复用。
```mermaid
graph TD
    A[用户输入] --> B[LLM 思考与输出]
    B --> C{代码解析}
    C -- 解析失败 --> E[生成错误 Prompt]
    E --> B
    C -- 成功提取工具调用 --> D[执行工具]
    D --> F{执行成功?}
    F -- 是 --> G[格式化观察结果]
    F -- 否 (抛出异常) --> H[格式化错误堆栈]
    G --> B
    H --> B
```

#### 2. 普通事件总线 Agent (如 OpenHands)
为了解耦，现代框架引入了事件总线。LLM 和工具被拆分为独立的消费者。虽然解耦了，但**总线上流淌的数据缺乏强语义契约**（通常只是松散的 JSON 字典），节点之间依靠隐含的默契配合，这导致了“隐式类型错误”频发。
```mermaid
graph LR
    subgraph 松散的事件总线
        E1((Action 事件))
        E2((Observation 事件))
    end
    
    LLM[LLM 节点] -- 发布 --> E1
    E2 -- 订阅 --> LLM
    
    Tool[工具节点] -- 订阅 --> E1
    Tool -- 发布 --> E2
```

#### 3. LAP 驱动的 Agent (语义契约总线)
LAP 在事件总线的基础上，引入了**不可绕过的安检口（检查站 Anchor）**和**严格的类型标签（Format）**。任何输出必须经过验证，判定（Verdict）决定了数据的去向。这使得系统具备了极强的类型安全和天然的自愈反馈回路。
```mermaid
graph TD
    subgraph LAP 类型安全总线
        S[[Format: agent-state]]
        A[[Format: agent-action]]
        O[[Format: tool-observation]]
    end

    subgraph LLM 软检查站
        Val1{LLM 意图判定}
        Val1 -- PASS (任务完成) --> Emit[最终答案]
        Val1 -- FAIL (需要调工具) --> A_out[输出带标签的 Action]
    end

    subgraph 工具硬检查站
        Val2{执行与语法校验}
        Val2 -- PASS (执行成功) --> O_out[输出 Observation]
        Val2 -- FAIL (带报错诊断) --> O_out
    end
    
    S -- 验证匹配进入 --> Val1
    A_out -. 注入总线 .-> A
    A -- 验证匹配进入 --> Val2
    O_out -. 注入总线 .-> O
    O -. Transformer 变身 .-> S
    
    style S fill:#d4edda,stroke:#28a745,stroke-width:2px
    style A fill:#fff3cd,stroke:#ffc107,stroke-width:2px
    style O fill:#cce5ff,stroke:#007bff,stroke-width:2px
```

### 1.3 用 LAP 重新表达熟悉的概念

为了展示 LAP 的优雅性，我们来看看如何用 LAP 重新表达你最熟悉的 **ReAct/CodeAct 循环（如 OpenHands 的核心逻辑）**。

在传统的硬编码实现中，这通常是一个复杂的 `while` 循环，里面夹杂着各种 `if/else` 来处理 LLM 解析错误或工具执行错误。

而在 LAP 事件总线体系下，它只是三个极其干净的语义处理节点：

1.  **Context (Transformer 节点):**
    *   **语义契约：** `tool-observation` → `agent-state`
    *   **逻辑：** 无论什么工具输出，到达这里都必须被转换为 LLM 能理解的上下文状态。
2.  **LLM (Soft Anchor 软锚定):**
    *   **语义契约：** `agent-state` → `agent-action`
    *   **路由：** LLM 输出 Verdict。如果它决定完成任务（PASS），则将文本 Emit 出管线；如果它决定调用工具（FAIL 软校验），则路由给下一个硬锚点。
3.  **Tool (Hard Anchor 硬锚定):**
    *   **语义契约：** `agent-action` → `tool-observation`
    *   **天然可追踪与自愈：** 无论工具执行成功（PASS）还是失败遇到了 Error 堆栈（FAIL 附带 Diagnosis 诊断信息），LAP 都会将其路由回 `Context` 节点。LLM 会在下一轮中自动看到诊断信息并尝试自愈。

这种表达方式**将“业务实现”与“语义契约”完全解耦**。它极其通用、易于扩展，并且由于全程在 Event Bus 上流转，任何一个节点的 Verdict 都在天然且精细地被记录，为未来的模型微调和自我进化（Evolution Engine）提供了完美的温床。详情可查看 `examples/openhands_codeact_loop.py`。

## 2. 愿景：事件总线 (Event Bus) 与语义契约

我认为目前静态的图连线并不适合真正的自治 Agent，目前最好的系统架构形态是**事件总线（Event Bus）**。

LAP 不试图去规定一个 Agent 内部应该如何思考（那是 Agent 框架的事），LAP 定义的是流淌在事件总线上的**类型契约**。只要遵循了 LAP 协议中关于 Format（语义类型）和 Verdict（判定路由）的规范，由不同开发者编写的不同 Agent，就可以在同一个事件总线上无缝协作、相互验证，并进行宏观的系统级进化。

基于上述特性，LAP 有潜力（只是有潜力，或许并不是目前最好的，但它可能是一个解）成为**语义神经网络（Semantic Neural Networks）**的合理载体。
*> 值得一提的是，语义神经网络可以被视为符号神经网络（LNN）的语义化代餐。虽然它的节点不像传统符号神经网络的节点那样绝对确定，但是借由 LLM，它可以实现平滑的概率性过渡。*

## 3. 起源与探索

LAP 的诞生源于个人在构建 AI 应用时的一段探索与困惑。我曾尝试切换使用 Langflow、LangSmith (LangGraph)，参考过 n8n 和 Dify，研究了飞书开放平台、飞书 Anycross，甚至开始自己手写 LangGraphFlow，期间也深度阅读了像 OpenHands 这样的项目。

在这个过程中，我一直在思考一个问题：**为什么 AI 工作流有如此多样的表达形式，却缺乏一种通用的底层契约？**

我需要一种方式，能把任何需求、架构设计、代码、代码审查意见、Git 提交历史等，作为不同源但统一接口的“内容”来处理。如果没有通用契约，我就必须在诸多工具中选择一个，并对其产生极高的依赖（Vendor Lock-in）。更深层的问题在于，目前的流程图（Graph/Flow）大多是现有明确工作流的静态映射，它们其实不够灵活，无法让 Agent 真正自由地“开写”或自主决策。

虽然传统的流程图本质上也缺乏通用契约，但在大语言模型时代，处理的**核心对象统一了——都是“语言（Language）”**。既然处理对象统一了，就应该拥有一种通用的处理契约。

**我认为这个通用契约不应该有护城河。** 它太通用了。任何人对于 SOP（标准作业程序）和语义对象的理解，都应当能成为这个生态的养料。我不想让“中心化 AI 集群的自适应、高质量自动工作服务”成为少数企业的专属特权。

## 4. 寻求专业验证与探讨

这套由个人痛点驱动产生的架构构想，在我的 OmniFactory 实验中解决了很多传统架构耦合的问题。但我深知，要成为一个真正的“协议”，它必须经得起工程界和学术界的严格推敲。

在讨论中，许多资深工程师第一时间会对这种“基于语义路由的事件总线”提出两个经典的工程质疑：
1.  **状态爆炸与死锁**：如果 LLM 反复生成不符合要求的产物，被硬锚点无限打回，Context 溢出了怎么办？
2.  **并发与一致性（脏写）**：在事件总线上，多个 Agent 并发修改同一个代码库，如何防范“脏提交”？

**LAP 的回答是：把传统的“工程问题”变成纯粹的“文字游戏（语义建模问题）”。**

在 LAP 看来，所有的不一致或错误，本质上都是**语义类型的缺失**（Type Error）：
*   **对于状态爆炸**：大模型没有物理内存概念。我们只需定义一个 `Hard Anchor: Length Checker`（字符长度校验器）。当原始状态 `raw-agent-state` 过长时，它产出 FAIL，并将其路由给 `Transformer: Context Compressor`（上下文压缩器），压缩完再变成符合要求的 `agent-state` 交给 LLM。（详见 `examples/openhands_full_loop.py`）
*   **对于并发与脏写**：在处理代码时，我们最终需要的不是 Agent 的口头宣称，而是一个**经过验证的 Git PR**。如果发生脏写，说明输出的语义是不准确的。因为在验证流的最后，必然存在一个需要强依赖 `Ground Truth`（基准真理）的 Validator（例如 Git 状态检查）。一旦缺失锁定或校验语义，它就无法通过。

由此，LAP 协议进一步引申出了一个极其重要的元定义：**基准真理面（Ground Truth Surface）**。

这个概念听起来很玄，但其实就是指**“谁才是最后说了算的”**。在 LAP 空间中，系统信心的上限（Confidence = 1.0）只能来源于严格的外部真理，而不是 LLM 的自我宣称：
*   **已有代码 / Git 状态**（代码源真理）
*   **互联网信息**（人类源真理）
*   **传感器与执行器返回**（物理源真理）
*   **数学定理与编译器**（逻辑源真理）

所有的软锚定（LLM）都在向硬锚定（这些真实世界的 Ground Truth）逼近并坍缩。

我非常希望就这些问题与您进行更深入的探讨。如果您觉得将传统系统工程问题“语义化”是一条可行的路，或者您发现了其中的逻辑漏洞，请随时提交 Issue 或参与讨论。

## 5. 规范文档与标准库

详细的协议规范位于 `specifications/` 目录下：

*   **[LAP 核心语义标准库 (中文)](specifications/LAP_STANDARD_LIBRARY_zh.md)** - 协议的“MIME Types”，定义了通用的 Format 树与语义标签表，用于不同 Agent 之间开箱即用的交流。
*   [LAP V0.1 核心规范 (中文)](specifications/LAP_V0.1_zh.md) - 基础理论与类型系统。
*   [LAP V0.2 核心规范 (中文)](specifications/LAP_V0.2_zh.md) - 高级路由、标签系统与基准真理面。

## 6. 参考实践

为了验证 LAP 的可行性，协议的首个参考实现项目（包含了符合协议的 Event Bus 体系和简单的演化引擎）还在 OmniFactory 项目中作为核心系统进行开发验证。
