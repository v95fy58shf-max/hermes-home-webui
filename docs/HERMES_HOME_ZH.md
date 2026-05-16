# Hermes Home 说明

Hermes Home 是一个外挂式家庭系统层。它不改 Hermes Agent 本体，而是在 Hermes 外侧建立家庭网关、家庭日志和家庭状态基础设施。

## 设计目标

第一阶段解决“多人聊天”：

- 每个家庭成员独立微信登录。
- 每个成员一个 Hermes profile 和从网关。
- 主网关 `home-master` 汇总消息。
- Web UI 负责创建网关、分配端口、切换频道配置。
- 家庭日志长期保存，但不混入个人上下文。

第二阶段解决“家庭状态”：

- 所有输入先进入 Event Bus。
- 长期系统存状态，不只存文本。
- 私人原文不直接共享。
- AI 根据问题按需检索状态和日志。
- 家庭关系成为可演进的数据结构。

## 二阶段模块

### Event Bus

位置：`hermes-home/core/event_bus.py`

所有输入都会被标准化为 Event：

```python
{
    "event_id": "...",
    "family_id": "...",
    "member_id": "...",
    "source": "wechat",
    "type": "chat_message",
    "scope": "private",
    "visibility": "private",
    "timestamp": "...",
    "payload": {}
}
```

这一步的意义是切断“消息直接写长期记忆”的路径。微信消息、成员加入、改名、家庭决定、日程、健康事件、情绪事件、设备状态都应该先变成事件。

### State Engine

位置：`hermes-home/core/state_engine.py`

State Engine 把 Event 转成结构化长期状态：

```python
{
    "state_id": "...",
    "family_id": "...",
    "member_id": "...",
    "scope": "private",
    "type": "emotion/stress",
    "value": 0.72,
    "trend": "up",
    "confidence": 0.81,
    "ttl": 172800,
    "created_at": "...",
    "updated_at": "..."
}
```

长期系统的中心是状态，而不是聊天记录。

### Privacy Scope

位置：`hermes-home/core/privacy.py`

支持的 scope：

- `private`
- `family_shared`
- `summary_only`
- `parent_visible`
- `system_only`
- `agent_safe`

所有 event、memory、state 都必须带 scope。系统允许共享状态摘要，但不允许把私人原文直接转发给其他成员。

### Decay Worker

位置：`hermes-home/core/decay_worker.py`

状态支持：

- `ttl`
- `importance`
- `confidence`
- `decay`

临时情绪、冲突等会随时间衰减或归档，避免长期人格污染。偏好、习惯、健康历史等可以长期保存。

### Memory Router

位置：`hermes-home/core/memory_router.py`

Memory Router 负责：

1. 分析用户问题。
2. 选择需要检索的状态类型。
3. 按隐私范围过滤。
4. 脱敏和摘要。
5. 把必要上下文注入 Hermes。

例如“孩子最近怎么样？”可以检索情绪趋势、关系摘要、睡眠趋势，但不能直接读取全部聊天记录。

### Relationship Graph

位置：`hermes-home/core/relationship_graph.py`

家庭系统关注关系，而不只是账号：

```python
{
    "member_a": "...",
    "member_b": "...",
    "relationship_state": {
        "trust": 0.71,
        "tension": 0.43,
        "support": 0.82
    },
    "updated_at": "..."
}
```

关系状态可由家庭关系分析器和后续人工确认逐步更新。

### Expert Analyzers

位置：`hermes-home/analyzers/`

当前包含：

- `emotion_analyzer.py`
- `sleep_analyzer.py`
- `family_relation_analyzer.py`
- `elderly_health_analyzer.py`

这些分析器不是聊天机器人。它们输入 event/state，输出低 token、可解释、可组合、可脱敏的状态信号。

## 和 Hermes 的边界

禁止修改：

- Hermes memory 内核
- Hermes runtime
- Hermes upstream package

Hermes Home 把 Hermes 当成可替换运行时。未来可以替换成 Hermes、LangGraph、OpenClaw 或其他 runtime，但家庭系统层应继续独立存在。
