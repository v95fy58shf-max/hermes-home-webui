# Hermes 多成员 WebUI

这是一个面向多成员场景改造的 Hermes Web UI 版本。它可以用于家庭，也可以用于小团队、企业、工作室或其他需要多个微信入口的组织。

核心原则：不修改 Hermes Agent 本体。Hermes 仍然可以按上游方式更新；多成员能力通过 Web UI、主网关、从网关插件和共享记忆层实现。

## 源码来源

本项目基于以下开源项目二次开发：

- Hermes Agent: https://github.com/NousResearch/hermes-agent
- Hermes Web UI: https://github.com/EKKOLearnAI/hermes-web-ui

原项目版权、协议与贡献归原作者所有。本仓库新增的多成员网关、微信独立绑定、共享记忆等能力位于 `hermes-home/` 及相关 Web UI 改动中。

## 解决的问题

- 多个成员都需要绑定微信。
- 每个微信登录态必须独立，不能互相覆盖。
- 不能直接修改 Hermes 本体，否则后续不好升级。
- 共享信息需要长期保存，但不能污染每个人自己的聊天上下文。
- Web UI 原本不支持多网关动态创建、切换和按网关配置频道。

## 主要功能

- 主网关 `home-master`：统一接收从网关消息，调用 Hermes 生成回复。
- 从网关 `wechat2`、`wechat3` 等：每个成员一个独立 Hermes profile，用于独立绑定微信。
- Relay 插件：从网关收到消息后转发给主网关。
- Web UI：负责新建网关、端口分配、按网关配置频道、改成员显示名、管理共享记忆。
- 首次绑定身份初始化：用户可回复“我是张三”“我叫小王”“叫我李经理”，系统会同步网关显示名。
- 共享记忆：独立的长期共享记录，按需检索，不混入个人聊天上下文。

## 共享记忆

共享记忆适合保存：

- 多人共同确认的信息
- 组织或团队决定
- 预约、日程、截止日期、项目节点
- 健康、照护、客户、工作、财务等长期有用信息
- 成就、大事件、里程碑
- 稳定偏好、禁忌、习惯和长期约束

Web UI 支持搜索、重要度过滤、新增、编辑和删除。Hermes 只在相关问题中像使用搜索结果一样检索共享记忆。

## 安装概览

```bash
cd hermes-home
sudo bash scripts/install-home-master.sh
sudo nano /opt/hermes-home/config.yaml
sudo systemctl start hermes-home-master.service
```

启动 Web UI 后，在“网关”页面新建从网关，再到“频道”页面选择对应网关进行微信扫码绑定。

## 发布清理

仓库不应包含：

- 模型 API key 或 provider 凭据
- 微信 token、account ID、OpenID、cookie、扫码状态
- Hermes 会话、历史、个人记忆、用户画像、persona 私有内容
- `/opt/hermes-home/home.db`
- Web UI token、运行数据库、日志
- 服务器 IP、密码、SSH key
