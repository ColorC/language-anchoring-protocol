# Language Anchoring Protocol (LAP) — V0.2 Specification

> **状态**: Draft / V0.2
> **日期**: 2026-03-15
> **作者**: LAP Protocol Authors
> **项目**: OmniFactory
> **变更**: 在 V0.1 基础上新增语义标签系统 (固有属性)、三层信息机制、未检验输入与入口守卫、confidence 三态语义、必要条件验证方法论、Format 类型精度

---

## 目录

1. [需求来源](#1-需求来源)
2. [核心发现](#2-核心发现)
3. [协议原语](#3-协议原语)
4. [类型系统](#4-类型系统)
5. [语义标签系统](#5-语义标签系统) *(V0.2 新增)*
6. [未检验输入与入口守卫](#6-未检验输入与入口守卫) *(V0.2 新增)*
7. [协议运作方式](#7-协议运作方式)
8. [现有系统的 LAP 转换](#8-现有系统的-lap-转换)
9. [最佳实践](#9-最佳实践) *(V0.2 新增)*
10. [愿景](#10-愿景)
11. [待校验指标](#11-待校验指标)

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

### 2.3 发现三：锚点有硬/软之分 —— 谁才是“说了算的”？

在流水线上，我们要区分两种不同力度的检查：

| | 硬检查 (Hard Anchor) —— **权威真相** | 软检查 (Soft Anchor) —— **语义猜测** |
|---|---|---|
| 性质 | **绝对真理**。机器说了算，结果非黑即白。 | **主观判定**。AI 或人说了算，结果有概率。 |
| 例子 | 编译器、JSON 校验、运行测试、Git 状态 | LLM 评分、人工代码审查、视觉美感判断 |
| 保证 | 同一输入永远同一结果 | 同一输入可能不同结果 |
| 角色 | **守门员**。守住系统底线。 | **决策者**。指引前进方向。 |

**核心洞察：系统信心的上限，永远取决于你引入了多少“权威真相”。**
- 仅仅“AI 觉得代码写得好”是不够的。
- 必须经过“编译器说语法没问题”和“测试说逻辑跑通了”这两层**现实硬基准**。
- **行业演进方向**：就是不断地用“硬性验证”去支撑“软性猜测”。

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
    "意图"     "方案"  "实现"  "验证报告"   "运行态"
```

**它们之间存在演变与转换关系。** Code 不等于 Requirement，但 Code 是基于 Requirement 转换出来的。在每次转换中（比如从需求到代码），**信息往往会变“窄”，或者丢掉一些背景细节**（因为代码无法表达需求里的所有心路历程）。这意味着——

### 2.5 发现五：这是一个带“质检”的类型流水线

当 Format 是类型、Anchor 是函数时，我们得到的不是一个简单的协议——而是一个**带有明确转换规则的类型系统**：

```
Format          = 语义类型 (它是啥)
Anchor          = 带类型签名的函数 (从 A 形态变到 B 形态，带校验)
Transformer     = 转换引擎 (LLM 驱动的自动翻译/编写)
Pipeline        = 程序 (一套完整的加工流水线)
类型检查        = 相当于“编译”，提前发现流程连错了没有
```

**深刻的纠正：区分“本身分类 (Is-A)”与“演变形态 (Derives-From)”**

在最初的构想中，我们容易混淆“分类”与“流程”。在 LAP 的严格定义中：

*   **分类 (Is-A，结构继承)**：表达“它是谁的儿子”。例如：`PythonCode` 属于 `Code`；`ArtRequirement` 属于 `Requirement`。
*   **演变 (Derives-From，形态转移)**：表达流水线里的先后关系。例如：`Code` 是从 `Requirement` 变过来的。**代码并不是需求**，它丢掉了需求里的“为什么”，只保留了具体的“怎么做”。

**TypeScript 给 JavaScript 的混乱加上了类型。LAP 给 AI 工作流的混乱加上了这套“变身规则”和“质检网络”。**

### 2.6 发现六：语义类型需要“侧面标签” *(V0.2 新增)*

V0.1 的类型系统只有一个维度——分类树（`Code <: Spec <: Requirement`）。但现实中的数据有**多个正交的属性**：

```
一份"代码差异" (code-diff) 可以有多个侧面:
  - 来源：来自 Git，还是 SVN？
  - 领域：属于前端，还是后端？
  - 状态：已通过审核，还是未审核？
  - 意图：为了修复安全漏洞，还是为了优化性能？
```

**分类树只能表达"它是啥"，不能表达"它处于什么状态"。** 如果把所有状态都塞进类型名里（比如叫 `git-frontend-reviewed-security-code-diff`），类型名会变得无法直视。

解决方案：**语义标签（Semantic Tags）**——给数据贴上可叠加的标签。

```
Format.id    = 本身分类 (它是啥，如 code-diff)
Format.tags  = 附加属性 (它处于什么状态，如 reviewed, security)
(id, tags)   = 它的完整身份
```

### 2.7 发现七：未经验证的输入是流水线的“隐患” *(V0.2 新增)*

一个管线声称自己接受 `code-diff` 作为输入。但谁能保证传进来的那串字符真的是 `code-diff`？

**在 LAP V0.1 中，我们默认“相信”输入。** 如果有人传了个假数据，管线会一直跑，直到某个下游节点因为读不到预期字段而崩溃。

为了堵住这个漏洞，V0.2 引入了**入口守卫（Entry Guard / 安检口）** 模式。所有进入管线的原始数据必须先经过“安检”，贴上“已验证”的标签，否则不准进入后续流程。

---

## 3. 协议原语

LAP 由五个原语构成。不多不少。

### 3.1 Format — 语义类型 *(V0.2 增强)*

```
Format = {
    id:                       唯一标识 (它是啥)
    name:                     人类可读名称
    description:              自然语言语义描述 (给 AI 和人读的“说明书”)
    parent:                   父类型 ID (分类树)
    schema:                   可选的结构约束 (JSON Schema)
    examples:                 示例

    # V0.2 新增
    tags:                     固有属性标签 (如该类型天生就属于 "source.vcs")
    semantic_preconditions:   成为该类型必须满足的硬指标 (给人看)
    required_tags:            输入必须已具备的标签 (安检要求)
}
```

**Format 是 LAP 的灵魂。** 它回答："流水线上跑着的这个东西，到底是什么？"

#### Format 的双重身份

就像一个人既有“职业”（分类），又有“技能证书”（标签）：

| 维度 | 表达方式 | 对应开发概念 | 用途 |
|------|---------|------|------|
| 职业身份 | `id` + `parent` 树 | 类 (Class/Struct) | 决定了它长什么样 |
| 技能/属性 | `tags` | 接口 (Interface/Trait) | 决定了它通过了哪些验证 |

对**人类**：看名字（name）就知道大概。
对**计算机**：同时看分类和标签。只有分类对且标签全，才算类型匹配。

#### 成为该类型的前提条件

`semantic_preconditions` 规定了数据必须满足什么条件才有资格被称为这个类型：

```yaml
format:
  id: "reviewed-code-diff"
  parent: "code-diff"
  tags: ["reviewed"]
  semantic_preconditions:
    - "必须经过至少一名人类审查"
    - "必须包含审查者的评价字段"
  required_tags: ["vcs-verified"]   # 必须先通过“安检口”确认是合法的版本控制代码
```

`required_tags` 是**机器自动检查**的——在搭建流水线时，系统会自动检查上游是否有“安检口”贴了这些标签。如果不贴，流水线直接报错，不让运行。

#### 语义分类树 (严格的父子关系)

```text
Requirement (需求/意图)
├── FeatureRequirement   "新功能需求"
└── BugfixRequirement    "修复 Bug 需求"

Code (源代码实现)
├── PythonCode           "Python 写的代码"
└── BashScript           "Bash 脚本"

Document (文档/规格)
├── Spec                 "详细方案/规格说明书"
└── APIDoc               "接口定义文档"
```

形态的改变由 Transformer 来完成：`需求 => 方案 => 代码`。

### 3.2 Verdict — 判定结果 *(V0.2 增强)*

```
Verdict = {
    kind:           PASS | FAIL | PARTIAL
    output:         判定通过的产物 (PASS 时) 或中间态 (PARTIAL 时)
    diagnosis:      失败诊断信息 (FAIL/PARTIAL 时)
    details:        结构化的判定细节

    # V0.2 新增
    confidence:     语义匹配确信度 (0.0 ~ 1.0, 可选)
    granted_tags:   本次判定授予的语义标签列表
}
```

Verdict 不是布尔值。它携带**诊断信息**——这是反馈回路的关键。当 FAIL 发生时，diagnosis 描述了"为什么不行"，这个信息会被路由回 LLM，使其能针对性地自我修正。

#### 判定结果语义

| Kind | 含义 | 类比 |
|------|------|------|
| PASS | 输出满足约束，锚定成功 | 编译通过 |
| FAIL | 输出不满足约束，需要外部处理 | 编译失败 + 错误信息 |
| PARTIAL | 部分满足，可以继续 | 警告但不阻断 |

#### V0.2: 语义置信度 (confidence)

`confidence` 量化了 validator 对语义匹配的确信程度：

```
confidence = 1.0  → 确定性判定 (硬锚定器总是 1.0)
confidence = 0.9  → 高确信度 (LLM 分类器: "这几乎肯定是一份 API 文档")
confidence = 0.5  → 存疑 (LLM: "这可能是需求文档也可能是设计文档")
confidence = 0.2  → 低确信度 (LLM: "这不太像需求文档，但勉强能解析")
```

**硬锚定器的 confidence 总是 1.0**——它要么通过要么不通过，没有模糊地带。
**软锚定器的 confidence 反映语义距离**——下游节点可据此决策（如低于阈值就 HALT）。

#### V0.2: 授予标签 (granted_tags)

`granted_tags` 声明本次验证确认了哪些语义维度：

```yaml
# 一个判断"输入是否来自合法版本控制系统"的 validator
verdict:
  kind: PASS
  confidence: 1.0
  granted_tags: ["vcs-verified"]   # 我确认了这份数据来自合法 VCS

# 一个判断"代码变更是否属于前端领域"的 validator
verdict:
  kind: PASS
  confidence: 0.85
  granted_tags: ["domain.frontend"]  # 我 85% 确信这是前端代码变更
```

标签在管线中**累积**——经过的 validator 越多，数据携带的已验证语义维度越多。

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

### 3.5 Pipeline — 类型安全的组合 *(V0.2 增强)*

```
Pipeline = {
    id:          唯一标识
    name:        人类可读名称
    description: 管线用途描述
    nodes:       Anchor 和 Transformer 的列表
    edges:       节点间的连接 (必须类型安全)
    entry:       入口节点 ID

    # V0.2 新增
    group:       管线所属组 (组内共享事件空间)
    tags:        管线级语义标签 (所有事件自动继承)
}
```

Pipeline 是 Anchor 和 Transformer 的有向组合图——LAP 的"程序"。

**Pipeline 的关键约束：类型安全。** 每条边的源节点 `format_out` 必须与目标节点 `format_in` 兼容（相同或可通过继承关系转换）。不兼容的连接在"编译期"（管线构建时）就会被拒绝。

**V0.2: Pipeline 的 `tags` 自动注入到所有事件中。** 当管线发射事件时，事件的 tags 字段会自动包含管线的 tags + 数据流过各 validator 时累积的 `granted_tags`。这使事件总线的消费者可以精确过滤特定语义范围的事件。

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

### 4.3 V0.2: 标签兼容性规则

V0.2 在结构兼容性之上增加了**标签兼容性**检查：

```
TAG_COMPATIBLE(data_tags, required_tags) =
    required_tags ⊆ data_tags
    -- 数据已累积的标签必须覆盖目标要求的所有标签
```

完整的类型检查变为：

```
FULLY_COMPATIBLE(source, target) =
    COMPATIBLE(source.format_out, target.format_in)     -- 结构兼容
    AND TAG_COMPATIBLE(accumulated_tags, target.required_tags)  -- 标签覆盖
```

标签兼容性是**路径敏感的**——它取决于数据到达某节点时累积了哪些 `granted_tags`，而非只看单条边。

### 4.4 Transformer 作为语义转换（伴随丢失）

当类型在流水线中发生实质性的状态转移（如衍生）时，必须插入 Transformer：

```
逻辑转换流 (基于依赖):
  Requirement → Spec      (需求分析)
  Spec → Code             (编程实现)
  Code → TestResult       (测试执行)
```

**关键洞察：Transformer 操作本质上是有损的转移。** 
从 `Requirement` 到 `Code`，需求中宏观的业务背景被丢弃，坍缩为具体的代码逻辑。
这就引出了 LAP 协议处理大模型幻觉时遇到的**“语义自定义悖论”**：如果我们规定“必须忠实于输入”，那一个负责脑暴发散的 Agent 算违规吗？显然不算，因为它“忠实”于了它发散的使命。

因此，在 LAP 的高级实践中，“忠实于原需求（或者忠实于预期的转换逻辑）”不应被降级为一个简单的 `loss_error` 字段，而是被**统一吸纳进 `confidence`（语义确信度）的评价体系中，并成为一种贯穿全生命周期的历史约束**。

如果一个 Agent 声称自己输出了 `Code`，它必须通过一个专门比对“原需求”与“新代码”的 Anchor（即进行一次基于源输入的 Ground Truth 校验）。如果没有这种“基于输入的强对应”，任何转换产物（即使格式完全正确）在语义上都是存疑的（例如 Agent 可能会“无论什么需求都输出同一段预置代码”以骗过格式校验）。只有通过了这种比对，`confidence` 才会被维持在较高水平。

### 4.5 类型推断

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

## 5. 语义标签系统 *(V0.2 新增)*

### 5.1 为什么需要标签

继承链回答 "这个东西**是什么**"（is-a 关系）：

```
code-diff <: requirement    — "代码差异"是一种"需求"
```

但继承链无法回答：
- 这份 code-diff **来自哪个系统**？（Git? SVN?）
- 这份 code-diff **属于什么领域**？（前端? 后端? 数据库?）
- 这份 code-diff **被验证过什么**？（格式合法? 来源可信? 领域已确认?）

如果把所有维度编码到类型名里，类型数量会指数爆炸：

```
# 不可行的做法
git-frontend-reviewed-security-code-diff
svn-backend-unreviewed-performance-code-diff
svn-fullstack-reviewed-bugfix-code-diff
...
```

标签系统用正交维度解决这个问题。

### 5.2 标签的设计原则

**点分层级命名**，参考 Java 包命名和日志 logger 命名：

```
source.git          — 来源: Git
source.svn          — 来源: SVN
domain.frontend     — 领域: 前端
domain.backend      — 领域: 后端
domain.infra        — 领域: 基础设施
lang.python         — 语言: Python
lang.en             — 语言: 英文
```

点分层级支持**前缀匹配**：订阅 `domain.*` 可以匹配所有领域标签。

### 5.3 标签的四种关系

```
缩窄 (Narrowing):
  tags=["source.git"] → tags=["source.git", "domain.frontend"]
  标签增多 → 语义更精确

放宽 (Widening):
  tags=["source.git", "domain.frontend"] → tags=["source.git"]
  标签减少 → 语义更宽泛

组合 (Composition):
  ["source.git"] ∪ ["domain.frontend"] = ["source.git", "domain.frontend"]
  两个正交维度的联合

交集 (Intersection):
  ["source.git", "domain.frontend"] ∩ ["source.git", "intent.bugfix"] = ["source.git"]
  共享的语义维度
```

**核心规则：标签越多 = 类型越窄 = 语义越精确。**

这与继承链的方向一致：子类型比父类型更具体。标签是继承链的正交补充。

### 5.4 三层信息机制：各管各的

LAP V0.2 区分三种信息承载机制，**各有各的职责，互不替代**：

| 机制 | 回答 | 时机 | 例子 |
|------|------|------|------|
| Format 类型链 (is-a 继承) | 数据经过了什么转换 | 编译期 | `raw-doc → english-doc → translated-doc` |
| Tags | 数据的**固有语义属性** | 编译期+运行时 | `source.git`, `domain.frontend`, `lang.en` |
| Event trace | 实际经过哪些节点、结果如何 | 运行时 | `ANCHOR_VERDICT at language_guard: PASS` |

**关键区分：Tags 只放固有属性，不放过程痕迹。**

```
固有属性 (应当作为 Tag):
  source.git       — 数据来自 Git (这是数据本身的属性)
  domain.frontend  — 属于前端领域 (这是数据本身的属性)
  lang.en          — 语言是英文 (这是数据本身的属性)

过程痕迹 (不应作为 Tag):
  context.enriched — "被上下文增强过" → 这是 Format 类型链的职责
                     (enriched-diff is-a code-diff 已表达了这个信息)
  refs.extracted   — "引用已提取" → 这是 Format 语义前置条件的职责
  status.reviewed  — "已审查" → 这是 event trace 的职责
                     (ANCHOR_VERDICT at review_checker: PASS 已记录了这件事)
```

**为什么过程痕迹不应放在 Tags 中？**

1. **冗余**: Format 类型链已经记录了 "数据经过了什么转换"。`enriched-diff` 继承自 `code-diff`，is-a 关系本身就是历史。
2. **脆弱**: 过程标签与管线结构紧耦合。改名一个节点就要改一批标签。
3. **语义模糊**: `context.enriched` 丢失了太多信息——被什么上下文增强？用什么方法？event trace 有完整答案。

**数据的"历史"如何追溯？**

```
问: "这份翻译文档经过了哪些处理？"

答 (通过 Format 类型链):
  translated-document is-a validated-document is-a raw-document
  → 它是一份经过验证和翻译的文档

答 (通过 event trace):
  1. format_guard: PASS (文档可解析)
  2. language_guard: PASS (确认为英文)
  3. translator: PASS, confidence=None (LLM 翻译)
  4. quality_checker: PASS (完整性检查通过)
  → 完整的处理历史，含每一步的结果和 confidence
```

三层各管各的，无需在 Tags 中重复 Format 类型链和 event trace 已承载的信息。

### 5.5 标签与事件总线

标签系统与事件总线的 subscribe 过滤**自然统一**：

```python
# 只消费"来自 Git 的前端代码变更"事件
bus.subscribe(
    group="frontend-team",
    consumer="reviewer-1",
    tags=["source.git", "domain.frontend"],
)
```

匹配规则：**事件的 tags 必须包含订阅指定的所有 tags**（AND 语义）。

标签来源有两层，合并后注入事件：

| 来源 | 示例 | 说明 |
|------|------|------|
| Pipeline.tags | `["myproject.pipeline.review"]` | 管线级固有标签 |
| Format.tags | `["source.git", "domain.frontend"]` | 类型级固有标签 |

事件发射时，两层标签合并为事件的 `tags` 字段。标签反映数据的固有语义属性，不反映过程痕迹。

### 5.6 PipelineChecker 的标签检查

编译期检查扩展为两个维度：

```
对每条边 (source_node → target_node):

  1. 结构检查 (V0.1):
     source.format_out 与 target.format_in 是否兼容 (is-a 关系)

  2. 标签兼容检查 (V0.2):
     target.format_in 的 tags 是否是
     source.format_out 的 tags 的子集 (或相等)

     如果 target 要求 tags 不被 source 覆盖 → 警告:
     "节点 'code_analyzer' 的输入类型要求标签 ['domain.frontend'],
      但上游输出类型的标签中不含该标签"
```

这是**编译期的语义安全检查**——在管线实际运行之前就发现类型定义中的标签不兼容。
标签是 Format 类型的固有属性，不是运行时累积的过程痕迹。

---

## 6. 未检验输入与入口守卫 *(V0.2 新增)*

### 6.1 问题：隐含的语义假设

考虑一个文档翻译管线：

```yaml
pipeline:
  entry: "translator"
  nodes:
    - id: "translator"
      format_in: "english-doc"
      format_out: "chinese-doc"
```

这个管线假设输入是英文文档。但谁验证了这一点？如果传入一份法文文档：
- `translator` 收到的数据结构可能完全正确（都是文本）
- 但**语义不匹配**——它不是英文
- 翻译器可能产出半英半法的混乱输出
- 下游节点没有任何机制检测到这个问题

**Bug 的根源：管线信任了未经验证的输入。**

### 6.2 Rust 的解决方案：Newtype Pattern

Rust 通过类型系统强制区分"未验证"和"已验证"：

```rust
// 未验证 — 只是一个字符串
struct RawDocument(String);

// 已验证的英文文档 — 只能通过 validate() 构造
struct EnglishDocument(String);

impl RawDocument {
    fn validate(self) -> Result<EnglishDocument, ValidationError> {
        if detect_language(&self.0) != Language::English {
            return Err(ValidationError::WrongLanguage);
        }
        Ok(EnglishDocument(self.0))
    }
}

// 翻译函数只接受 EnglishDocument，不接受 RawDocument
fn translate(doc: EnglishDocument) -> ChineseDocument { ... }
```

**未经 `validate()` 就无法构造 `EnglishDocument`，编译器强制保证这一点。**

### 6.3 LAP 的解决方案：入口守卫模式

LAP V0.2 引入**入口守卫（Entry Guard）** 模式——每个管线的入口节点应当是一个**类型守卫**，负责将未检验输入 narrow 为已检验类型。

```yaml
# 反模式: 直接信任输入
pipeline:
  entry: "translator"           # 假设输入已经是英文文档

# 正确模式: 入口守卫
pipeline:
  entry: "language_guard"       # 先验证输入语言

  nodes:
    - id: "language_guard"
      kind: ANCHOR
      format_in: "raw-document"        # 接受: 未检验的文档
      format_out: "english-document"   # 产出: 已验证的英文文档
      validator:
        kind: HARD
        description: "检测文档语言，验证为英文"
      routes:
        PASS: { action: NEXT, target: "translator" }
        FAIL: { action: HALT, feedback: "输入不是英文文档" }

    - id: "translator"
      kind: ANCHOR
      format_in: "english-document"    # 要求: 已验证的英文文档
      format_out: "chinese-document"
```

**语义缩窄的两条路径对比：**

```
路径 A (错误): raw-document ──────────────────▶ translator
               ↑ 语义假设被隐含，没有验证

路径 B (正确): raw-document ──▶ language_guard ──▶ translator
               ↑ 未检验输入      ↑ 显式验证         ↑ 已检验输入
```

### 6.4 入口守卫的分层

入口守卫可以是**多层**的。一个文档处理管线可能需要逐步验证：

```
raw-document                          (未检验输入)
    │
    ▼ [format_guard]  验证格式合法
validated-document                    tags=["format.valid"]
    │
    ▼ [language_guard]  验证是英文
english-document                      tags=["format.valid", "lang.en"]
    │
    ▼ [domain_classifier]  判断文档领域
english-legal-document                tags=["format.valid", "lang.en", "domain.legal"]
    │
    ▼ [translator]  开始翻译
chinese-legal-document                tags=["lang.zh", "domain.legal"]
```

每一层守卫将数据从一个 Format 类型 narrow 到更精确的子类型。标签是 Format 类型的固有属性——数据进入 `english-document` 类型就自带 `lang.en` 标签，无需运行时"授予"。这使得：
- **每个 validator 职责单一**——只检查一个维度
- **失败点精确**——"格式不合法"和"不是英文"是不同的错误
- **可组合**——需要法文翻译？替换 `language_guard` 为法文检测器即可

### 6.5 confidence 与语义距离

当入口守卫是软锚定器（如 LLM 分类器）时，`confidence` 量化了语义匹配的不确定性：

```
场景: LLM 判断一份文档是否属于"法律领域"

已校准，高置信度:
  verdict: PASS, confidence=0.95
  → 下游翻译器可以放心使用法律术语词库

已校准，低置信度:
  verdict: PASS, confidence=0.4
  → 下游翻译器应该回退到通用词库，或请求人工确认

未校准 (实验前):
  verdict: PASS, confidence=None
  → 默认路由处理，标记为待校准
```

**confidence 让管线可以量化语义风险并做出相应决策。** 在 V0.1 中，软锚定的不确定性是黑箱——PASS 就是 PASS，没有程度之分。V0.2 的 confidence 把这个黑箱打开了。

注意 `confidence=None` 表示"未校准"——在没有实验数据之前，诚实地表达"不知道准不准"，而非编造一个数字。

管线可以基于 confidence 设置**阈值路由**：

```yaml
routes:
  PASS:
    - condition: "confidence >= 0.8"
      action: NEXT
      target: "specialized_processor"
    - condition: "confidence >= 0.5"
      action: NEXT
      target: "general_processor"
    - condition: "confidence < 0.5"
      action: HALT
      feedback: "语义匹配度过低，无法继续"
```

### 6.6 与事件总线的对齐

入口守卫产出的事件自然携带语义标签：

```
事件 1: ANCHOR_VERDICT at format_guard
  format_out: validated-document (tags: ["format.valid"])
  confidence: 1.0

事件 2: ANCHOR_VERDICT at language_guard
  format_out: english-document (tags: ["format.valid", "lang.en"])
  confidence: 1.0

事件 3: ANCHOR_VERDICT at domain_classifier
  format_out: english-legal-document (tags: ["format.valid", "lang.en", "domain.legal"])
  confidence: None (未校准)
```

事件总线的消费者可以按 Format 的固有标签精确订阅：
- 订阅 `tags=["format.valid"]` → 收到所有格式合法的文档事件
- 订阅 `tags=["lang.en", "domain.legal"]` → 只收到英文法律文档事件
- 标签来自 Format 类型定义，而非运行时累积

---

## 7. 协议运作方式

### 7.1 静态阶段：管线构建

```
1. 用户/系统声明一组 Anchor 和 Transformer
2. 声明它们之间的连接（边）
3. 类型检查器验证:
   a. 结构兼容性: 每条边的 format_out → format_in (V0.1)
   b. 标签兼容性: format_out 的 tags 是否覆盖下游 format_in 的 tags (V0.2)
   c. 入口守卫:   entry 节点是否接受未检验输入 (V0.2 警告)
4. 产出: 类型安全 + 语义安全的 Pipeline 定义
```

### 7.2 动态阶段：管线执行

```
1. 输入数据从入口节点进入，携带 Format 类型 (含固有标签)
2. 当前节点 (Anchor) 执行:
   a. 验证输入是否匹配 format_in (硬检查)
   b. 调用 Validator 判定
   c. 产出 Verdict (PASS / FAIL / PARTIAL)
   d. V0.2: Verdict 携带 confidence (None / 1.0 / 已校准值)
3. 根据 Verdict 查路由表:
   - PASS  → 前进到下一节点 (或 EMIT 退出)
   - FAIL  → 按路由处理 (RETRY / JUMP / HALT)
   - PARTIAL → 继续或分支
4. 数据通过 Format 类型转换获得新的固有标签 (由 format_out 的 tags 定义)
5. 如果下一节点需要类型转换，经过 Transformer
6. 重复直到 Pipeline 到达出口 (EMIT) 或终止 (HALT)
7. 每一步的 Verdict 写入 event trace，供事后溯源
```

### 7.3 运行时事件

Pipeline 执行过程中的每一步都产生事件（与 OmniFactory 的 FactoryEvent 对齐）：

```
ANCHOR_ENTER     — 进入锚点
ANCHOR_VERDICT   — 锚点产出判定 (V0.2: 含 confidence)
ANCHOR_ROUTE     — 路由决定
TRANSFORM_BEGIN  — 开始类型转换
TRANSFORM_END    — 类型转换完成
PIPELINE_EMIT    — 管线产出最终结果
PIPELINE_HALT    — 管线异常终止
```

### 7.4 示例：双锚点 Agent 循环

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

### 7.5 示例：带入口守卫的文档处理管线 *(V0.2 新增)*

```yaml
pipeline:
  id: "doc-translation"
  name: "Document Translation Pipeline"
  tags: ["translation", "nlp"]
  entry: "input_guard"

  formats:
    - id: "raw-document"
      parent: "requirement"
      description: "未经检验的文档输入"
      tags: []
      semantic_preconditions: []

    - id: "validated-document"
      parent: "raw-document"
      description: "格式合法、语言已确认的文档"
      tags: ["format.valid", "lang.en"]
      semantic_preconditions:
        - "文档格式可解析 (非二进制/非损坏)"
        - "文档语言已被检测确认为英文"

    - id: "translated-document"
      parent: "validated-document"
      description: "已完成翻译的文档"
      tags: ["lang.zh"]
      semantic_preconditions:
        - "译文已由翻译引擎生成"
        - "原文语言已确认为英文"

  nodes:
    # 入口守卫: 验证文档格式和语言
    - id: "input_guard"
      kind: ANCHOR
      format_in: "raw-document"
      format_out: "validated-document"
      validator:
        kind: HARD
        description: "检查文档可解析、检测语言"
      routes:
        PASS:
          action: NEXT
          target: "translator"
        FAIL:
          action: HALT
          feedback: "文档不可解析或语言不受支持"

    # 翻译器: 依赖入口守卫的验证结果
    - id: "translator"
      kind: ANCHOR
      format_in: "validated-document"    # required_tags 由 format 声明
      format_out: "translated-document"
      validator:
        kind: SOFT
        description: "LLM 驱动的翻译"
      routes:
        PASS: { action: NEXT, target: "quality_checker" }
        FAIL: { action: RETRY, max_retries: 2 }

    # 质量检查: 硬锚定
    - id: "quality_checker"
      kind: ANCHOR
      format_in: "translated-document"
      format_out: "translated-document"
      validator:
        kind: HARD
        description: "检查译文完整性 (非空、长度合理、无乱码)"
      routes:
        PASS: { action: EMIT }
        FAIL: { action: HALT }
```

**注意 `input_guard` 的位置**——它在 `translator` 之前，确保翻译器永远不会收到格式错误或语言未知的文档。如果没有入口守卫，翻译器可能收到二进制文件并产出垃圾。

---

## 8. 现有系统的 LAP 转换

### 8.1 ChatGPT 对话 = 单锚点管线

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

### 8.2 OpenAI Function Calling = 双锚点管线

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

### 8.3 SWE-Agent (代码修复) = 多锚点管线

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

### 8.4 Guardrails AI = 判定器链

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

### 8.5 CI/CD Pipeline = 纯硬锚定管线

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

### 8.6 V0.2 视角：用标签增强 CI/CD *(新增)*

用 V0.2 的标签系统，可以为 CI/CD 管线增加语义维度：

```yaml
pipeline:
  id: "cicd-enhanced"
  tags: ["ci", "production"]
  entry: "input_guard"

  nodes:
    # V0.2: 入口守卫 — 验证提交合法性
    - id: "input_guard"
      format_in: "code-commit"
      format_out: "verified-commit"
      validator:
        kind: HARD
        description: "验证签名、检查提交者权限、确认分支策略"
      routes:
        PASS:
          action: NEXT
          target: "anchor-build"
          # format_out 的 tags 包含 ["author.verified", "branch.valid"]
        FAIL:
          action: HALT
          feedback: "提交不合法 (签名无效/无权限/分支策略不符)"

    - id: "anchor-build"
      # ... (同 8.5, 但现在可以信任输入已被验证)
```

**没有入口守卫**：编译器可能编译来自被盗凭据的恶意提交。
**有入口守卫**：在编译之前就拒绝不合法的提交。

---

## 9. 最佳实践 *(V0.2 新增)*

### 9.1 Format 命名规范

**对人类：名称应当完整描述类型的语义**

```
好的命名:
  "verified-code-commit" — 人一眼知道这是"经过验证的代码提交"
  "translated-legal-doc" — 人一眼知道这是"已翻译的法律文档"

坏的命名:
  "input-v2"  — 什么输入？v2 是什么意思？
  "processed" — 被什么处理过？
  "data"      — 最没有信息量的名称
```

**对计算机：`(id, tags)` 整体是唯一标识**

```yaml
# 两个结构相同但语义不同的类型
format:
  id: "code-diff"
  tags: ["source.git", "domain.frontend"]

format:
  id: "code-diff"
  tags: ["source.svn", "domain.backend"]

# 结构一样 (都是 code-diff)，语义不同 (标签不同)
# 计算机通过标签区分，人通过命名 + 描述区分
```

### 9.2 入口守卫原则

**每个管线的第一个节点应当是入口守卫。**

```
原则: 管线的 entry 节点应当接受最宽泛的输入类型，
      并通过显式验证将其 narrow 为下游节点期望的精确类型。

原因: 现实中的输入永远是"未检验的"——
      它可能格式错误、领域不符、来源不可信、或者根本不是预期的东西。
      在第一个节点就拦截这些问题，比在管线中间莫名其妙地崩溃好得多。
```

入口守卫的最佳实践：

| 规则 | 说明 |
|------|------|
| 接受最宽类型 | `format_in` 应该是 `raw-*` 或无标签的基础类型 |
| 产出窄类型 | `format_out` 应该是带标签的具体类型 |
| 用硬锚定 | 入口守卫应尽量用 HARD validator (确定性) |
| 失败即停 | FAIL → HALT，不要试图 RETRY 不合法的输入 |
| 类型精确 | `format_out` 的固有标签精确反映已验证的语义维度 |

### 9.3 标签设计规范

**标签只放固有语义属性——数据"是什么"，而非"经过了什么"。**

```
固有属性 (好的标签):
  "source.git"       — 数据来自 Git (数据本身的属性)
  "lang.en"          — 语言是英文 (数据本身的属性)
  "domain.frontend"  — 属于前端领域 (数据本身的属性)

过程痕迹 (坏的标签):
  "context.enriched" — "被增强过" → Format 类型链已表达 (enriched-diff is-a code-diff)
  "refs.extracted"   — "引用已提取" → Format 语义前置条件已声明
  "status.reviewed"  — "已审查" → event trace 已记录 (ANCHOR_VERDICT at reviewer: PASS)
  "structure.valid"  — "结构合法" → Format 转换本身意味着此事

无信息量:
  "input"            — 没有语义
  "v2"               — 版本号不是语义维度
  "probably.english" — 概率性判断不应成为标签 (用 confidence 替代)
```

**判断标准：如果去掉管线中的某个节点，这个标签是否仍然有意义？**
- `source.git` → 有意义 (数据确实来自 Git，不管管线结构如何)
- `context.enriched` → 无意义 (没有 enricher 节点就不存在这个标签)

### 9.4 confidence 使用指南

confidence 有三种语义状态：

| 值 | 含义 | 来源 |
|----|------|------|
| `None` | **未校准** (uncalibrated) — 不知道准不准 | 实验前的软锚定器一律用 `None` |
| `1.0` | **确定性** — 定义上为真，不是测量 | 硬锚定器 (编译器、schema 校验) |
| `0.xx` | **已校准** — 来自实验数据或后验 | 有校准数据后的软锚定器 |

**关键原则：在没有实验数据之前，不要编造 confidence 数字。**

```
错误做法:
  confidence = 0.8  ← 凭感觉写的，没有校准数据支撑

正确做法:
  confidence = None  ← 诚实表达"我不知道准不准"
  # 等收集了 (confidence, actual_correct) 数据对后，再填入校准值
```

有了校准数据后的路由策略：

| 场景 | confidence | 处理方式 |
|------|-----------|---------|
| 硬锚定器 | 总是 `1.0` | 不需要额外处理 |
| 已校准，高确信 | ≥ 0.8 | 正常流转 |
| 已校准，中等确信 | 0.5 ~ 0.8 | 回退到通用处理或人工确认 |
| 已校准，低确信 | < 0.5 | HALT 或 RETRY with different prompt |
| 未校准 | `None` | 按默认路由处理，标记为待校准 |

### 9.5 语义距离与管线稳定性

**定义：语义距离 = 输入数据的实际语义 与 Format 声称的语义 之间的差距。**

```
语义距离 = 0: 完美匹配
  输入声称是 "english-doc"，实际确实是英文文档

语义距离 > 0: 存在偏差
  输入声称是 "english-doc"，实际是中英混合文档

语义距离 >> 0: 严重不匹配
  输入声称是 "english-doc"，实际是一张图片
```

**管线稳定性与入口处的语义距离成反比。** 如果入口处就有大的语义偏差，这个偏差会在管线中**放大**——每个后续节点都基于错误的语义假设工作，错误像滚雪球一样越来越大。

入口守卫的作用就是**在管线入口将语义距离压缩到 0（或尽可能接近 0）**。这就是为什么入口守卫是 LAP V0.2 最重要的实践。

### 9.6 必要条件验证方法论 (逆否命题 + 反例驱动)

**验证规则 = 必要条件。** Validator 检查的是 "成为好输出的必要条件"，而非充分条件。

#### 理想与现实

```
理想: 验证规则是充分必要条件
  "满足这些条件 ⟺ 一定是好输出"
  → 现实中几乎不可能达到 (语义空间太大)

现实: 用必要条件组合逼近
  "如果不满足 C，一定不是好输出" (逆否命题)
  → 每多一条必要条件，就多排除一类坏输出
  → 必要条件的交集逐步逼近充分必要条件
```

#### 逆否命题思考法

设计每条验证规则时，必须用**逆否命题**角度思考，而非正向假设：

```
正向假设 (错误的思考方式):
  "如果带了代码变更，那 summary 应该提到具体文件"
  → 在已经被错误缩窄的假设空间里推理
  → 可能遗漏 "纯配置变更、无代码但有 summary" 的合法情况

逆否命题 (正确的思考方式):
  "如果没有 summary，是否一定不是好的需求文档？"
  → 是的，没有 summary 的需求文档一定不完整
  → 结论: summary 必填是一条有效的必要条件
```

#### 反例验证流程

每条候选必要条件必须经过反例检验才能接受：

```
步骤 1: 提出候选规则 C
步骤 2: 用逆否命题提问: "如果不满足 C，是否一定不是好输出？"
步骤 3: 寻找反例: 是否存在 "C 不成立但输出正确" 的情况？
步骤 4: 判定:
  找到反例 → C 不是必要条件，丢弃或修正
  找不到反例 → C 是必要条件，接受
```

#### 实际案例：代码审查需求 Validator

以下展示对候选验证规则的完整分析过程（以代码审查管线为例）：

**接受的规则 (通过反例检验):**

| 规则 | 逆否提问 | 反例存在？ | 结论 |
|------|---------|-----------|------|
| commit_id 必填 | 没有 commit_id → 一定不是好审查？ | 无反例 | ✓ 接受 |
| summary 必填 | 没有 summary → 一定不是好审查？ | 无反例 | ✓ 接受 |
| changes 非空数组 | 没有任何变更 → 一定不是好审查？ | 无反例 | ✓ 接受 |
| 每个变更必须有 change_type | 没有变更类型 → 一定不是好审查？ | 无反例 | ✓ 接受 |
| change_type 在有效枚举内 | 类型不在枚举中 → 一定不对？ | 无反例 | ✓ 接受 |

**拒绝的规则 (存在反例):**

| 规则 | 逆否提问 | 反例 | 结论 |
|------|---------|------|------|
| 每个变更必须关联源文件 | 变更不关联源文件 → 一定不对？ | 纯配置变更: 只改 YAML/JSON，无源代码文件 | ✗ 拒绝 |
| 函数名必须出现在 diff 中 | 函数名不在 diff 中 → 一定不对？ | 配置级变更: 只修改环境变量或权限设置 | ✗ 拒绝 |
| old_value 必须是字面量 | old_value 不是字面量 → 一定不对？ | 自然语言描述: "旧逻辑: 重试3次后超时" | ✗ 拒绝 |

#### 常见陷阱

**陷阱 1: 在错误的类型假设内推理**

```
场景: InputGuard 命名为 "code-commit" 但实际只通过含 .py 文件的提交
问题: Validator 在 "code-commit = 一定有 Python 文件" 的假设下分析
结果: "每个变更必须关联 .py 文件" 看起来找不到反例
     (因为在假设空间内，确实每个提交都有 .py 文件)
真相: 假设空间本身就是错的——code-commit 可以是纯配置/文档变更
```

**解决方法: 隔离分析。** 只看 validator 自身的 `format_in` / `format_out` 定义，不引入上游节点的行为假设。

**陷阱 2: 混淆 "忠实检查" 和 "直接筛选"**

```
忠实检查 (正确): "如果不满足 A，一定不是好的 B"
  → validator 检查必要条件，不预设结论

直接筛选 (危险): "如果满足 A，就是好的 B"
  → validator 在做充分性判断，可能放过不满足但碰巧匹配的坏输出
```

**陷阱 3: 上下游必要条件的方向关系**

```
正确方向: 上游的必要条件 ⊇ 下游的必要条件
  入口守卫检查: "是合法的 Git 提交" (宽)
  最终 validator: "commit_id 必填 + summary 必填 + changes 非空 + ..." (窄)
  → 上游只排除明显不合格的，下游逐步收紧

错误方向: 上游比下游更严格
  入口守卫检查: "必须包含 .py 源文件" (窄)
  最终 validator: "changes 可包含配置文件变更" (宽)
  → 矛盾! 入口已排除了下游认为合法的输入
```

### 9.7 Format 类型精度

**Format 类型名必须诚实反映实际语义范围。**

如果 validator 实际筛选的是子集，类型名就必须反映这个子集。否则下游一切推理都建立在错误基础上。

```
场景: InputGuard 实际过滤 "包含 Python 源文件的提交"
错误命名: code-commit  ← 暗示包含所有代码提交
正确命名: python-code-commit  ← 诚实反映范围

或者: 修改 InputGuard 使其真正接受所有代码提交
正确命名: code-commit  ← 此时名称与行为一致
```

**检验方法：如果输入不在这个类型声称的范围内但被放进来了，下游会怎样？**

- 如果下游能正常处理 → 类型名太窄了，应该放宽
- 如果下游会崩溃 → 类型名正确
- 如果下游能处理但结果差 → 需要拆分为两个类型

---

## 10. 愿景

### 10.1 短期：OmniFactory 的协议基础

LAP 为 OmniFactory 提供：
- Agent step 循环的形式化描述（双锚点管线）
- 多 Agent 协作的类型安全组合
- 管线可观测性的统一事件模型
- 影子干预的自然挂载点（在任意 Anchor 之间插入 Intervention Anchor）
- V0.2: 语义标签驱动的精确事件过滤
- V0.2: 入口守卫确保管线输入的语义安全

### 10.2 中期：MCP 的对偶协议

```
MCP = 输入侧标准化 (LLM 如何访问外部能力)
LAP = 输出侧标准化 (LLM 产物如何被验证和路由)
```

MCP 回答："LLM 可以用什么工具？"
LAP 回答："LLM 的输出该怎么检验？"

二者互补，覆盖 LLM 与外部世界交互的完整表面。

### 10.3 长期：大语言编程模型

LAP 不只是一个协议——它是一种**编程范式**：

- **Format 是类型**：描述数据的语义（V0.2: 结构身份 + 语义标签）
- **Anchor 是函数**：接收类型、产出类型、带有验证逻辑
- **Transformer 是类型转换**：LLM 驱动的语义转换
- **Pipeline 是程序**：类型安全的函数组合
- **类型检查是编译器**：在管线构建时捕获错误（V0.2: 含标签覆盖检查）

在这个范式下：
- "编程" = 声明 Format 之间的 Transformer
- "测试" = 添加硬锚定器到管线中
- "调试" = 检查管线中哪个 Anchor 的 Verdict 不符合预期
- "重构" = 重组 Anchor 和 Transformer 的连接方式
- "需求分析" = 定义入口 Format 和出口 Format
- V0.2: "类型安全" = 不仅结构匹配，还要固有标签兼容 + 必要条件验证

**用户只需要声明"从这个类型到那个类型"，系统自动推断中间需要哪些 Transformer 和 Anchor——这就是自然语言编程的真正形态。**

---

## 11. 待校验指标

LAP V0.2 在 V0.1 的 8 项指标基础上，增加以下校验项：

### 11.1 V0.1 指标 (保留)

| 指标 | 通过标准 |
|------|---------|
| 原语完备性 | 五个原语可描述所有已知 LLM 锚定场景 |
| 类型系统有效性 | 100% 类型错误捕获，0% 误报 |
| Transformer 可行性 | 核心 Transformer 单次成功率 > 60%，配合 RETRY > 90% |
| 协议开销 | LAP 开销 < 总执行时间 1% |
| 可读性 | LAP YAML 描述优于等价 Python 代码 |
| 互操作性 | 现有工具 adapter < 50 行，不修改原工具 |

### 11.2 V0.2 新增指标

#### 标签系统有效性

**问题**: 标签兼容检查能否在编译期发现类型不兼容？

**验证方法**:
1. 构建一个管线，其中某节点的 `format_in` 要求标签 `["domain.frontend"]` 但上游 `format_out` 的标签不含该标签
2. 检查 PipelineChecker 是否发出警告
3. 修正 Format 定义后，警告是否消失

**通过标准**: 100% 的标签不兼容被检出。

#### 入口守卫效果

**问题**: 入口守卫是否有效减少下游节点的意外失败？

**验证方法**:
1. 准备 100 份输入，其中 30% 是格式错误/领域不符的
2. 对比有/无入口守卫时管线的行为:
   - 无守卫: 统计哪些节点因意外输入而 FAIL
   - 有守卫: 统计入口就被拦截的数量

**通过标准**: 有入口守卫时，下游节点因"意外输入"导致的 FAIL 减少 > 90%。

#### confidence 校准

**问题**: 软锚定器的 confidence 值是否与实际准确率相关？

**验证方法**:
1. 收集 LLM 分类器的 (confidence, actual_correct) 数据对
2. 绘制校准曲线: confidence=0.8 的预测中，实际正确率是否约 80%？

**通过标准**: Brier Score < 0.15（校准良好）。

#### 语义距离与管线成功率的关系

**问题**: 入口处的语义距离是否确实影响管线最终产出质量？

**验证方法**:
1. 人工标注一批输入的"真实语义距离"
2. 运行管线，记录最终产出质量评分
3. 分析二者相关性

**通过标准**: 语义距离与产出质量呈显著负相关 (r < -0.5)。

---

## 附录 A：术语表

| 术语 | 定义 |
|------|------|
| **Anchor（锚点）** | 流水线上的“检查站”。负责把 AI 的猜测变成确定的产物。 |
| **Format（类型）** | 数据在流水线上的“身份标签”。V0.2: 由 `(分类, 属性)` 共同定义身份。 |
| **Verdict（判定）** | 检查站的结论。包含：通过/打回/部分完成 + 诊断意见。 |
| **Validator（检查器）** | 检查站内部的具体逻辑。分“硬检查”（机器验证）和“软检查”（AI/人工评审）。 |
| **Route（路由）** | “根据结果去哪”。通过了进下一步，没过滚回去重写。 |
| **Transformer（转换器）** | 数据变身器。负责把一种身份的数据（如需求）翻译成另一种（如代码）。 |
| **Pipeline（管线/流水线）** | 由多个检查站和变身器串起来的完整加工流程。 |
| **权威真相 (Ground Truth)** | **不可逾越的现实基准**。例如：代码能不能编译、测试能否跑通、Git 里的真实状态。 |
| **语义标签 (Tags)** | 数据的“附加属性”。例如：“已通过安全扫描”、“前端代码”等辅助标识。 |
| **入口安检 (Entry Guard)** | 专门把关“外界脏数据”的节点，给干净的数据贴上“已验证”标签。 |
| **语义距离 (Semantic Distance)** | AI 的输出离你想要的“标准形态”差得有多远。 |
| **置信度 (Confidence)** | 检查站对这次输出“有多大把握”。硬检查永远是 1.0，软检查反映 AI 的确信度。 |

## 附录 B：与现有协议的关系

```
              ┌──────────────────────────────────────────┐
              │          应用层 (Applications)            │
              │  Agent / 代码生成 / 对话 / 自动化          │
              ├──────────────────────────────────────────┤
              │    LAP (Language Anchoring Protocol)      │  ← 本协议
              │    输出验证 + 语义类型路由                  │
              │    V0.2: 语义标签 + 入口守卫 + 置信度       │
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

## 附录 C：V0.1 → V0.2 变更摘要

| 变更项 | V0.1 | V0.2 |
|--------|------|------|
| Format 身份 | `id` (继承链) | `(id, tags)` 双维度 |
| Format 字段 | id, name, description, parent, schema | 新增 tags, semantic_preconditions, required_tags |
| Verdict 字段 | kind, output, diagnosis, details | 新增 confidence, granted_tags |
| Pipeline 字段 | id, name, description, nodes, edges, entry | 新增 group, tags |
| 类型检查 | 结构兼容性 | 结构兼容性 + 标签覆盖性 |
| 输入处理 | 隐含信任 | 入口守卫模式 (显式验证) |
| 语义不确定性 | 黑箱 (PASS/FAIL 二元) | confidence 量化 + 阈值路由 |
| 发现数 | 5 个 | 7 个 (新增: 语义维度, 未检验输入) |
| 最佳实践 | 无 | 5 条 (命名/入口守卫/标签设计/confidence/语义距离) |

---

*LAP V0.2 — 2026-03-15 — Draft*
