# Language Anchoring Protocol (LAP) — V0.3 规范

> **状态**：Draft / V0.3
> **日期**：2026-03-20
> **作者**：LAP Protocol Authors
> **项目**：OmniFactory
> **相较 V0.2 的变更**：新增七项协议原语，源自 Explorer V4 实验和软件工程设计审查发现的缺口。所有新增均为向后兼容——V0.2 管线无需修改即可继续运行。

---

## 目录

1. [新原语：StateAnchor — 物理世界状态](#1-新原语stateanchor)
2. [新原语：Task — 有状态执行实例](#2-新原语task)
3. [新原语：消息信封 — 传输无关协议载体](#3-新原语消息信封)
4. [可见性与隐私：公开/内部/私有分级](#4-可见性与隐私)
5. [响应模式：单点响应 vs 全链路追踪](#5-响应模式)
6. [溯源字段：意图步骤可追溯性](#6-溯源字段)
7. [元代理操作协议 (LAP-MOP)](#7-元代理操作协议-lap-mop)
8. [标准库标签更新](#8-标准库标签更新)

---

## 1. 新原语：StateAnchor

### 1.1 动机

**发现于 Explorer V4 实验（2026-03-20）：**

一个 Agent 声称已生成 `feishu_message_output`（一个语义类型标签）。后续任务将此标签用作执行起点——但以该名称命名的文件或可检索实体从未存在过。Agent 在允许的 25 步内全部用于寻找那个从未被创建的文件，最终失败。

**根本原因**：LAP V0.1/V0.2 定义了数据的"语义类型"，但从未定义"管线执行时的物理世界状态"。这导致两类本质不同的对象被混为一谈：

- `agent_output` — LLM 声称已生成的语义标签（仅在当前追踪上下文内有效）
- `state_anchor` — 可独立验证的物理事实（git 哈希、文件摘要、版本控制号）

### 1.2 定义

**StateAnchor** 是物理世界中可独立验证的参照点：

```
StateAnchor = {
    kind:        StateKind     -- 可靠性等级（见下文）
    ref:         str           -- 标识符（"abc123" / "sha256:..." / "CL:12345"）
    path:        str | None    -- 文件路径或服务 URL
    verified_at: datetime      -- 最后一次确认此锚点的时间
    is_mutable:  bool          -- 外部行为者是否可修改（如用户在 P4 CL 上继续编辑）
    trace_id:    str           -- 哪个 Agent 追踪产生/观测了此锚点
}
```

### 1.3 StateKind 可靠性等级

| 等级 | Kind | 可靠性 | 备注 |
|------|------|-------|------|
| 1（最高）| `git_commit` | 不可变 | 一旦推送，内容永不改变 |
| 2 | `file_hash` | 内容绑定 | 文件内容的 SHA-256；路径可变 |
| 3 | `p4_changelist` | 服务器真相 | 用户可能在其上继续编辑 → `is_mutable=True` |
| 3 | `svn_revision` | 服务器真相 | 同 P4；检查 `is_mutable` |
| 4 | `api_snapshot` | 时间有界 | 某时刻的外部服务状态；有 TTL |
| 5（最低）| `agent_output` | ⚠️ 短暂 | LLM 声称已生成。**绝不用作管线入口点。** |

### 1.4 核心晋升规则

`agent_output` 锚点当且仅当满足以下条件时，可**晋升**为 `file_hash`：

1. Agent 已将输出写入指定文件路径。
2. 硬锚定器（如文件存在性检查 + sha256 计算）已验证该文件。
3. 新计算的 sha256 成为新的 `ref`，`kind` 变更为 `FILE_HASH`。

```
变更前：StateAnchor(kind=AGENT_OUTPUT, ref="feishu_message_output", ...)
        — Agent 声称已生成，未经验证

变更后：StateAnchor(kind=FILE_HASH, ref="sha256:abc...", path="data/feishu_msg.json", ...)
        — 文件实际存在，与声称输出一致
```

### 1.5 StateSnapshot

**StateSnapshot** 是在 `run_agent` 调用开始时捕获的一组 StateAnchor：

```json
{
  "task_id": "01KM...",
  "trace_id": "01KM...",
  "assertion": "HARD",
  "anchors": [
    {"kind": "git_commit", "ref": "abc123", "path": "e:/WindowsWorkspace"},
    {"kind": "file_hash", "ref": "sha256:...", "path": "data/feishu_v1_state.json"}
  ]
}
```

`assertion` 声明快照的整体可信度：
- `"HARD"` — 所有锚点均已独立验证
- `"SOFT"` — 用户断言或 LLM 推断，未独立验证

---

## 2. 新原语：Task

### 2.1 动机

LAP V0.1/V0.2 定义了 `Pipeline`（静态蓝图）和 `Anchor`（执行单元），但没有 **Task** 的概念——Pipeline 执行的有状态运行时实例。

没有 Task 原语：
- 没有标准方式表示"暂停并等待人工审查"
- 没有标准方式表示"此任务由子任务组成"
- 成功/失败无法传播回路由图
- 任务历史在重启后不累积

### 2.2 定义

```
Task = {
    task_id:        str              -- ULID，全局唯一
    parent_task_id: str | None       -- 子任务用；None = 根任务
    origin:         TaskOrigin       -- 发起者：human | explorer | meta_agent
    pipeline_id:    str              -- 此任务运行的 Pipeline 蓝图
    state_snapshot: StateSnapshot    -- 任务开始时的物理世界状态
    status:         TaskStatus       -- pending | running | paused | completed | failed
    result:         str | None       -- 最终 Agent 输出（completed 时）
    trace_id:       str | None       -- 关联的意图追踪 ID
    created_at:     datetime
    completed_at:   datetime | None
}
```

**TaskStatus 转换**：
```
pending → running → completed
                 → failed
                 → paused → running   （人工审查后）
```

### 2.3 任务谱系

Task 通过 `parent_task_id` 形成树结构。这允许：
- **Explorer 会话**：一个 Explorer 实例生成的所有任务共享同一 `session_task_id` 作为 `parent_task_id`
- **人工升级**：Agent 无法继续时，创建 `paused` 任务，人工恢复
- **元代理扇出**：规划任务并行生成多个执行子任务

---

## 3. 新原语：消息信封

### 3.1 动机

LAP 目前完全以进程内函数调用运行。没有定义 LAP 消息在网络上传输时的外观。这阻止了：
- LAP 消息的 HTTP/WebSocket/文件传输
- 跨组织在共享 Pipeline 上协作
- 隐私保护的消息转发（在外部投递前剥离私有字段）

### 3.2 LAP 消息信封

**传输无关信封**，将任何 LAP 载荷包装用于传输：

```json
{
  "lap_version": "0.3",
  "envelope_id": "01KM4Z2A...",
  "task_id":     "01KM4XZD...",
  "parent_id":   "01KM4X...",
  "origin": {
    "kind":     "human | agent | system",
    "identity": "user@example.com | agent:explorer-v4 | cron"
  },
  "visibility": "private | internal | public",
  "format_id":   "feishu_state_data",
  "format_tags": ["ground-truth.file", "domain:feishu"],
  "state_anchor": {
    "kind": "file_hash",
    "ref":  "sha256:abc...",
    "path": "data/feishu_v1_state.json"
  },
  "payload": { "...": "任意载荷" },
  "signature": null
}
```

### 3.3 传输绑定

信封与传输无关。各传输协议的绑定：

| 传输 | 用途 | 端点模式 |
|------|------|---------|
| **HTTP REST** | 外部请求、公共 API | `POST /lap/v1/task` |
| **WebSocket** | 流式响应、实时监控 | `ws://host/lap/v1/stream/{task_id}` |
| **文件 / IPC** | 本地进程间、离线队列 | `lap_inbox/` 目录轮询 |
| **SQLite（现有）** | 单机、SQLiteBus | 通过 `FactoryEvent` 进程内调用 |

现有的 `SQLiteBus` + `FactoryEvent` 构成文件/IPC 绑定。`RedisBus`（已在 SDK 合约中预留）是预期的 HTTP/WebSocket 后端。

---

## 4. 可见性与隐私

### 4.1 三个可见性级别

每个消息信封携带 `visibility` 字段：

| 级别 | 含义 | 转发规则 |
|------|------|---------|
| `private` | 敏感数据；不得跨越信任边界 | 外部投递前剥离 |
| `internal` | 组织内部；不对公共 API | 仅返回类型摘要，剥离载荷 |
| `public` | 可完整公开 | 原样返回 |

### 4.2 投影规则（用于外部响应）

响应跨越信任边界时（如外部 HTTP 客户端请求完整追踪）：

```
ProjectedResponse(msg, visibility_level):
  if msg.visibility == "private":
      → 用 {"_redacted": true, "format_id": msg.format_id} 替换载荷
  elif msg.visibility == "internal":
      → 用 {"_summary": msg.format_id, "step_count": ...} 替换载荷
  else:
      → 返回完整载荷
```

### 4.3 各级别示例

| 数据 | 级别 | 理由 |
|------|------|------|
| API 密钥 / OAuth 令牌 | `private` | 绝不离开源系统 |
| 内部文件路径（`E:\WindowsWorkspace\...`）| `private` | 泄露目录结构 |
| Agent 推理步骤 | `internal` | 对同组织调试有用，不公开 |
| 任务状态（pending/completed）| `public` | 可安全公开 |
| 最终任务结果（非敏感时）| `public` | 取决于上下文 |

---

## 5. 响应模式

### 5.1 单点响应

仅返回任务最终状态，不含内部追踪：

```json
{
  "task_id": "01KM...",
  "status": "completed",
  "result_format": "feishu_state_data",
  "result_summary": "message_id=om:abc123",
  "verdict": "PASS",
  "steps_taken": 4,
  "visibility": "public"
}
```

适用场景：调用方只需结果，不需推理路径。

### 5.2 全链路追踪响应

返回完整执行历史，按请求的可见性级别投影：

```json
{
  "task_id": "01KM...",
  "status": "completed",
  "visibility_projection": "internal",
  "semantic_path": [
    "user_request → feishu_state_data → recall_result"
  ],
  "trace": [
    {
      "step": 0,
      "tool": "think",
      "action_class": "acquire",
      "input_types": ["user_request"],
      "output_types": ["feishu_state_data"],
      "desc": "读取 feishu_v1_state.json 获取 message_id",
      "type_source": "llm_infer",
      "route_node_id": "...",
      "route_decision": "MERGE"
    }
  ]
}
```

适用场景：调试、Critic 分析，或构建语义执行图。

---

## 6. 溯源字段

### 6.1 动机

V0.1/V0.2 记录了每个意图步骤**发生了什么**（`input_types`、`output_types`、`action_class`），但没有记录**为何相信类型正确**或**谁触发了这个步骤**。

没有溯源：
- 无法区分"从历史数据可靠匹配"的类型标签 vs. "LLM 凭空发明"的标签
- Critic/调试系统无法判断哪些步骤由人类发起，哪些由 Explorer 发起
- 路由图合并无法追溯到触发合并的具体追踪

### 6.2 V0.3 意图步骤新字段

新增至 `intent_steps` 表和 `IntentTracer`：

| 字段 | 类型 | 值 | 含义 |
|------|------|---|------|
| `type_source` | str | `llm_infer`, `history_match`, `user_explicit` | 语义类型的确定方式 |
| `type_confidence` | float | 0.0–1.0（-1 = 未知）| 类型断言的置信度 |
| `parent_task_id` | str | ULID 或空 | 哪个 Task 生成了此追踪 |
| `origin` | str | `human`, `explorer`, `meta_agent` | 追踪的发起者 |
| `route_node_id` | str | ULID 或空 | 此步骤被合并到的路由节点（由 RouteClassifier 回填）|
| `route_decision` | str | `NEW`, `MERGE`, `NOISE` 或空 | RouteClassifier 对此步骤的决策（回填）|

### 6.3 回填协议

`route_node_id` 和 `route_decision` 在记录时为空，由 `RouteClassifier` 在追踪处理后回填。`IntentTracer.record_route_decision()` 是指定的写回方法。

---

## 7. 元代理操作协议 (LAP-MOP)

### 7.1 动机

Explorer 当前在每次分类时直接写入 `route_graph.db`。这意味着：
- 没有**为何**创建或合并节点的审计追踪
- 没有人工或更高层审查图操作的机制
- 自动合并可能静默破坏历经多次追踪才建立起的精度

### 7.2 图操作原语

LAP-MOP 定义了元代理可对路由图提出的标准操作集：

| 操作 | 参数 | 效果 |
|------|------|------|
| `CreateNode` | `(input_types, output_types, action_class, desc, tool_name, evidence_trace_id)` | 向路由图添加新 `IntentNode` |
| `MergeNodes` | `(node_id_a, node_id_b, canonical_desc, evidence_trace_ids)` | 合并两个语义等价的节点 |
| `SplitNode` | `(node_id, split_criteria, new_nodes)` | 将过于泛化的节点分裂为更精确的节点 |
| `RecordOutcome` | `(node_id, success, trace_id)` | 更新节点的 `success_rate` EMA |
| `ProposeType` | `(type_name, definition, examples, evidence_trace_id)` | 注册新语义类型 |
| `LinkTypes` | `(parent_type, child_type, relationship)` | 声明类型层次关系 |
| `ObsoleteNode` | `(node_id, reason, evidence_trace_id)` | 将节点标记为废弃（不删除）|

### 7.3 操作生命周期

每个 LAP-MOP 操作经历：

```
proposed → [confidence >= auto_accept_threshold] → accepted
         → [confidence < threshold]              → pending_review → accepted | rejected
```

所有操作无论是否被接受都持久化，形成完整审计日志。

### 7.4 证据要求

每个 LAP-MOP 操作必须携带：
- `evidence_trace_id`：触发此提案的追踪 ID
- `confidence`：0.0–1.0（高于阈值的操作自动接受）
- `proposed_by`：`'llm'` | `'embedding_auto'` | `'human'`

---

## 8. 标准库标签更新

V0.3 对 LAP 标准库的新增：

### 8.1 状态与溯源标签

| 标签 | 含义 |
|------|------|
| `state.git_anchored` | Format 实例绑定到特定 git commit |
| `state.file_anchored` | Format 实例已通过文件哈希验证 |
| `state.agent_output` | ⚠️ 短暂；由 Agent 生成，未独立验证 |
| `provenance.llm_infer` | 类型标签由 LLM 推断（默认）|
| `provenance.history_match` | 类型标签从路由图历史匹配 |
| `provenance.user_explicit` | 类型标签由人类明确声明 |

### 8.2 任务与来源标签

| 标签 | 含义 |
|------|------|
| `origin.human` | 由人类发起 |
| `origin.explorer` | 由 Explorer Agent 会话发起 |
| `origin.meta_agent` | 由元代理规划步骤发起 |
| `visibility.private` | 包含敏感信息；不公开 |
| `visibility.internal` | 组织内可用；外部投递前投影 |
| `visibility.public` | 可完整公开 |

---

## 附录：术语表新增（V0.3）

| 术语 | 定义 |
|------|------|
| **StateAnchor** | 物理世界中可独立验证的参照点（git 哈希、文件摘要等），用于锚定 Pipeline 执行时对环境状态的假设。|
| **StateSnapshot** | 任务开始时捕获的 StateAnchor 集合；使 Pipeline 执行可复现。|
| **Task** | Pipeline 执行的有状态运行时实例，具有生命周期（pending/running/paused/completed/failed）和父子关系。|
| **消息信封** | 任何 LAP 载荷在网络或 IPC 上传输时的传输无关包装器。|
| **可见性** | 三级隐私分类（private/internal/public），控制数据如何跨信任边界转发。|
| **LAP-MOP** | 元代理操作协议——带审计追踪和接受生命周期的路由图修改提案的标准操作集。|
| **溯源** | 语义类型标签**如何**确定的记录（LLM 推断 vs. 历史匹配 vs. 明确声明）。|
