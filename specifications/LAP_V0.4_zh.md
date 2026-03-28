# Language Anchoring Protocol (LAP) — V0.4 规范

> **状态**：草案 / V0.4
> **日期**：2026-03-28
> **作者**：LAP Protocol Authors
> **项目**：OmniFactory
> **相较 V0.x 的变更**：重大版本升级。以**六元语义模型**为理论基础重构整个协议。V0.1–V0.3 所有机制在新框架下保留并泛化。向后兼容说明见§9。

---

## 核心转变

LAP V0.x 以 **Anchor（锚点）** 为中心：一切都是关于如何约束 LLM 输出、如何验证产物格式、如何在管线中路由。

LAP V0.4 以 **Signal（信号）** 为中心：**语义精确优于格式精确**。在 LLM 密集系统中，格式约束是语义约束的一个特例——只有在语义需要确定性验证时，才需要精确格式。大多数时候，自然语言文本本身就是最精确的语义载体。

这一转变不是否定 V0.x 的工作，而是将其提升到更高的抽象层次：锚点（Anchor）成为 Node 类型签名的表达方式，Verdict 成为 Signal 的特化，Pipeline 成为 Intent 的动态路由结果。

---

## 目录

1. [六元原语](#1-六元原语)
2. [Signal — 语义货币](#2-signal--语义货币)
3. [Format — 类型系统](#3-format--类型系统)
4. [Hook — 感知层](#4-hook--感知层)
5. [Node — 处理层](#5-node--处理层)
6. [Tool — 执行层](#6-tool--执行层)
7. [Intent — 意志层](#7-intent--意志层)
8. [Consciousness 环 — 执行模型](#8-consciousness-环--执行模型)
9. [向后兼容：V0.x → V1.0 映射](#9-向后兼容v0x--v10-映射)
10. [StateAnchor（保留）](#10-stateanchor保留)
11. [Task 与 Intent 的统一](#11-task-与-intent-的统一)
12. [消息信封（升级）](#12-消息信封升级)
13. [元代理操作协议（升级）](#13-元代理操作协议升级)
14. [跨机互操作](#14-跨机互操作)

---

## 1. 六元原语

LAP V0.4 的理论基础是六个正交原语。任何 LLM 密集系统的任何机制都可以用这六个原语的组合来表达，且表达是完备的——没有任何机制需要模型外的额外概念。

| 原语 | 别名 | 层次 | 职责 |
|------|------|------|------|
| **Hook** | 感官 | 感知层 | 在特定条件下观测环境，发出 Signal |
| **Signal** | 信号 | 语义层 | 节点间流动的语义实例（自然语言文本 + 类型标签）|
| **Format** | 概念 | 类型层 | Signal 的语义类型，定义"是什么" |
| **Node** | 节点 | 处理层 | Signal → Signal 的处理单元（可含 LLM 调用）|
| **Tool** | 躯体 | 执行层 | 操作外部世界，产生可观测的状态变化 |
| **Intent** | 意图 | 意志层 | 触发执行周期的特殊 Signal，由 (input_Format, output_Format) 对构成 |

**模型完备性**：
- 进化机制 = Consciousness 环（CompletionHook 条件 = `evolution_outcome: effective`）
- 痛觉系统 = Consciousness 环（CompletionHook 条件 = `pain_signal: decreasing`）
- 任务执行 = Intent + CompletionHook（条件 = `output Format 匹配`）
- 元进化 = 更高层 Consciousness 环，观测下层环的 CompletionHook 输出

---

## 2. Signal — 语义货币

### 2.1 定义

Signal 是六元系统中的基本流通单元。所有信息在节点间以 Signal 的形式传递。Signal 必须是自然语言可读的——LLM 或人类都能直接消费其 `text` 字段，无需解析 `meta`。

**语义精确原则**：`text` 字段是语义主体。不得将关键语义信息只存入 `meta` 结构化字段。如果信息不能用一句话表达，Signal 的 `text` 就是自然语言那句话。

```python
@dataclass
class Signal:
    format: str       # Format ID（类型标签）
    text: str         # 自然语言内容（语义主体）
    node_id: str = "" # 来源节点（追溯用）
    meta: dict = field(default_factory=dict)  # 结构化附加信息（路由/过滤用）
```

### 2.2 Signal 与 V0.x Verdict 的关系

V0.x 的 `Verdict` 是 Signal 的**特化**：专门表达"判定结果"语义。Signal 泛化了 Verdict——所有语义实例都是 Signal。

| V0.x 概念 | V0.4 对应 |
|----------|---------|
| `Verdict(kind=PASS)` | `Signal(format="verdict.pass", text="验证通过：...")` |
| `Verdict(kind=FAIL, diagnosis=...)` | `Signal(format="verdict.fail", text=diagnosis)` |
| `Verdict.confidence` | `Signal.meta["confidence"]` |
| `Verdict.granted_tags` | `Signal.meta["granted_tags"]` |

### 2.3 Signal 流动规则

- Signal 从 Hook/Node 产生，流向 Node 消费
- Node 消费 Signal 后，产出新的 Signal（转换或聚合）
- ConsciousnessNode 消费 Signal，产出 Intent（特殊 Signal）
- Tool 接收 Node 的调用指令，不直接消费 Signal，返回执行结果给调用 Node
- Signal 不携带执行逻辑，只携带语义内容

---

## 3. Format — 类型系统

### 3.1 定义

Format 是语义类型系统。它定义 Signal 的"是什么"，不定义"怎么处理"。Format 是**声明**，Node 是**实现**。同一 Format 可以有多个 Node 实现，且可以独立进化。

### 3.2 Format ID 命名规范

Format ID 采用点分命名空间，类似 MIME 类型：

```
{domain}.{subdomain}[.{specifics}]

示例：
  pain.routing.gap          # 路由盲区痛觉信号
  verdict.pass              # 锚定通过
  verdict.fail              # 锚定失败
  completion.evolution      # 进化完成信号
  intent.evolve.node        # 进化节点的 Intent
  state.anchor.git_commit   # git commit 状态锚点（硬类型）
  trace.exec.hard_node      # TRACE-SED 提取的硬节点执行轨迹
```

### 3.3 Format 定义结构

```python
class FormatSpec(BaseModel):
    id: str                       # 全局唯一 ID
    name: str                     # 人类可读名称
    description: str              # 自然语言描述（核心——LLM 可直接读懂）
    examples: list[FormatExample] # 2-5 个输入→输出示例（取代 JSON Schema 的主要定义方式）
    parent_id: str | None = None  # 父类型（类型继承）
    hard: bool = False            # True=硬类型（确定性验证），False=软类型（语义验证）
    schema: dict | None = None    # 可选：JSON Schema（仅硬类型需要）

class FormatExample(BaseModel):
    input_text: str   # 输入的自然语言示例
    output_text: str  # 输出的自然语言示例
    note: str = ""    # 说明（可选）
```

### 3.4 以示例定义 Format（核心创新）

**V1.0 的关键设计原则**：Format 首先由自然语言 `description` 和 `examples` 定义，JSON Schema 是可选的附加约束（仅硬类型使用）。

传统协议要求：先定义 Schema，再对照 Schema 验证。
V1.0 的方式：先用自然语言和示例描述语义，系统通过 LLM 判断"这个 Signal 是否符合此 Format 的语义意图"。

```yaml
# 示例：pain.routing.gap Format 定义
id: pain.routing.gap
name: 路由盲区痛觉信号
description: |
  表示系统在处理某类任务时发现路由网络中没有合适的处理节点，
  导致任务失败或退化到低质量路径。
  触发此信号意味着需要创建新的语义节点来覆盖此盲区。
examples:
  - input_text: "任务：分析 feishu 数据；错误：没有节点可以处理 feishu_table 格式"
    output_text: "路由盲区：feishu_table → analysis，近20次路由均失败，建议创建新节点"
  - input_text: "最近15步中，10步路由到 generic_processor 但均失败"
    output_text: "路由盲区检测：generic_processor 不适合当前任务类型，系统需要专化节点"
hard: false  # 语义验证，不需要精确 JSON Schema
```

### 3.5 Format 继承

```
signal
  ├── pain.*
  │   ├── pain.routing.gap
  │   ├── pain.node.timeout
  │   └── pain.evolution.failed
  ├── verdict.*
  │   ├── verdict.pass
  │   └── verdict.fail
  ├── intent.*
  │   └── intent.evolve.*
  ├── completion.*
  │   └── completion.evolution
  └── state.anchor.*  ← 硬类型（hard=True）
      ├── state.anchor.git_commit
      └── state.anchor.file_hash
```

---

## 4. Hook — 感知层

### 4.1 定义与规范

Hook 是系统的感官。观测环境、判断触发条件、发出 Signal list——不决策、不执行、不修改状态。

**关键约束**：
- `poll()` / `on_event()` 不调用 LLM
- 不写任何外部状态（只读）
- `Signal.text` 必须是可读自然语言，不是数值字符串

### 4.2 两种形态

```python
class PeriodicHook(ABC):
    """周期性感知，每 N 轮触发一次。"""
    async def poll(self, db_path: str, round_num: int) -> list[Signal]: ...
    def should_poll(self, round_num: int) -> bool: ...

class EventHook(ABC):
    """事件驱动感知，在事件发生时同步调用。"""
    def on_event(self, event: dict) -> list[Signal]: ...
```

### 4.3 CompletionHook — 闭合环路的特化 Hook

**CompletionHook** 是 EventHook 的特化用途：观测执行结果 Signal，判断其 Format 是否满足某个 Intent 的 `output_format`。若满足，发出"完成"Signal，闭合 Consciousness 环。

```python
class CompletionHook(EventHook):
    """观测执行结果，判断 Intent 是否已完成。

    触发条件：observed_signal.format ≈ intent.output_format
    触发结果：Signal(format="completion.{output_format}", text=执行结果摘要)
    """
    def __init__(self, intent_output_format: str, target_node_id: str): ...
    def on_event(self, event: dict) -> list[Signal]: ...
```

CompletionHook 体现了一个深刻洞见：**"意识到做完了"的瞬间总是一次观测**。完成判断不能由执行者自评，必须由独立的观测者（Hook）判定——这既是架构约束，也是防止自我欺骗的机制。

---

## 5. Node — 处理层

### 5.1 两类 Node

```python
class BaseNode(ABC):
    """普通处理节点：Signal → Signal 转换。"""
    def process(self, signal: Any) -> Any: ...

class ConsciousnessNode(ABC):
    """意识节点：Signal → Intent 决策。"""
    def decide(self, signal: Any, *args, **kwargs) -> Any: ...
    def ready(self, *args) -> bool: ...  # 冷却期控制
```

### 5.2 Node 类型签名（对应 V0.x AnchorSpec）

每个 Node 有输入/输出 Format 签名，V0.x 的 `AnchorSpec` 即对应此签名：

```python
class Router(ABC):
    """Node 的管线执行接口（运行时绑定）。"""
    INPUT_KEYS: list[str] | None = None
    OUTPUT_KEYS: list[str] | None = None
    def validate_input(self, input_data: Any) -> Verdict | None: ...
    def validate_output(self, verdict: Verdict) -> Verdict | None: ...
    def run(self, input_data: Any) -> Verdict: ...
```

### 5.3 Consciousness 节点的内部结构（四阶段展开）

复杂 Consciousness 节点可展开为四个独立可进化的阶段：

```
Monitor → Judge → Project(Intent) → [执行在环外发生] → CompletionHook → Monitor
```

| 阶段 | 职责 | 进化粒度 |
|------|------|---------|
| Monitor | 聚合 Hook Signal，维护状态语义摘要 | 聚合策略可进化 |
| Judge | 决定是否投射 Intent 及内容 | **系统智商天花板，必须独立进化** |
| Project | 将 Intent 格式化为执行请求 | 格式可进化 |
| CompletionHook | 观测结果，闭合环路 | 完成条件可进化 |

**Judge 必须独立的根本理由**：CompletionHook 产出的"执行结果 Signal"是 Judge 的**外部训练信号**——Judge 投射 Intent X，X 执行后 CompletionHook 观测结果，产生"X 是否达成目标"的 Signal。这是 Judge 的进化依据。Monitor 和 Judge 混在一起时，此外部信号无法定向反馈给 Judge，系统智商被封死。

---

## 6. Tool — 执行层

### 6.1 定义与规范

Tool 是系统的"手脚"。操作外部世界（文件系统、网络、数据库），产生可观测的状态变化。Tool 不做语义判断，不调用 LLM——只执行确定性操作。

```python
class Tool(ABC):
    name: str         # 工具唯一标识
    description: str  # 自然语言描述（供 LLM 理解用途）

    def execute(self, params: dict) -> dict:
        """执行并返回 {"success": bool, "output": str, ...}"""
        ...
```

### 6.2 Tool 与 V0.x Transformer 的关系

V0.x 的 `Transformer` 是 Tool 的特化（专注于 Format 类型转换）：

| V0.x 概念 | V0.4 对应 |
|----------|---------|
| `Transformer(method=RULE)` | 确定性 Tool |
| `Transformer(method=LLM)` | Node（LLM 调用属于 Node 层，不是 Tool）|
| `Transformer(method=HYBRID)` | Node + Tool 组合 |

---

## 7. Intent — 意志层

### 7.1 定义

Intent 是 ConsciousnessNode 产出的特殊 Signal，用于触发一个执行周期。Intent 的本质是**类型签名**：声明"我需要一个接受 Format_A 输入、产出 Format_B 输出的执行"。

Intent 不指定"怎么做"，只声明"做什么类型的事情"。具体执行路径由语义路由器根据 (input_format, output_format) 对动态匹配。

```python
@dataclass
class Intent:
    format: str = "intent"
    text: str = ""                 # 自然语言描述意图内容
    node_id: str = ""              # 发起 Intent 的 Consciousness 节点 ID
    meta: dict = field(default_factory=dict)
    input_format: str = ""         # 期望的输入 Format
    output_format: str = ""        # 期望的输出 Format（CompletionHook 匹配目标）
    priority: float = 0.5
    deadline_rounds: int = -1      # 超时轮次（-1 = 无超时）
```

### 7.2 Intent 与 V0.x 的关系

| V0.x 概念 | V0.4 对应 |
|----------|---------|
| `AnchorSpec(format_in, format_out)` | `Intent(input_format, output_format)` |
| 预定义 Pipeline 执行顺序 | Intent → 语义路由器动态匹配 Node 执行链 |
| `Route(action=RETRY)` | 执行失败 → CompletionHook 未触发 → Judge 重新投射 |
| `Route(action=EMIT)` | CompletionHook 触发 → 环路闭合 |
| `StateAnchor`（V0.3）| 硬类型 Signal（`state.anchor.*`）|
| `Task`（V0.3）| Intent 的生命周期实例 |

---

## 8. Consciousness 环 — 执行模型

### 8.1 最小 Consciousness 环

```
Hook ──Signal──→ ConsciousnessNode.decide()
                       │
                       ├── None → 不触发（冷却/阈值未达）
                       │
                       └── Intent ──→ 语义路由器 ──→ Node 执行链
                                                           │
                                                      CompletionHook.on_event()
                                                           │
                                            Signal(format="completion.*")
                                                           │
                                      ← 回传 ConsciousnessNode ←
```

### 8.2 奇点问题与解法

**问题**：若 Judge 是单一不可分的节点，Judge 的质量封死系统智商上限，且 Judge 无法被外部评估（自评 = 幻觉）。

**解法**：CompletionHook 产出的执行结果 Signal 是**外部事实**，不是 Judge 的自评。

- Judge 投射 Intent X
- X 被执行（Judge 不参与执行）
- CompletionHook 独立观测执行结果
- CompletionHook 产出"X 是否达成目标"的 Signal
- 此 Signal 是 Judge 的训练信号（外部真相）
- 进化系统可以据此独立优化 Judge 的 `processing_prompt`

**结论**：Consciousness 环通过 CompletionHook 将 Judge 的决策与其结果之间建立了可观测的因果链，使 Judge 可被进化。系统智商不被封死。

### 8.3 多层 Consciousness 环（元进化）

```
元 Consciousness 环（监测下层环的质量）
    │
    ├── 观测下层 CompletionHook 输出
    ├── Judge：下层 Consciousness 是否需要进化？
    └── Intent：进化某个下层 Judge 节点
           │
    痛觉 Consciousness 环（监测节点痛觉）
           │
    进化 Consciousness 环（执行具体进化）
           │
    任务执行 Consciousness 环（最底层）
```

每一层都是相同的六元结构。元进化不需要特殊原语——就是一个更高层的 Consciousness 节点，观测下层节点的 CompletionHook 输出。

---

## 9. 向后兼容：V0.x → V1.0 映射

### 9.1 完整映射表

| V0.x 概念 | V0.4 等价 | 迁移策略 |
|----------|---------|---------|
| `FormatSpec` | `FormatSpec`（保留，新增 `examples` 字段）| 现有定义自动向后兼容 |
| `AnchorSpec` | Node 的类型签名 + `FormatSpec` | Anchor 分解为 Node + Format |
| `ValidatorSpec` / `Validator` | `Node.validate_input/output` | 内化为 Node 接口 |
| `Verdict(kind, output, diagnosis)` | `Signal(format="verdict.*", text=diagnosis)` | Verdict 仍可用，视为 Signal 特化 |
| `Route(action=NEXT/RETRY/EMIT)` | 语义路由器决策结果 | 从静态路由表改为动态语义匹配 |
| `Transformer(RULE)` | 确定性 Tool | 按实现方式分类 |
| `Transformer(LLM)` | LLM Node | - |
| `OperatorSpec` | `semantic_nodes` 表中的节点记录 | 持久化到 DB，支持进化 |
| `StateAnchor` | 硬类型 Signal（`state.anchor.*`）| 见 §10 |
| `Task` | Intent 的生命周期实例 | 见 §11 |
| `Message Envelope` | 消息信封（升级）| 见 §12 |
| `LAP-MOP` | 元代理操作协议（升级）| 见 §13 |

### 9.2 V0.x Pipeline 的迁移

V0.x 的静态 Pipeline（预定义节点序列）在 V1.0 中有两种迁移方式：

**方式 A：保持静态（保守迁移）**
将现有 Pipeline 直接映射为 Node 执行链，语义路由器固定路由到此链。行为与 V0.x 完全相同。

**方式 B：动态化（完整迁移）**
将 Pipeline 入口转为 Intent，让语义路由器动态匹配最合适的执行路径。获得自适应能力，但需要语义网络积累足够的历史数据。

---

## 10. StateAnchor（保留）

StateAnchor 在 V1.0 中重新表达为**硬类型 Signal**（`hard=True` 的 Format）：

```python
Signal(
    format="state.anchor.git_commit",   # 硬类型
    text="git commit abc123 已验证：实现了 X 功能",
    meta={
        "commit_hash": "abc123",
        "verified_at": "2026-03-28T10:00:00",
        "path": "e:/WindowsWorkspace"
    }
)
```

**StateAnchor 的特殊价值**：为 CompletionHook 提供**不依赖 LLM 判断的客观完成证据**。当 Intent 的完成条件可以用 StateAnchor 表达时，CompletionHook 可以完全确定性地触发，不受 LLM 幻觉影响。

StateAnchor 等级（从 V0.3 保留）：
| 等级 | Kind | 完成条件可靠性 |
|------|------|-------------|
| 1 | `git_commit` | 最高（不可变）|
| 2 | `file_hash` | 高（内容绑定）|
| 3 | `p4_changelist` | 中（可能被继续编辑）|
| 4 | `api_snapshot` | 低（时间有界）|
| 5 | `agent_output` | ⚠️ 极低（LLM 断言，不可独立验证）|

---

## 11. Task 与 Intent 的统一

V0.3 的 `Task` 是 Pipeline 的执行实例。V1.0 中，Task 对应 Intent 的**生命周期**：

```
Intent 发出 → 语义路由器匹配 → 执行开始（Task.status = running）
                                  ↓
                          CompletionHook 触发（Task.status = completed）
                                  ↓
                          CompletionHook 未在 deadline 前触发（Task.status = failed）
```

TaskStatus 转换（从 V0.3 保留，语义对齐）：
```
pending → running → completed
                 → failed
                 → paused → running   （人工介入或资源等待）
```

Task 仍是记录执行历史的实体，但触发方式从"调用 Pipeline.run()" 变为"ConsciousnessNode 发出 Intent"。

---

## 12. 消息信封（升级）

V0.3 的消息信封在 V1.0 中新增 `signal` 字段，统一用 Signal 表达载荷类型：

```json
{
  "lap_version": "0.4",
  "envelope_id": "01KM4Z2A...",
  "task_id": "01KM4XZD...",
  "parent_id": "01KM4X...",
  "origin": {
    "kind": "human | agent | system | external_node",
    "identity": "user@example.com | node:sed.feishu_parser"
  },
  "signal": {
    "format": "feishu_state_data",
    "text": "已读取飞书消息 om:abc123，内容为...",
    "node_id": "sed.feishu_parser",
    "meta": {}
  },
  "state_anchor": {
    "kind": "file_hash",
    "ref": "sha256:abc...",
    "path": "data/feishu_msg.json"
  },
  "visibility": "private | internal | public",
  "payload": { "...": "向后兼容：原始 payload 保留" }
}
```

**V1.0 新增**：`origin.kind` 新增 `external_node`（跨机互操作用），`signal` 字段统一表达语义内容（`payload` 保留以兼容 V0.x）。

---

## 13. 元代理操作协议（升级）

V0.3 的 LAP-MOP 操作在 V1.0 中重新映射为 Intent：

| V0.3 LAP-MOP 操作 | V1.0 Intent |
|-----------------|------------|
| `CreateNode` | `Intent(input_format="routing.gap", output_format="semantic_node.new")` |
| `MergeNodes` | `Intent(input_format="semantic_node.pair", output_format="semantic_node.merged")` |
| `SplitNode` | `Intent(input_format="semantic_node.overgeneral", output_format="semantic_node.split")` |
| `RecordOutcome` | CompletionHook 自动触发，无需显式操作 |
| `ProposeType` | `Intent(input_format="format.proposal", output_format="format.registered")` |
| `ObsoleteNode` | Pain Consciousness 环判定后产出的 Intent |

所有操作的审计追踪、置信度阈值、`pending_review` 生命周期从 V0.3 保留，现在通过 Consciousness 环的 CompletionHook 自然实现。

---

## 14. 跨机互操作

本节为跨机互操作提供基本框架，详细协议见独立文档《语义交换协议（SEP）V0.1》。

### 14.1 核心原则

**外部系统可以注册为任何六元原语的实现**：

| 外部系统类型 | 注册为 | 通信模式 |
|------------|-------|---------|
| 外部 API 服务 | ExternalTool / ExternalNode | HTTP（拉取模型）|
| 外部事件流 | ExternalHook | WebSocket/SSE（推送模型）|
| 外部 LLM 服务 | ExternalNode（LLM 类型）| HTTP + 流式响应 |
| 外部格式定义库 | FormatProvider | HTTP（声明性接口）|

### 14.2 注册原则

外部原语注册不要求精确的 Schema——注册时提供：
1. **自然语言描述**：这个原语做什么
2. **示例**：3-5 个输入→输出对（Signal 级别）
3. **端点信息**：如何访问
4. **可见性声明**：支持哪些 visibility 级别

系统从示例中推断 Format，在语义网络中注册节点。

### 14.3 格式协商

当调用节点的输出 Format 与被调用外部节点的期望输入 Format 不精确匹配时：
- 语义路由器检查语义相似度（不做精确格式匹配）
- 若语义相似度 > 阈值，插入 LLM Transformer Node 自动桥接
- 若语义相似度 < 阈值，返回"无法路由"Signal，触发 Consciousness 判断

**语义精确优于格式精确**：不要求格式完全一致，要求语义意图可理解。

---

## 附录 A：核心原语接口汇总

```python
# Signal
@dataclass
class Signal:
    format: str; text: str; node_id: str = ""; meta: dict = field(default_factory=dict)

# Hook
class PeriodicHook(ABC):
    async def poll(self, db_path: str, round_num: int) -> list[Signal]: ...
class EventHook(ABC):
    def on_event(self, event: dict) -> list[Signal]: ...

# Node
class BaseNode(ABC):
    def process(self, signal: Any) -> Any: ...
class ConsciousnessNode(ABC):
    def decide(self, signal: Any, *args, **kwargs) -> Any: ...
    def ready(self, *args) -> bool: ...

# Tool
class Tool(ABC):
    name: str; description: str
    def execute(self, params: dict) -> dict: ...

# Format
class FormatSpec(BaseModel):
    id: str; name: str; description: str
    examples: list[FormatExample] = []
    parent_id: str | None = None; hard: bool = False
    schema: dict | None = None

# Intent
@dataclass
class Intent:
    format: str = "intent"; text: str = ""; node_id: str = ""
    meta: dict = field(default_factory=dict)
    input_format: str = ""; output_format: str = ""
    priority: float = 0.5; deadline_rounds: int = -1
```

---

## 附录 B：六元模型完备性验证

| 系统机制 | 六元表达 | 验证完备性 |
|---------|---------|---------|
| 任务执行 | Intent(input→output) + CompletionHook | ✅ |
| 痛觉驱动进化 | Pain Hook → PainJudge(ConsciousnessNode) → Intent → Evolution Node 链 → CompletionHook | ✅ |
| 路由盲区探测 | RoutingGapHook → RoutingGapJudge → Intent(create_node) → CreateNode Tool → CompletionHook | ✅ |
| 元进化 | EvoCompletionHook → MetaJudge → Intent(evolve_judge) → Evolution Node 链 | ✅ |
| 人工审查 | CompletionHook 条件 = `human_approval_signal` | ✅ |
| 跨机调用 | ExternalTool/Node 在语义网络中注册，Intent 正常路由 | ✅ |

所有机制均可用六元原语无损表达。

---

*LAP V0.4 — Language Anchoring Protocol 正式版 — 2026-03-28*
