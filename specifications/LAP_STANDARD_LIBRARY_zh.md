# LAP 核心语义标准库 (Standard Semantic Library)

> **状态**: Draft
> **用途**: 类似于 HTTP 的 MIME Types，本标准库定义了 LAP 协议中最常见、最具通用性的 `Format` (语义类型) 和 `Tags` (语义标签)，以便不同的 Agent 之间能够达成开箱即用的语义共识。

---

## 1. 核心 Format 分类与流转

在 LAP 中，我们严格区分“结构继承 (Is-A)”与“语义衍生 (Derives-From)”。所有在事件总线上流淌的数据都属于某个基础大类，并且通过 Transformer 跨大类流转。

### 1.1 结构继承树 (Is-A)

```text
1. Requirement (意图基类)
   ├── FeatureRequirement (功能需求)
   ├── BugfixRequirement  (修复需求)
   ├── ChatMessage        (对话形态输入)
   └── Ticket             (工单形态意图)

2. Spec (结构化规格基类)
   ├── TaskSpec           (带验证标准的任务规格)
   ├── Doc                (人类可读文档)
   └── APIDoc             (机器可读接口文档)

3. Code (可执行逻辑基类)
   ├── CodePatch          (代码补丁/Diff)
   └── Binary             (编译产物)

4. Verification (验证与报告基类)
   ├── TestPlan           (测试策略)
   ├── TestResult         (测试执行报告)
   ├── TestVerdict        (外部硬锚定测试结果/Ground Truth)
   └── CISignal           (持续集成信号)

5. AgentRuntime (运行时状态基类)
   ├── AgentState         (上下文)
   ├── AgentAction        (决策输出)
   └── ToolObservation    (工具反馈)
```

### 1.2 语义衍生路径 (Derives-From)

管线通过 Transformer 定义状态转移（伴随潜在的语义丢失，需要通过后续的 `semantic.faithful` 标签来验证）：
`Requirement => Spec => Code => TestResult`

## 2. 基础 Format 定义详解

### 2.1 需求与规格层
*   **`requirement`**: 一个有状态的意图。这是所有类型的基类。
*   **`spec`**: 将模糊的需求明确化为可执行的结构化规格。
*   **`task-spec`**: `[tags: task.input]` 包含任务描述文本 + 验证方式（如测试命令），通常用于 Benchmark 或确定性任务分发。

### 2.2 运行时层 (Agent Loop)
*   **`agent-state`**: 包含 Agent 当前指令、历史和上下文。是需求在运行时环境中的形态。
*   **`agent-action`**: Agent 根据 state 做出的单步决策（如 `tool_call`, `think`, `finish`）。
*   **`tool-observation`**: 物理世界（工具）对 `agent-action` 的回应。

### 2.3 产物层
*   **`code`**: 可执行的意图实现（源代码、配置）。
*   **`code-patch`**: `[tags: task.output]` Agent 对代码仓库的修改集合（如 diff）。
*   **`test-result`**: 包含通过/失败/跳过等状态的报告。

## 3. 标准语义标签 (Tags) 参考

在 LAP V0.2 中，Tags 用于跨越继承树定义非结构化的语义切面。

### 3.1 领域与语言 (Domain & Language)
*   `domain:frontend` / `domain:backend` / `domain:database` / `domain:devops`
*   `lang:python` / `lang:typescript` / `lang:rust` / `lang:go`

### 3.2 确信度与真理 (Ground Truth)
*   `ground-truth.hard`: 绝对物理真理。Confidence 永远视为 1.0（如编译器通过、外部 Pytest 通过）。
*   `ground-truth.human`: 人类审查通过。
*   `validation.syntax`: 通过了初步的语法校验，但尚未进行逻辑校验。
*   `validation.security`: 通过了代码安全扫描。

### 3.3 语义保真度 (Semantic Fidelity)

*   `semantic.faithful`: **语义无损/忠实**。表示该数据（如一段代码）已经被特定的 Anchor 验证过，它完美且忠实地实现了其上游来源（如一段需求）的意图。没有夹带私货，也没有遗漏。这是防御 Agent 产生幻觉或“无论输入什么都输出同样代码”的最重要标签。

### 3.4 进化与自我修复 (Evolution Engine)
*   `evolution.residual`: 标记为“残差”，即管线内自洽但被物理世界打脸的数据，需要触发系统进化。
*   `evolution.attribution`: 语义归因结果，标明是由于过度生成(MORE)、缺失(LESS)还是错误(WRONG)导致的问题。

---

*随着协议的发展，此标准库将通过社区提案不断扩充。*
