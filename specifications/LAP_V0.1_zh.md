# Language Anchoring Protocol (LAP) — V0.1 Specification

> **状态**: Draft / V0.1
> **日期**: 2026-03-14
> **作者**: zhouhaowen
> **项目**: OmniFactory

---

## 目录

1. [需求来源](#1-需求来源)
2. [核心发现](#2-核心发现)
3. [协议原语](#3-协议原语)
4. [类型系统](#4-类型系统)
5. [协议运作方式](#5-协议运作方式)
6. [现有系统的 LAP 转换](#6-现有系统的-lap-转换)
7. [愿景](#7-愿景)
8. [待校验指标](#8-待校验指标)

---

## 1. 需求来源

### 1.1 根问题

LLM（Large Language Model）的 L 代表什么？**Language**。

LLM 的本质是一个概率语言生成器——给定输入序列，输出下一个 token 的概率分布。它不保证输出正确、不保证输出可用、不保证输出安全。

然而我们围绕 LLM 构建了整个产业：代码生成、对话系统、自动化 Agent、内容创作……**所有这些应用做的事情，归根结底只有一件——把概率输出锚定为确定性的、可靠的产物。**

- Structured Output (JSON mode) 是锚定——约束 token 采样空间
- Tool Use / Function Calling 是锚定——约束输出为合法的函数调用
- 编译器是锚定——验证代码语法和类型正确性
- 测试套件是锚定——验证代码行为正确性
- 人工审查是锚定——验证产物满足业务意图
- CI/CD Pipeline 是锚定——验证产物满足部署条件

**它们是同一个动作的不同实例。但没有人给这个动作命名，没有人给它定义协议。**

### 1.2 现有工具的碎片化

| 工具 | 锚定的层 | 局限 |
|------|---------|------|
| Outlines / SGLang | token 级语法约束 | 只管结构，不管语义；需要 logit 访问 |
| Instructor / Pydantic | JSON schema 校验 + 重试 | 只有一层校验；没有链式判定 |
| Guardrails AI | 可组合的 validator 链 | Python 绑定；不是协议是库 |
| DSPy | 签名 + 断言 + 自动优化 | 学术导向；断言是布尔型 |
| NeMo Guardrails | 对话行为策略 | 仅限对话场景 |

**每个工具解决一个碎片。没有人定义统一的协议层。**

这就像 HTTP 出现之前，每个公司用自己的方式在网络上传输文档。
这就像 LSP 出现之前，每个编辑器用自己的方式与语言工具通信。
这就像 MCP 出现之前，每个 Agent 框架用自己的方式访问工具。

**MCP 标准化了输入侧（LLM 如何访问工具）。输出侧（LLM 产物如何被验证和路由）仍是空白。**

LAP 填补这个空白。

### 1.3 直接触发

在构建 OmniFactory（AI 原生软件工厂）的过程中，我们需要让多个 Agent 在事件总线上协作完成软件工程任务。每个 Agent 的每一步决策都需要被观测、验证、可能被干预。我们发现：Agent 的 step 循环本质上就是两个锚点的交替——LLM 决策（软锚定）和工具执行（硬锚定）。这个发现从具体场景出发，逐步抽象为通用协议。

---

## 2. 核心发现

### 2.1 发现一：锚定的原子结构

所有锚定操作都可以分解为一个二元结构：

```
Anchor = (Format, Validator → Verdict → Route)
```

- **Format**：定义判定器的输入结构——"LLM 应该输出什么形态的东西"
- **Validator**：判定输出是否合格——"这个输出满不满足约束"
- **Route**：根据判定结果决定下一步——"合格去哪、不合格去哪"

这是不可再分割的原子单位。任何更小的拆分都会丢失锚定的完整语义。

### 2.2 发现二：Agent 系统是锚点计数问题

Agent 系统的可靠性本质上由**锚点数量和质量**决定：

```
0 锚点 = 裸 LLM 输出          — 纯概率，不可靠
1 锚点 = 人工检查              — 可靠但不可扩展
2 锚点 = Agent 循环            — 最小自治单元
N 锚点 = 生产级管线            — 趋近确定性
```

**双锚点是最小自治单元**——少于两个锚点无法形成自主循环：

```
┌──────────────────┐          ┌──────────────────┐
│   Anchor_LLM     │          │   Anchor_Tool    │
│   (软锚定)        │ ──tool──▶│   (硬锚定)       │
│                  │ ◀──obs── │                  │
│ LLM 判定:         │          │ Tool 判定:       │
│ "接下来该做什么"    │          │ "调用是否合法"    │
│                  │          │ "执行结果是什么"   │
└───────┬──────────┘          └──────────────────┘
        │ finish
        ▼
    Pipeline Exit
```

这解释了为什么 2023 年之前没有真正的 Agent：不是模型不够强，而是 function calling（第二锚点）还没有被标准化。

### 2.3 发现三：锚点有硬/软之分

| | 硬锚定器 (Hard Anchor) | 软锚定器 (Soft Anchor) |
|---|---|---|
| 性质 | 确定性判定，可证明 | 概率性判定，不可证明 |
| 例子 | JSON Schema、编译器、测试 | LLM-as-judge、人工审查 |
| 保证 | 同一输入永远同一结果 | 同一输入可能不同结果 |
| 角色 | 守门员 | 决策者 |

**行业演进方向 = 不断用硬锚定器替换/增强软锚定器**：
- "LLM 觉得代码对了" (软) → pytest 跑过了 (硬)
- "LLM 觉得安全" (软) → 安全扫描通过 (硬)

### 2.4 发现四：Format 是语义类型，不是结构定义

这是最关键的发现。

Format 不是 "JSON Schema" 那种结构约束。Format 携带**语义**——它描述的不是"字段叫什么"，而是"这个东西是什么"。

在 Agent 循环中，流过管线的东西语义上始终是同一个东西——**需求（Requirement）**，只是状态在变：

```
输入:              未检验的需求 (raw requirement)
输出带 Tool:       未完成但可继续的需求 (in-progress requirement)
输出不带 Tool:     已完成或无法完成的需求 (resolved requirement)
```

推而广之，代码、文档、测试、部署产物——它们都是 Format，都是需求在经过不同锚定后的变体形态：

```
Requirement → Spec → Code → TestResult → Deployment
    "意图"     "规格"  "实现"  "验证报告"   "运行态"
```

**它们之间存在衍生与转移关系。** Code 不等于 Requirement，但 Code 是基于 Requirement 衍生出来的实现。在每次状态转移中（比如从需求到代码），都伴随着**语义的坍缩与潜在的丢失**。这意味着——

### 2.5 发现五：这是一个类型系统与流转图

当 Format 是类型、Anchor 是函数时，我们得到的不是一个简单的协议——而是一个**带有明确转换规则的类型系统**：

```
Format          = 语义类型
Anchor          = 带类型签名的函数 (Format_in → Format_out)
Transformer     = 类型转换器 (LLM 驱动的隐式/显式转换，伴随语义损失风险)
Pipeline        = 程序 (类型安全的函数组合)
类型检查        = 编译期错误检测
```

**深刻的纠正：区分“继承(Inheritance)”与“衍生(Derivation)”**

在最初的构想中，我们容易混淆“继承”与“流转”。在 LAP 的严格定义中：

*   **继承 (Is-A, 结构继承)**：表达包含关系。例如：`PythonCode` 继承自 `Code`；`ArtRequirement` 继承自 `Requirement`。子类完全包含父类的语义。
*   **衍生 (Derives-From, 语义转移)**：表达流水线中的因果关系。例如：`Code` 衍生自 `Requirement`。`Code` **并不是** `Requirement`，它丢失了需求中的“Why（为什么做）”，只保留了“How（怎么做）”。

**TypeScript 给 JavaScript 的无类型混沌加上了类型系统。LAP 给 LLM 管线的无类型混沌加上了基于继承和衍生规则的语义流转网络。**

---

## 3. 协议原语

LAP 由五个原语构成。不多不少。

### 3.1 Format — 语义类型

```
Format = {
    id:            唯一标识
    name:          人类可读名称
    description:   自然语言语义描述 (协议的"语言锚定"之根)
    parent:        父类型 ID (严格的 Is-A 继承链, null = 根类型)
    schema:        可选的结构约束 (JSON Schema)
    examples:      示例实例
}
```

**Format 是 LAP 的灵魂。** 它回答："流过管线的这个东西是什么？"

Format 之间的 `parent` 必须是严格的**结构与语义包含关系**：

```text
严格继承树 (Is-A):
Requirement
├── FeatureRequirement   "功能性需求"
└── BugfixRequirement    "修复性需求"

Code
├── PythonCode           "Python 源代码"
└── BashScript           "Bash 脚本"

文档与规格
├── Spec                 "结构化规格"
└── APIDoc               "API 接口文档"
```

而流转关系则由 Pipeline 中的 Transformer 来定义：`Requirement => Spec => Code`。

### 3.2 Verdict — 判定结果

```
Verdict = {
    kind:       PASS | FAIL | PARTIAL
    output:     判定通过的产物 (PASS 时) 或中间态 (PARTIAL 时)
    diagnosis:  失败诊断信息 (FAIL/PARTIAL 时)
    details:    结构化的判定细节
}
```

Verdict 不是布尔值。它携带**诊断信息**——这是反馈回路的关键。当 FAIL 发生时，diagnosis 描述了"为什么不行"，这个信息会被路由回 LLM，使其能针对性地自我修正。

三种判定结果的语义：

| Kind | 含义 | 类比 |
|------|------|------|
| PASS | 输出满足约束，锚定成功 | 编译通过 |
| FAIL | 输出不满足约束，需要外部处理 | 编译失败 + 错误信息 |
| PARTIAL | 部分满足，可以继续 | 警告但不阻断 |

### 3.3 Anchor — 锚点

```
Anchor = {
    id:          唯一标识
    name:        人类可读名称
    format_in:   输入类型 (Format ID)
    format_out:  输出类型 (Format ID)
    validator:   判定器规约 {
        kind:        HARD | SOFT
        description: 自然语言描述
    }
    routes: {
        PASS:    Route (下一步)
        FAIL:    Route (失败处理)
        PARTIAL: Route (部分处理)
    }
}
```

Anchor 是 LAP 的原子执行单位。它回答三个问题：
1. **输入长什么样？** → `format_in`
2. **怎么判定？** → `validator`
3. **判定后往哪走？** → `routes`

Anchor 是有类型签名的：`format_in → format_out`。这使得类型检查成为可能。

### 3.4 Transformer — 类型转换器

```
Transformer = {
    id:          唯一标识
    name:        人类可读名称
    from_format: 源类型 (Format ID)
    to_format:   目标类型 (Format ID)
    method:      转换方式 (LLM | RULE | HYBRID)
    description: 自然语言描述转换逻辑
}
```

当两个 Anchor 的输出/输入类型不直接匹配但存在语义继承关系时，需要一个 Transformer 做类型转换。

**Transformer 的关键特性：它由 LLM 驱动。** 传统类型系统的类型转换（如 `parseInt`）是确定性的。LAP 的类型转换是概率性的——因为语义转换本身就是 LLM 最擅长的事情。

```
Transformer: ChatMessage → Spec
    "用户说'帮我修个登录的 bug'→ 结构化的 BugSpec"
    method: LLM
    这个转换本身就是一次软锚定。

Transformer: Spec → Code
    "将需求规格转换为可执行代码"
    method: LLM
    这个转换就是"编程"。

Transformer: Code → Doc
    "将代码转换为文档"
    method: LLM | RULE (部分可由 AST 提取确定性生成)
    method = HYBRID。
```

**深刻的洞察：传统软件工程中被认为是"创造性工作"的编程、写文档、设计测试——在 LAP 框架下都只是 Transformer。** 它们是 Format 之间的类型转换，由 LLM 作为通用转换引擎驱动。

### 3.5 Pipeline — 类型安全的组合

```
Pipeline = {
    id:          唯一标识
    name:        人类可读名称
    description: 管线用途描述
    nodes:       Anchor 和 Transformer 的列表
    edges:       节点间的连接 (必须类型安全)
    entry:       入口节点 ID
}
```

Pipeline 是 Anchor 和 Transformer 的有向组合图——LAP 的"程序"。

**Pipeline 的关键约束：类型安全。** 每条边的源节点 `format_out` 必须与目标节点 `format_in` 兼容（相同或可通过继承关系转换）。不兼容的连接在"编译期"（管线构建时）就会被拒绝。

```
Pipeline "Fix a Bug" (合法):

  ChatMessage ──[Transformer]──▶ Spec ──[Anchor_Coder]──▶ Code
                ChatMessage→Spec     Spec→Code              │
                                                             ▼
                                     Deployment ◀──[Anchor_Deploy]
                                                  Code×TestResult→Deployment
                                                             ▲
                                     TestResult ──[类型匹配 ✓]─┘
                                         ▲
                                   [Anchor_Tester]
                                      Code→TestResult

Pipeline "Invalid" (非法):

  TestResult ──▶ Anchor_Coder
                 输入要求 Spec, 但收到 TestResult
                 TestResult ⊄ Spec (无继承关系)
                 → 类型错误！管线构建失败。
```

---

## 4. 类型系统

### 4.1 类型兼容性规则

```
COMPATIBLE(A, B) =
    A == B                           -- 直连 (短路)
    OR A <: B                        -- A 是 B 的子类型, 自动向上转型
    OR EXISTS Transformer(A → B)     -- 显式转换可用
```

当 `COMPATIBLE(A, B)` 为 false 时，管线构建失败。这是 LAP 的"编译器"。

### 4.2 子类型关系 (<:)

子类型关系由 Format 的继承链决定，必须遵循严格的语义包含（Is-A）：

```
PythonCode <: Code
意味着:
  需要 Code 的地方可以传入 PythonCode（PythonCode 是 Code 的一种）
  需要 PythonCode 的地方不能传入普通的 Code
```

这是**协变（covariant）**子类型：子类型可以替代父类型，反之不行。

### 4.3 Transformer 作为语义转换（伴随丢失）

当类型在流水线中发生实质性的状态转移（如衍生）时，必须插入 Transformer：

```
逻辑转换流 (基于依赖):
  Requirement → Spec      (需求分析)
  Spec → Code             (编程实现)
  Code → TestResult       (测试执行)
```

**关键洞察：Transformer 操作本质上是有损的转移。** 
从 `Requirement` 到 `Code`，需求中宏观的业务背景被丢弃，坍缩为具体的代码逻辑。
因此，Transformer 是一次极其危险的软锚定。这就引出了 LAP 协议的一条**根本性铁律 (Fundamental Rule)：所有的输出必须绝对忠实于输入（Semantic Fidelity）**。
格式的转换绝不能成为“夹带私货”或“遗漏条件”的借口。即使丢失了上游的宏观上下文，产出的结果也必须是输入意图的无损投影。这意味着任何 Transformer 后面，都应当紧跟着负责校验“语义忠实度”的锚点。

### 4.4 类型推断

在某些场景下，Pipeline 可以自动推断需要插入哪些 Transformer：

```
用户声明: ChatMessage ──▶ Deployment
系统推断:
  ChatMessage ──[T1]──▶ Spec ──[T2]──▶ Code ──[A1]──▶ TestResult
       T1: ChatMessage→Spec           T2: Spec→Code      │
       (需求理解)                      (编程)              ▼
                                              Deployment ◀─[A2]
                                              A2: Code×TestResult→Deployment
                                              (部署)
```

**这就是"自然语言编程"的真正含义——不是让 LLM 写代码，而是让用户声明起点和终点类型，系统自动推断中间的转换链。**

---

## 5. 协议运作方式

### 5.1 静态阶段：管线构建

```
1. 用户/系统声明一组 Anchor 和 Transformer
2. 声明它们之间的连接（边）
3. 类型检查器验证每条边的类型兼容性:
   - 兼容 → 通过
   - 不兼容但可转换 → 自动插入 Transformer
   - 不兼容且不可转换 → 报错
4. 产出: 类型安全的 Pipeline 定义
```

### 5.2 动态阶段：管线执行

```
1. 输入数据从入口节点进入，携带 Format 类型标签
2. 当前节点 (Anchor) 执行:
   a. 验证输入是否匹配 format_in (硬检查)
   b. 调用 Validator 判定
   c. 产出 Verdict (PASS / FAIL / PARTIAL)
3. 根据 Verdict 查路由表:
   - PASS  → 前进到下一节点 (或 EMIT 退出)
   - FAIL  → 按路由处理 (RETRY / JUMP / HALT)
   - PARTIAL → 继续或分支
4. 如果下一节点需要类型转换，经过 Transformer
5. 重复直到 Pipeline 到达出口 (EMIT) 或终止 (HALT)
```

### 5.3 运行时事件

Pipeline 执行过程中的每一步都产生事件（与 OmniFactory 的 FactoryEvent 对齐）：

```
ANCHOR_ENTER     — 进入锚点
ANCHOR_VERDICT   — 锚点产出判定
ANCHOR_ROUTE     — 路由决定
TRANSFORM_BEGIN  — 开始类型转换
TRANSFORM_END    — 类型转换完成
PIPELINE_EMIT    — 管线产出最终结果
PIPELINE_HALT    — 管线异常终止
```

### 5.4 示例：双锚点 Agent 循环

用 LAP 描述标准的 Agent 循环（目前所有 Agent 框架做的事）：

```yaml
pipeline:
  id: "agent-loop"
  name: "Standard Agent Loop"
  entry: "anchor-llm"

  formats:
    - id: "run-state"
      name: "AgentRunState"
      description: "未完成的需求 + 已有的行动观察历史"
      parent: "requirement"

    - id: "action"
      name: "AgentAction"
      description: "LLM 的决策输出 (tool_call / think / finish)"
      parent: "requirement"

    - id: "observation"
      name: "ToolObservation"
      description: "工具执行后的观察结果"
      parent: "requirement"

  anchors:
    - id: "anchor-llm"
      name: "LLM Decision (Soft)"
      format_in: "run-state"
      format_out: "action"
      validator:
        kind: SOFT
        description: "LLM 根据当前状态决定下一步行动"
      routes:
        PASS:    { action: EMIT }              # finish/reject → 退出
        PARTIAL: { action: NEXT, target: self } # think → 记录，重新进入
        FAIL:    { action: NEXT, target: "anchor-tool" } # tool_call → 需要硬锚定

    - id: "anchor-tool"
      name: "Tool Execution (Hard)"
      format_in: "action"
      format_out: "observation"
      validator:
        kind: HARD
        description: "校验工具调用合法性，执行工具，返回结果"
      routes:
        PASS: { action: JUMP, target: "anchor-llm" }  # 成功 → 回到 LLM
        FAIL: { action: JUMP, target: "anchor-llm" }  # 失败 → 也回到 LLM（带诊断）

  transformers:
    - id: "obs-to-state"
      from_format: "observation"
      to_format: "run-state"
      method: RULE
      description: "将观察结果追加到 AgentRunState.history"
```

注意 `anchor-tool` 的 PASS 和 FAIL 都路由回 `anchor-llm`——因为无论工具成功还是失败，LLM 都需要看到结果并做下一步决策。**区别在于 Verdict 携带的 diagnosis：成功时是观察结果，失败时是错误信息。**

---

## 6. 现有系统的 LAP 转换

### 6.1 ChatGPT 对话 = 单锚点管线

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
        description: "人类阅读并判断 LLM 回复是否满意"
      routes:
        PASS: { action: EMIT }
        FAIL: { action: RETRY, feedback: "用户的修正指令" }
```

一个锚点，一个人类。最原始的 LAP 实例。

### 6.2 OpenAI Function Calling = 双锚点管线

```yaml
pipeline:
  id: "function-calling"
  entry: "anchor-llm"

  anchors:
    - id: "anchor-llm"
      format_in: "conversation"
      format_out: "function-call-or-text"
      validator: { kind: SOFT, description: "LLM 决定是否调用函数" }
      routes:
        PASS: { action: EMIT }                           # 纯文本回复
        FAIL: { action: NEXT, target: "anchor-schema" }  # 函数调用

    - id: "anchor-schema"
      format_in: "function-call"
      format_out: "validated-call"
      validator: { kind: HARD, description: "JSON Schema 校验函数参数" }
      routes:
        PASS: { action: EMIT }    # 参数合法 → 执行
        FAIL: { action: RETRY }   # 参数非法 → 重新采样
```

### 6.3 SWE-Agent (代码修复) = 多锚点管线

```yaml
pipeline:
  id: "swe-agent"
  entry: "anchor-planner"

  anchors:
    - id: "anchor-planner"
      format_in: "issue"              # GitHub Issue (Ticket <: Requirement)
      format_out: "action"
      validator: { kind: SOFT, description: "LLM 规划修复策略" }
      routes:
        PASS:    { action: NEXT, target: "anchor-submit" }
        FAIL:    { action: NEXT, target: "anchor-tool" }
        PARTIAL: { action: NEXT, target: self }

    - id: "anchor-tool"
      format_in: "action"
      format_out: "observation"
      validator: { kind: HARD, description: "执行 bash/edit 命令" }
      routes:
        PASS: { action: JUMP, target: "anchor-planner" }
        FAIL: { action: JUMP, target: "anchor-planner" }

    - id: "anchor-submit"
      format_in: "code-patch"
      format_out: "pr"
      validator: { kind: HARD, description: "git diff 格式校验 + 提交 PR" }
      routes:
        PASS: { action: NEXT, target: "anchor-ci" }
        FAIL: { action: JUMP, target: "anchor-planner" }

    - id: "anchor-ci"
      format_in: "pr"
      format_out: "test-result"
      validator: { kind: HARD, description: "CI 运行测试套件" }
      routes:
        PASS: { action: EMIT }                           # 测试通过 → 完成
        FAIL: { action: JUMP, target: "anchor-planner" } # 测试失败 → 回到 LLM

  transformers:
    - id: "issue-to-context"
      from_format: "issue"
      to_format: "run-state"
      method: LLM
      description: "解析 Issue，提取复现步骤和代码位置"
```

注意 SWE-Agent 比基础 Agent 多了两个硬锚定器（git + CI）。**每多一个硬锚定器，系统的可靠性就上升一个台阶。**

### 6.4 Guardrails AI = 判定器链

```yaml
pipeline:
  id: "guardrails"
  entry: "anchor-format"

  anchors:
    - id: "anchor-format"
      format_in: "llm-output"
      format_out: "parsed-output"
      validator: { kind: HARD, description: "JSON 解析 + Schema 校验" }
      routes:
        PASS: { action: NEXT, target: "anchor-toxicity" }
        FAIL: { action: RETRY, feedback: "schema 错误信息" }

    - id: "anchor-toxicity"
      format_in: "parsed-output"
      format_out: "safe-output"
      validator: { kind: SOFT, description: "毒性检测 (LLM-as-judge)" }
      routes:
        PASS: { action: NEXT, target: "anchor-factuality" }
        FAIL: { action: RETRY, feedback: "内容包含不当表述" }

    - id: "anchor-factuality"
      format_in: "safe-output"
      format_out: "verified-output"
      validator: { kind: SOFT, description: "事实性验证 (RAG 检索)" }
      routes:
        PASS: { action: EMIT }
        FAIL: { action: RETRY, feedback: "以下声明无法被验证: ..." }
```

Guardrails AI 的 validator 链 = LAP 中的**串行多锚点管线**。但 Guardrails 没有类型系统，没有 Transformer，也没有路由到不同分支的能力。

### 6.5 CI/CD Pipeline = 纯硬锚定管线

```yaml
pipeline:
  id: "cicd"
  entry: "anchor-build"

  anchors:
    - id: "anchor-build"
      format_in: "code"
      format_out: "binary"
      validator: { kind: HARD, description: "编译器" }
      routes:
        PASS: { action: NEXT, target: "anchor-test" }
        FAIL: { action: HALT, feedback: "编译错误" }

    - id: "anchor-test"
      format_in: "binary"
      format_out: "test-result"
      validator: { kind: HARD, description: "测试套件" }
      routes:
        PASS: { action: NEXT, target: "anchor-security" }
        FAIL: { action: HALT, feedback: "测试失败" }

    - id: "anchor-security"
      format_in: "binary"
      format_out: "security-report"
      validator: { kind: HARD, description: "安全扫描" }
      routes:
        PASS: { action: NEXT, target: "anchor-deploy" }
        FAIL: { action: HALT, feedback: "安全漏洞" }

    - id: "anchor-deploy"
      format_in: "binary"
      format_out: "deployment"
      validator: { kind: HARD, description: "部署健康检查" }
      routes:
        PASS: { action: EMIT }
        FAIL: { action: HALT, feedback: "部署失败，回滚" }
```

CI/CD 是**纯硬锚定管线**——没有任何软锚定器。这是 LLM 出现之前人类构建的锚定管线。LAP 的贡献是让软锚定器（LLM）可以自然地插入这条管线的任何位置。

---

## 7. 愿景

### 7.1 短期：OmniFactory 的协议基础

LAP 为 OmniFactory 提供：
- Agent step 循环的形式化描述（双锚点管线）
- 多 Agent 协作的类型安全组合
- 管线可观测性的统一事件模型
- 影子干预的自然挂载点（在任意 Anchor 之间插入 Intervention Anchor）

### 7.2 中期：MCP 的对偶协议

```
MCP = 输入侧标准化 (LLM 如何访问外部能力)
LAP = 输出侧标准化 (LLM 产物如何被验证和路由)
```

MCP 回答："LLM 可以用什么工具？"
LAP 回答："LLM 的输出该怎么检验？"

二者互补，覆盖 LLM 与外部世界交互的完整表面。

### 7.3 长期：大语言编程模型

LAP 不只是一个协议——它是一种**编程范式**：

- **Format 是类型**：描述数据的语义
- **Anchor 是函数**：接收类型、产出类型、带有验证逻辑
- **Transformer 是类型转换**：LLM 驱动的语义转换
- **Pipeline 是程序**：类型安全的函数组合
- **类型检查是编译器**：在管线构建时捕获错误

在这个范式下：
- "编程" = 声明 Format 之间的 Transformer
- "测试" = 添加硬锚定器到管线中
- "调试" = 检查管线中哪个 Anchor 的 Verdict 不符合预期
- "重构" = 重组 Anchor 和 Transformer 的连接方式
- "需求分析" = 定义入口 Format 和出口 Format

**用户只需要声明"从这个类型到那个类型"，系统自动推断中间需要哪些 Transformer 和 Anchor——这就是自然语言编程的真正形态。**

---

## 8. 待校验指标

LAP V0.1 是理论框架。在进入 V0.2 之前，需要通过以下实验验证其有效性：

### 8.1 原语完备性

**问题**: 五个原语（Format, Verdict, Anchor, Transformer, Pipeline）是否足以描述所有已知的 LLM 锚定场景？

**验证方法**: 尝试用 LAP 描述以下场景，检查是否有无法表达的情况：

| 场景 | 复杂度 | 验证重点 |
|------|--------|---------|
| JSON Structured Output | 最低 | 单锚点硬判定 |
| ChatGPT + 人工审查 | 低 | 单锚点软判定 + RETRY 路由 |
| ReAct Agent | 中 | 双锚点循环 |
| SWE-Agent + CI | 高 | 多锚点 + 多 Transformer |
| 多 Agent 协作 | 最高 | Pipeline 嵌套、类型推断 |

**通过标准**: 全部场景可描述，且描述比自然语言更精确、比代码更简洁。

### 8.2 类型系统有效性

**问题**: 类型检查能否在管线构建时捕获真实的配置错误？

**验证方法**:
1. 故意构建类型不安全的管线（如将 TestResult 直接连到 Coder）
2. 检查类型检查器是否报错
3. 检查错误信息是否有指导意义（"需要插入 Transformer: TestResult → Spec"）

**通过标准**: 100% 的类型错误被捕获；0% 的合法管线被误报。

### 8.3 Transformer 可行性

**问题**: LLM 驱动的类型转换在实践中的成功率和成本如何？

**验证方法**: 对以下 Transformer 做基准测试：

| Transformer | 成功率目标 | 成本约束 |
|-------------|-----------|---------|
| ChatMessage → Spec | > 80% | < $0.01/次 |
| Spec → Code | > 60% | < $0.10/次 |
| Code → TestPlan | > 70% | < $0.05/次 |
| Code → Doc | > 90% | < $0.02/次 |

**通过标准**: 核心 Transformer 的单次成功率 > 60%；配合 RETRY 路由后 > 90%。

### 8.4 协议开销

**问题**: LAP 的类型检查和事件发射是否引入不可接受的运行时开销？

**验证方法**: 对比有/无 LAP 的 Agent 循环执行时间。

**通过标准**: LAP 开销 < 总执行时间的 1%（因为 LLM 调用是秒级，LAP 操作是微秒级）。

### 8.5 可读性

**问题**: LAP 管线定义是否比等价的代码/配置更容易理解？

**验证方法**: 让不了解 LAP 的工程师分别阅读：
1. 一段 Agent 循环的 Python 代码
2. 等价的 LAP Pipeline YAML 定义

要求他们回答："这个管线在什么情况下会失败？"

**通过标准**: LAP 组的正确率 > 代码组。

### 8.6 与现有生态的互操作

**问题**: LAP 能否作为"描述层"覆盖在现有工具之上，而不要求它们重写？

**验证方法**: 为以下现有工具编写 LAP adapter：
- Guardrails AI → LAP Anchor
- DSPy Module → LAP Anchor
- MCP Tool → LAP Anchor (format_in = tool params, validator = tool execution)
- pytest → LAP Anchor (format_in = code, validator = test suite)

**通过标准**: Adapter 代码 < 50 行；不修改原工具代码。

---

## 附录 A：术语表

| 术语 | 定义 |
|------|------|
| **Anchor（锚点）** | LAP 的原子执行单位。`(Format_in, Validator, Routes) → Format_out`。将概率性输出锚定为确定性产物。 |
| **Format（格式/类型）** | 流过管线的数据的语义类型。不只描述结构，更描述语义（"这是什么"）。 |
| **Verdict（判定）** | Validator 的输出。`PASS / FAIL / PARTIAL` + 诊断信息。 |
| **Validator（判定器）** | 执行锚定判定的组件。分硬（确定性）和软（概率性）两种。 |
| **Route（路由）** | 判定结果到下一步行动的映射。`NEXT / RETRY / JUMP / EMIT / HALT`。 |
| **Transformer（转换器）** | Format 之间的类型转换器。通常由 LLM 驱动。是软锚定的一种特殊形式。 |
| **Pipeline（管线）** | Anchor 和 Transformer 的有向类型安全组合。LAP 的"程序"。 |
| **硬锚定（Hard Anchoring）** | 确定性判定。编译器、JSON Schema、测试套件。可证明。 |
| **软锚定（Soft Anchoring）** | 概率性判定。LLM-as-judge、人工审查。不可证明。 |
| **语义继承** | Format 之间的子类型关系。Code <: Spec <: Requirement。子类型保持父类型的意图语义但改变表达结构。 |

## 附录 B：与现有协议的关系

```
              ┌──────────────────────────────────────────┐
              │          应用层 (Applications)            │
              │  Agent / 代码生成 / 对话 / 自动化          │
              ├──────────────────────────────────────────┤
              │    LAP (Language Anchoring Protocol)      │  ← 本协议
              │    输出验证 + 类型安全路由                  │
              ├──────────────────────────────────────────┤
              │    MCP (Model Context Protocol)           │
              │    输入标准化 (工具/资源访问)               │
              ├──────────────────────────────────────────┤
              │    LLM API (OpenAI / Anthropic / ...)    │
              │    模型推理接口                            │
              ├──────────────────────────────────────────┤
              │    传输层 (HTTP / WebSocket / gRPC)       │
              └──────────────────────────────────────────┘
```

---

*LAP V0.1 — 2026-03-14 — Draft*
