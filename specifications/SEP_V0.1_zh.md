# 语义交换协议（SEP）V0.1
## Semantic Exchange Protocol — Cross-Machine Six-Primitive Interoperability

> **状态**：草案 / V0.1
> **日期**：2026-03-28
> **基于**：LAP V0.4 + 六元语义接口规范 V1.0
> **定位**：定义外部系统如何作为六元原语接入语义节点网格，实现跨机、跨组织的语义级互操作

---

## 核心设计理念

### 语义精确优于格式精确

传统互操作协议（REST/RPC/gRPC）的核心是**格式契约**：调用方和被调用方必须就精确的数据结构达成共识，任何格式偏差都是错误。

SEP 的核心是**语义契约**：参与方就"这个操作的语义意图"达成共识，格式是实现细节，可以在运行时协商。

在 LLM 密集系统中：
- 格式校验失败 → 需要人工处理
- 语义理解失败 → 也需要人工处理
- **格式不匹配但语义可理解** → LLM 可以自动桥接，系统继续运行

因此，SEP 将格式约束视为可选的优化，而非必要的前提条件。

### 以示例注册，而非以 Schema 注册

外部节点注册时不需要提供 JSON Schema 或 OpenAPI 规范。需要提供的是：
- 自然语言描述：这个原语做什么
- 3-5 个示例：输入 Signal → 输出 Signal 的具体例子

系统从示例中推断 Format，在语义网络中注册节点。这使得注册过程对 LLM 友好、对人类友好，同时保留了足够的语义信息供路由器使用。

---

## 目录

