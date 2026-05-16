# Hermes Home WebUI

Hermes Home WebUI 是基于 Hermes Agent 和 Hermes Web UI 的家庭版改造。目标不是把 Hermes 改成另一个不可维护的本体，而是在 Hermes 外面增加一层可替换、可升级、可长期演进的家庭系统层。

核心原则：

- 不修改 Hermes Agent 内核。
- Hermes 只作为 LLM Runtime Provider。
- 多微信、多成员、家庭状态、家庭记忆都放在外挂层。
- 发布源码时不包含模型 API、微信登录态、个人记忆、运行数据库和服务器密钥。

## 源码来源

本项目基于以下开源项目二次开发：

- Hermes Agent: https://github.com/NousResearch/hermes-agent
- Hermes Web UI: https://github.com/EKKOLearnAI/hermes-web-ui

原项目版权、协议和贡献归原作者所有。本仓库保留 Web UI 管理基础，并新增 `hermes-home/` 家庭层、Web UI 多网关管理和家庭状态系统。

## 第一阶段成果

- 多微信独立 profile，每个家庭成员一个从网关。
- `home-master` 主网关统一接收从网关消息。
- `home-slave-relay` 插件把从网关消息转发给主网关。
- Web UI 支持新建网关，端口自动递增。
- 新建网关会清空频道配置和微信凭据，避免复制登录态。
- 频道页面支持按运行中的网关动态切换配置。
- 首次微信绑定后会询问用户身份。
- 用户说“我是妈妈”“我叫张三”“叫我小王”时，可同步更新网关显示名。
- 新增家庭日志，和个人聊天上下文分离。
- 家庭日志支持搜索、重要性过滤、新增、编辑和删除。
- 新增家庭日志 skill，让 Hermes 知道必要时可检索家庭长期信息。

## 第二阶段目标

第二阶段开始从“多人聊天系统”升级为“家庭状态系统”。

新增基础设施：

- Event Bus：所有输入先统一成事件。
- State Engine：把事件转成长期结构化状态。
- Privacy Scope：所有 event、memory、state 都带隐私范围。
- Decay Worker：状态和记忆支持 TTL、importance、confidence、decay。
- Memory Router：根据问题决定检索哪些状态或日志，再脱敏注入 Hermes。
- Relationship Graph：把家庭关系作为一等对象，而不是只看账号。
- Expert Analyzers：情绪、睡眠、家庭关系、老人健康等低 token 分析器。

核心链路：

```text
微信/设备/NAS
      ↓
Gateway Layer
      ↓
Event Bus
      ↓
State Engine
      ↓
Privacy Filter
      ↓
Memory Router
      ↓
Relationship Graph
      ↓
Expert Analyzers
      ↓
Hermes / LLM
      ↓
家庭建议与交互
```

## 隐私原则

家庭系统不直接转发私人原文，而是做状态转发。

例子：

- 孩子原话：“我讨厌妈妈”
- 原始事件 scope：`private`
- 可共享摘要 scope：`summary_only`
- 注入给家庭层的内容：“孩子近期家庭关系压力偏高”

目前定义的隐私范围：

- `private`
- `family_shared`
- `summary_only`
- `parent_visible`
- `system_only`
- `agent_safe`

## 目录

```text
hermes-home/
  master_gateway.py
  config.example.yaml
  core/
    event_bus.py
    state_engine.py
    privacy.py
    decay_worker.py
    memory_router.py
    relationship_graph.py
  analyzers/
    emotion_analyzer.py
    sleep_analyzer.py
    family_relation_analyzer.py
    elderly_health_analyzer.py
  plugins/home_slave_relay/
  skills/family-logs/SKILL.md
  systemd/hermes-home-master.service
  scripts/install-home-master.sh

docs/HERMES_HOME_ZH.md
docs/RELEASE_SANITIZE.md
```

## 安装概览

```bash
cd hermes-home
sudo bash scripts/install-home-master.sh
sudo nano /opt/hermes-home/config.yaml
sudo systemctl start hermes-home-master.service
```

然后启动 Web UI，在“网关”页面新建从网关，在“频道”页面选择对应网关扫码绑定微信。

## 发布清理

仓库不应包含：

- 模型 API key 或 provider 凭据
- 微信 token、account ID、OpenID、cookie、扫码状态
- Hermes 会话、历史、个人记忆、用户画像、persona 私有内容
- `/opt/hermes-home/home.db`
- Web UI token、运行数据库、日志
- 服务器 IP、密码、SSH key

详见 `docs/RELEASE_SANITIZE.md`。
