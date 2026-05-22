# Hermes Home WebUI 维护说明

本仓库不是原版 Hermes Web UI。

这是一个面向家庭、团队、企业或小组织的多成员网关版本。它保留 Hermes Agent 本体可更新，把多微信、多网关、共享记忆和统一管理放在外挂层与 WebUI 改造层。

## 维护时不要误删的改造

- 侧边栏不应该再出现“用户 / profile”切换器。
- Web 管理端是单管理员视角，默认指向 `home-master`，界面显示为 `master`。
- `default` 是原版 profile，不应该在已有 `home-master` 时显示为管理网关。
- “频道”页顶部必须有动态网关选项卡，用于切换 `master / wechat2 / wechat3 ...` 并分别配置各自频道。
- 微信扫码、token、Account ID 等频道配置必须按网关隔离，不能共用一份。
- “记忆”“历史”“用户画像”等成员相关页面应按网关选项卡切换；共享记忆单独全局保存。
- “对话”只保留给主网关测试使用，指向 `home-master`。
- 不要恢复原版 profile 管理页、profile selector、profile switch UX。
- 不要恢复原版群聊 UI。多 agent 协作应通过 skill 或 workflow 调用，不应该做成多人同时发言的聊天页面。

## 判断是否跑错版本

如果页面出现下面情况，通常说明服务器跑回了原版或旧版 WebUI：

- 左下角出现“用户 default”下拉框。
- “频道”页上方没有网关选项卡。
- `/api/hermes/gateways` 返回里把 `default` 当成一个普通网关显示。
- “网关”页没有 `master` 这个显示名，而是显示 `home-master` 或 `default`。

## 设计原则

- Hermes Agent 本体不可侵入修改，方便后续更新。
- `home-master` 是系统主网关，负责聚合、记忆检索和统一回复。
- `wechat2`、`wechat3` 等从网关只是独立微信入口，每个从网关有自己的 profile、端口、登录态和频道配置。
- 新建从网关时，端口递增，频道凭据清空，启动后自动加入主网关 relay。
- 长期共享记忆不混入个人聊天上下文，只在需要时检索。