1. [参与方类型](#1-参与方类型)
2. [注册协议](#2-注册协议)
3. [发现协议](#3-发现协议)
4. [Signal 交换协议](#4-signal-交换协议)
5. [Format 协商](#5-format-协商)
6. [Hook 订阅协议](#6-hook-订阅协议)
7. [信任模型](#7-信任模型)
8. [分布式节点网格](#8-分布式节点网格)
9. [完整示例](#9-完整示例)
10. [与传统协议的对比](#10-与传统协议的对比)

---

## 1. 参与方类型

SEP 允许外部系统以六元原语的任意类型接入：

### 1.1 ExternalNode（外部节点）

外部系统作为 Node 接入：接收 Signal，经过处理（可含外部 LLM 调用），返回 Signal。

```
ExternalNode 特征：
- 有语义描述和示例
- 接受 Signal 输入，返回 Signal 输出
- 可以是无状态的（每次调用独立）或有状态的（维护会话）
- HTTP 端点（同步）或 WebSocket 端点（流式）
```

典型用例：
- 外部 LLM 服务（将 Signal 转化为 LLM prompt，返回响应作为 Signal）
- 专业领域分析服务（法律文本分析、医学编码、代码审查）
- 数据转换服务（格式 A → 格式 B 的确定性转换）

### 1.2 ExternalTool（外部工具）

外部系统作为 Tool 接入：执行确定性操作，产生外部世界变化。

```
ExternalTool 特征：
- 操作外部世界（数据库、文件系统、第三方 API）
- 确定性执行（相同输入 → 相同输出）
- 不调用 LLM
- 返回 {"success": bool, "output": str, "state_anchor": {...}}
```

典型用例：
- 数据库写入服务
- 文件存储服务
- 第三方平台 API（飞书消息发送、GitHub Issue 创建）
- 编译/测试执行服务

### 1.3 ExternalHook（外部 Hook）

外部系统作为 Hook 接入：主动推送 Signal 给节点网格。

```
ExternalHook 特征：
- 主动推送（不是被动响应）
- 监控外部事件，在条件满足时向网格注入 Signal
- WebSocket/SSE 流（推送模型）
- 不调用 LLM，不修改外部状态
```

典型用例：
- CI/CD 系统（构建失败时推送 Signal）
- 监控告警（指标超阈值时推送 Signal）
- 用户行为事件（用户提交代码时推送 Signal）
- 外部数据变更（数据库变更通知）

### 1.4 FormatProvider（Format 提供方）

外部系统提供领域 Format 定义，供网格中其他节点使用。

```
FormatProvider 特征：
- 提供 FormatSpec 定义（含描述和示例）
- 可以批量注册一个领域的所有 Format
- 可以提供 Format 继承关系
- HTTP 端点（声明性，只读）
```

典型用例：
- 行业标准语义类型库（医疗 HL7、金融 FIBO）
- 公司内部领域 Format 注册中心
- 开源语义类型社区

---

## 2. 注册协议

### 2.1 注册请求

外部原语向任意 SEP 节点的 `/sep/v1/register` 端点发送注册请求。

**请求格式（HTTP POST）**：

```json
{
  "primitive_type": "node | tool | hook | format_provider",
  "identity": {
    "name": "feishu-message-analyzer",
    "description": "分析飞书消息的语义内容，提取结构化信息（任务、决策、行动项）",
    "version": "1.2.0",
    "maintainer": "team-collab@example.com"
  },
  "examples": [
    {
      "input": {
        "format": "feishu.message.raw",
        "text": "【紧急】明天截止，请评审 PR #123 并合入"
      },
      "output": {
        "format": "task.structured",
        "text": "任务：评审 PR #123 并合入；截止时间：明天；优先级：紧急；指派人：未指定"
      }
    },
    {
      "input": {
        "format": "feishu.message.raw",
        "text": "已确认：本次迭代聚焦登录流程优化，其他需求延期"
      },
      "output": {
        "format": "decision.structured",
        "text": "决策：本次迭代范围 = 登录流程优化；延期需求数量 = 其余所有；决策者 = 未知"
      }
    }
  ],
  "endpoint": {
    "url": "https://feishu-analyzer.internal/sep/process",
    "transport": "http",
    "timeout_seconds": 30,
    "streaming": false
  },
  "visibility": ["public", "internal"],
  "capabilities": {
    "max_signal_length": 8000,
    "languages": ["zh", "en"],
    "llm_powered": true
  }
}
```

**注意**：没有强制的 JSON Schema，没有 OpenAPI 规范要求。示例就是合约。

### 2.2 注册响应

```json
{
  "status": "registered",
  "node_id": "ext.feishu-message-analyzer.01KM...",
  "inferred_formats": {
    "input": ["feishu.message.raw", "feishu.message.*"],
    "output": ["task.structured", "decision.structured"]
  },
  "semantic_summary": "分析飞书消息内容，提取任务、决策、行动项等结构化语义",
  "mesh_nodes": ["node.local:7890", "node.peer1:7891"],
  "registered_at": "2026-03-28T10:00:00Z",
  "expires_at": "2026-04-28T10:00:00Z",
  "heartbeat_interval_seconds": 300
}
```

- `node_id` 是此外部原语在语义网格中的全局唯一标识
- `inferred_formats` 是系统从示例中推断的 Format（非强制约束，用于路由参考）
- 注册有效期默认 30 天，需通过心跳续期

### 2.3 注册生命周期

```
注册请求 → 语义推断（LLM 分析示例）→ 节点网格注册
    ↓
周期心跳（每 N 分钟 POST /sep/v1/heartbeat）
    ↓
心跳超时 → 节点标记为 inactive（不删除，保留历史）
    ↓
重新注册 → 恢复 active 状态（node_id 不变）
```

---

## 3. 发现协议

### 3.1 意图查询（语义发现）

调用方不通过名称查找节点，而是通过**语义意图**查询：

**请求（HTTP GET /sep/v1/discover）**：

```json
{
  "intent": "分析一段自然语言文本，提取其中包含的任务和行动项",
  "input_format_hint": "feishu.message.*",
  "output_format_hint": "task.*",
  "visibility_required": "internal",
  "min_confidence": 0.6
}
```

**响应**：

```json
{
  "candidates": [
    {
      "node_id": "ext.feishu-message-analyzer.01KM...",
      "name": "feishu-message-analyzer",
      "semantic_similarity": 0.92,
      "inferred_input_formats": ["feishu.message.raw"],
      "inferred_output_formats": ["task.structured"],
      "description": "分析飞书消息内容，提取任务、决策、行动项等结构化语义",
      "endpoint_url": "https://feishu-analyzer.internal/sep/process",
      "last_seen": "2026-03-28T09:55:00Z"
    },
    {
      "node_id": "sed.task_extractor.01KM...",
      "name": "sed.task_extractor（本地沉淀节点）",
      "semantic_similarity": 0.78,
      "description": "从 Agent 执行轨迹中沉淀的任务提取节点",
      "endpoint_url": "local://sed.task_extractor"
    }
  ]
}
```

发现是**语义匹配**，不是名称查找。没有精确的 Format ID 匹配要求。

### 3.2 Format 查询

查询某个 Format 的定义和示例（用于理解和兼容性评估）：

```
GET /sep/v1/formats/{format_id}
GET /sep/v1/formats?query=飞书消息&domain=collaboration
```

---

## 4. Signal 交换协议

### 4.1 Signal 信封

所有 SEP 消息都使用 LAP V0.4 的**消息信封**包装。SEP 在其基础上新增 `sep_metadata` 字段：

```json
{
  "lap_version": "0.4",
  "envelope_id": "01KM...",
  "task_id": "01KM...",
  "origin": {
    "kind": "external_node",
    "identity": "node:sed.routing_gap_judge"
  },
  "signal": {
    "format": "feishu.message.raw",
    "text": "【紧急】明天截止，请评审 PR #123 并合入",
    "node_id": "sed.routing_gap_judge",
    "meta": {
      "source_channel": "feishu_group_12345",
      "message_id": "om:abc123"
    }
  },
  "visibility": "internal",
  "sep_metadata": {
    "target_node_id": "ext.feishu-message-analyzer.01KM...",
    "routing_confidence": 0.92,
    "fallback_node_ids": ["sed.task_extractor.01KM..."],
    "timeout_seconds": 30,
    "require_state_anchor": false
  }
}
```

### 4.2 外部节点的响应格式

外部节点处理后返回同样的信封格式，`signal` 字段是处理结果：

```json
{
  "lap_version": "0.4",
  "envelope_id": "01KM...(新ID)",
  "task_id": "01KM...(同一 task_id)",
  "origin": {
    "kind": "external_node",
    "identity": "node:ext.feishu-message-analyzer"
  },
  "signal": {
    "format": "task.structured",
    "text": "任务：评审 PR #123 并合入；截止时间：明天；优先级：紧急；指派人：未指定",
    "node_id": "ext.feishu-message-analyzer.01KM...",
    "meta": {
      "confidence": 0.95,
      "extracted_items": 1,
      "source_message_id": "om:abc123"
    }
  },
  "state_anchor": null,
  "visibility": "internal"
}
```

### 4.3 格式宽容原则

外部节点**必须**实现格式宽容：

```
格式宽容 = 在 Signal 语义可理解时不拒绝请求，即使格式 ID 不精确匹配

具体来说：
- 收到 Signal.format="feishu.message.thread" 时，若节点描述覆盖飞书消息，尝试处理
- 不能仅因为 format ID 字符串不完全匹配就返回 "format not supported" 错误
- 可以在响应中说明"以 feishu.message.raw 处理，置信度 0.80"
```

格式宽容是 SEP 与传统 API 的核心差别：语义理解决定是否处理，格式标签是参考不是门槛。

---

## 5. Format 协商

### 5.1 自动协商流程

当路由器将 Signal 发送给外部节点时，若输出 Format 与目标 Format 不精确匹配：

```
Step 1：语义相似度检查
  router.semantic_similarity(
    source_format="task.structured",
    target_format="task.action_item"
  ) → 0.85

Step 2：若相似度 > 阈值（默认 0.70）
  自动插入 LLM Transformer Node
  Transformer 收到 Signal(format="task.structured", text=...)
  Transformer 产出 Signal(format="task.action_item", text=...)

Step 3：若相似度 < 阈值
  返回 Signal(format="routing.gap", text="无法在 task.structured 和 task.action_item 之间找到语义桥接")
  触发 RoutingGapJudgeNode → 可能创建新的专化节点
```

### 5.2 手动 Format 声明

外部节点可以在响应中主动声明实际产出的 Format（若与请求的不同）：

```json
{
  "signal": {
    "format": "task.structured",
    "text": "...",
    "meta": {
      "intended_format": "task.structured",
      "actual_format_note": "已尽力匹配 task.action_item 语义，但更适合标注为 task.structured"
    }
  }
}
```

路由器会将此声明用于后续的格式推断学习。

### 5.3 Format 示例交换

两个节点首次建立连接时，可以交换各自的 Format 示例，以便双方更好地理解对方的语义边界：

```
GET /sep/v1/formats/examples?node_id=ext.feishu-message-analyzer.01KM...

返回该节点注册时提供的所有 input/output 示例对
```

---

## 6. Hook 订阅协议

### 6.1 ExternalHook 注册

ExternalHook 通过 WebSocket 向 SEP 节点的 `/sep/v1/hook/subscribe` 端点建立持久连接：

```json
POST /sep/v1/hook/register
{
  "primitive_type": "hook",
  "hook_type": "event",
  "identity": {
    "name": "ci-failure-hook",
    "description": "监控 CI/CD 流水线，在构建或测试失败时发出 Signal"
  },
  "signal_formats": ["ci.build.failed", "ci.test.failed"],
  "examples": [
    {
      "event": "build_failed",
      "output_signal": {
        "format": "ci.build.failed",
        "text": "构建失败：main 分支，commit abc123，错误：TypeScript 编译错误 42 个"
      }
    }
  ],
  "push_endpoint": "wss://ci-hook.internal/sep/push",
  "visibility": "internal"
}
```

### 6.2 Signal 推送

ExternalHook 在事件发生时向 SEP 节点推送信封，不等待响应：

```
WebSocket 消息（ExternalHook → SEP 节点）：
{
  "envelope_id": "01KM...",
  "signal": {
    "format": "ci.build.failed",
    "text": "构建失败：main 分支，commit abc123，TypeScript 编译错误 42 个",
    "node_id": "ext.ci-failure-hook"
  },
  "visibility": "internal"
}
```

SEP 节点收到后，将 Signal 注入语义网格，由订阅此 Format 的 ConsciousnessNode 消费。

### 6.3 Hook 触发条件声明

ExternalHook 可以声明触发条件（供路由器过滤），减少不必要的 Signal 传播：

```json
"trigger_conditions": {
  "natural_language": "仅在实际发生错误时触发，不在成功时触发",
  "signal_frequency": "event_driven",
  "estimated_daily_signals": 50,
  "cooldown_seconds": 60
}
```

---

## 7. 信任模型

### 7.1 信任层级

SEP 不使用传统的 API Key 认证作为主要信任机制——因为 API Key 是格式契约的一部分，而 SEP 优先语义契约。信任通过**能力声明 + StateAnchor 验证**建立：

| 信任层级 | 验证方式 | 适用场景 |
|---------|---------|---------|
| **公开**（public）| 无验证，直接接受 | 公开 Format 定义查询、发现 API |
| **内部**（internal）| 网络层隔离（同 VPC/内网）| 组织内部节点间 Signal 交换 |
| **验证**（verified）| StateAnchor 验证 | 跨组织、高价值 Signal 交换 |
| **人工审查**（reviewed）| 每次操作需人工确认 | 敏感操作（写入生产数据库等）|

### 7.2 StateAnchor 作为信任凭证

跨组织 Signal 交换时，外部节点可以提供 StateAnchor 证明其产出的真实性：

```json
"state_anchor": {
  "kind": "file_hash",
  "ref": "sha256:abc...",
  "path": "s3://company-data/analysis_result.json",
  "verified_at": "2026-03-28T10:00:00Z"
}
```

接收方可以独立验证此 StateAnchor，建立对 Signal 内容的信任，而无需信任发送方的身份。

### 7.3 能力声明透明度

所有注册的外部原语必须声明：
- 是否调用 LLM（`llm_powered: true/false`）
- 是否会修改外部状态（`has_side_effects: true/false`）
- 数据保留策略（`data_retention: "none" | "session" | "persistent"`）
- 可见性支持范围（`visibility: ["public", "internal"]`）

这些声明用于路由器的风险评估，不是技术限制——外部节点可以声明任何内容，但声明与行为不符会影响信任分数。

---

## 8. 分布式节点网格

### 8.1 架构

```
┌─────────────────────────────────────────────────────────┐
│                    语义节点网格                           │
│                                                         │
│   ┌──────────────┐     ┌──────────────┐                 │
│   │  本地 LSR     │◄────►  Peer LSR   │                 │
│   │ (Local       │     │ (远程节点)   │                 │
│   │ Semantic      │     └──────────────┘                 │
│   │ Router)       │              │                       │
│   └──────┬───────┘              │                       │
│          │                      ▼                       │
│   ┌──────┴──────┐      ┌──────────────┐                 │
│   │ 本地节点集  │      │ 外部节点集   │                 │
│   │ (sed.*, evo.*) │      │ (ext.*)    │                 │
│   └─────────────┘      └──────────────┘                 │
└─────────────────────────────────────────────────────────┘
         ▲                         ▲
         │                         │
   ┌─────┴──────┐          ┌───────┴────────┐
   │ ExternalHook│          │ ExternalNode   │
   │ (推送 Signal)│         │ (接收/返回     │
   └────────────┘          │ Signal)        │
                           └────────────────┘
```

### 8.2 本地语义路由器（LSR）

每个参与 SEP 的节点运行一个 LSR，负责：
- 管理本地注册的原语（本地节点 + 在此 LSR 注册的外部节点）
- 接收 Intent，匹配最优节点（本地优先，再查询 Peer）
- 转发 Signal 到本地或远程节点
- 维护节点健康状态（心跳监控）

```
LSR 路由决策：
1. 接收 Intent(input_format, output_format)
2. 查询本地语义网络（semantic_network.db）
3. 若本地无匹配，查询 Peer LSR
4. 按语义相似度排序候选节点
5. 发送 Signal 给最优候选节点
6. 若候选节点失败，尝试下一个（降级路由）
```

### 8.3 Peer 链接

LSR 之间通过 Peer 链接互相感知：

```json
POST /sep/v1/peer/link
{
  "peer_endpoint": "https://other-org.internal/sep",
  "peer_name": "data-team-cluster",
  "shared_visibility": ["internal"],
  "sync_formats": true
}
```

Peer 链接建立后：
- 双方同步 public/internal Format 定义
- 跨 Peer 的 Intent 路由成为可能
- 各方保持对等关系，无中心节点

---

## 9. 完整示例

### 场景：外部飞书分析服务接入

**步骤 1：外部服务注册**

```bash
curl -X POST https://local-lsr/sep/v1/register \
  -H "Content-Type: application/json" \
  -d '{
    "primitive_type": "node",
    "identity": {
      "name": "feishu-task-extractor",
      "description": "从飞书消息中提取结构化任务信息"
    },
    "examples": [
      {
        "input": {"format": "feishu.message.raw", "text": "明天之前需要完成代码评审"},
        "output": {"format": "task.structured", "text": "任务：代码评审；截止：明天；状态：待完成"}
      }
    ],
    "endpoint": {"url": "https://feishu-extractor.svc/process", "transport": "http"}
  }'
```

**步骤 2：语义网格中的路由**

系统内某个 ConsciousnessNode 产出 Intent：

```python
Intent(
    text="分析最新飞书消息，提取今日待办任务",
    input_format="feishu.message.raw",
    output_format="task.structured",
    priority=0.7
)
```

LSR 查询语义网络，找到匹配的外部节点（相似度 0.94），发送 Signal：

```json
{
  "signal": {
    "format": "feishu.message.raw",
    "text": "收到 15 条新消息，含：明天 standup 改到 10:30；PR #456 需要评审；新需求文档已上传",
    "node_id": "hook.feishu_poller"
  },
  "sep_metadata": {"target_node_id": "ext.feishu-task-extractor.01KM..."}
}
```

**步骤 3：外部节点处理并返回**

```json
{
  "signal": {
    "format": "task.structured",
    "text": "今日待办（3项）：1. 出席 10:30 standup；2. 评审 PR #456；3. 阅读新需求文档；全部优先级：中",
    "node_id": "ext.feishu-task-extractor.01KM...",
    "meta": {"item_count": 3, "confidence": 0.91}
  }
}
```

**步骤 4：CompletionHook 触发**

观测到 Signal.format="task.structured" 匹配 Intent.output_format="task.structured"，CompletionHook 触发，Intent 完成，Consciousness 环闭合。

---

### 场景：Format 协商桥接

调用方期望 `task.action_item`，外部节点输出 `task.structured`：

```
语义相似度检查：
  task.structured ↔ task.action_item → 0.82（超过阈值 0.70）

自动插入 LLM Transformer：
  输入：Signal(format="task.structured", text="今日待办（3项）：...")
  输出：Signal(format="task.action_item", text="行动项列表：□ 10:30 standup □ 评审 PR #456 □ 阅读需求文档")

路由继续，无需人工干预
```

---

## 10. 与传统协议的对比

| 维度 | REST/RPC | MCP（Model Context Protocol）| SEP（本协议）|
|------|---------|--------------------------|------------|
| 注册方式 | OpenAPI / Protobuf Schema | Tool 名称 + JSON Schema | 自然语言描述 + 示例 |
| 发现方式 | 服务名称 + 端点 URL | Tool 名称精确匹配 | 语义意图查询 |
| 格式约束 | 强制（Schema 不匹配 = 错误）| 强制（JSON Schema）| 软性（语义可理解即可）|
| 格式不匹配时 | 返回 4xx 错误 | 返回错误 | LLM 自动桥接 |
| 信任机制 | API Key / OAuth | — | StateAnchor + 能力声明 |
| 状态追踪 | 无标准 | 无标准 | Task + Intent 生命周期 |
| 推送模型 | Webhook（格式固定）| — | ExternalHook（Signal 信封）|
| 适合场景 | 高确定性、低 LLM 密度 | 工具调用场景 | LLM 密集、语义多变场景 |

**SEP 与 MCP 的关系**：MCP 解决了"LLM 如何访问工具"（输入侧）；SEP 解决了"跨机 LLM 系统如何在语义层互操作"（语义路由侧）。两者互补，不互斥。MCP Tool 可以包装为 SEP ExternalTool 参与语义网格。

---

## 附录 A：SEP 端点规范

### LSR 必须实现的端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/sep/v1/register` | POST | 注册外部原语 |
| `/sep/v1/heartbeat` | POST | 心跳续期 |
| `/sep/v1/discover` | GET/POST | 语义发现查询 |
| `/sep/v1/formats/{id}` | GET | 查询 Format 定义 |
| `/sep/v1/signal` | POST | 发送 Signal 给目标节点 |
| `/sep/v1/hook/register` | POST | 注册 ExternalHook |
| `/sep/v1/hook/subscribe` | WS | ExternalHook 推送连接 |
| `/sep/v1/peer/link` | POST | 建立 Peer 链接 |
| `/sep/v1/health` | GET | LSR 健康状态 |

### 外部节点必须实现的端点

ExternalNode 只需实现一个处理端点（在注册时声明）：

```
POST {endpoint.url}
  Body: LAP V0.4 Message Envelope（含 signal 字段）
  Response: LAP V0.4 Message Envelope（含 signal 字段）
  HTTP Status: 200（成功）| 422（语义无法处理）| 503（节点不可用）
```

**重要**：外部节点不应返回 `400 Bad Request`（格式错误），而应返回 `422 Unprocessable Entity`（语义无法处理），并在响应 signal.text 中说明原因。这体现了"语义精确优于格式精确"的原则。

---

## 附录 B：最小可行注册

以最少的信息注册一个有效的 ExternalNode：

```json
{
  "primitive_type": "node",
  "identity": {
    "name": "my-text-summarizer",
    "description": "将长文本压缩为 3-5 句摘要"
  },
  "examples": [
    {
      "input": {"format": "text.long", "text": "（长文本示例...）"},
      "output": {"format": "text.summary", "text": "（摘要示例）"}
    }
  ],
  "endpoint": {"url": "http://localhost:8080/summarize", "transport": "http"}
}
```

最小注册即可参与语义网格。随着使用积累，系统会从实际 Signal 交互中学习更精确的 Format 推断。

---

*语义交换协议（SEP）V0.1 — 六元跨机互操作 — 2026-03-28*
