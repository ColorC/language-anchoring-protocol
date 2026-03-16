# LAP 核心语义标准库 (Standard Semantic Library)

> **状态**: Draft
> **用途**: 类似于 HTTP 的 MIME Types，本标准库定义了 LAP 协议中最常见、最具通用性的 `Format` (语义类型) 和 `Tags` (语义标签)，以便不同的 Agent 之间能够达成开箱即用的语义共识。

---

## 1. 核心 Format 分类与演变

在 LAP 中，我们关注两个维度：一个是数据**“本身是什么分类”**（结构继承），一个是数据在流程中**“如何演变形态”**（语义衍生）。所有在事件总线上流淌的数据都必须有一个明确的基础身份。

### 1.1 数据分类树 (Is-A：它是什么)

```text
1. Requirement (需求/意图类)
   ├── FeatureRequirement (新功能需求)
   ├── BugfixRequirement  (改 Bug 需求)
   ├── ChatMessage        (对话式的输入)
   └── Ticket             (来自工单系统的意图)

2. Spec (方案/规格类)
   ├── TaskSpec           (带验收标准的任务书)
   ├── Doc                (给人读的文档)
   └── APIDoc             (给机器读的接口定义)

3. Code (实现/逻辑类)
   ├── CodePatch          (代码改动/Diff)
   └── Binary             (编译出来的二进制)

4. Verification (验证/报告类)
   ├── TestPlan           (测试怎么做的方案)
   ├── TestResult         (测试跑出来的报告)
   ├── TestVerdict        (判定结果/外部真理)
   └── CISignal           (流水线信号)

5. AgentRuntime (运行时状态)
   ├── AgentState         (Agent 脑子里的上下文)
   ├── AgentAction        (Agent 决定要干啥，如调工具)
   └── ToolObservation    (工具执行完返回的结果)
```

### 1.2 语义演变路径 (Derives-From：怎么变身)

数据在流水线中会通过 Transformer 发生形态转换。**注意：转换过程中可能会丢失原始意图的细节**，因此必须通过后续的“检查站（Anchor）”来把关，确保产物依然忠实于原始需求。
典型路径：`需求 (Requirement) => 方案 (Spec) => 代码 (Code) => 结果 (TestResult)`

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

### 3.3 进化与自我修复 (Evolution Engine)

*   `evolution.residual`: 标记为“残差”，即管线内自洽但被物理世界打脸的数据，需要触发系统进化。
*   `evolution.attribution`: 语义归因结果，标明是由于过度生成(MORE)、缺失(LESS)还是错误(WRONG)导致的问题。

---

*随着协议的发展，此标准库将通过社区提案不断扩充。*
