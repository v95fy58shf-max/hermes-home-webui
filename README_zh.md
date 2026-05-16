# Hermes Home WebUI

这是一个面向家庭场景魔改的 Hermes Web UI 版本，目标是把 Hermes 变成可多人使用的家庭 Agent。

核心原则：不修改 Hermes Agent 本体。Hermes 仍然可以按上游方式更新；家庭能力通过 Web UI、主网关、从网关插件和家庭日志层实现。

## 源码来源

本项目基于以下开源项目二次开发：

- Hermes Agent: https://github.com/NousResearch/hermes-agent
- Hermes Web UI: https://github.com/EKKOLearnAI/hermes-web-ui

本仓库保留 Hermes Web UI 原有管理面板能力，并在此基础上加入家庭网关、多微信绑定、家庭长期日志等功能。原项目版权、协议与贡献归原作者所有；本仓库新增的家庭版功能位于 `hermes-home/` 及相关 Web UI 改动中。

## 这个版本解决什么问题

原始 Hermes 适合单人或单网关使用。家庭场景里会遇到几个问题：

- 多个家庭成员都需要绑定微信。
- 每个微信登录态必须独立，不能互相覆盖。
- 不能直接改 Hermes 本体，否则后续不好升级。
- 家庭公共信息需要长期保存，但不能污染每个人自己的聊天上下文。
- Web UI 原本不支持多网关动态创建、切换和按网关配置频道。

这个版本把 Hermes 拆成主从结构：

- 主网关 `home-master`：家庭 Agent 的“大脑”，负责汇总、回复、检索家庭日志。
- 从网关 `wechat2`、`wechat3` 等：每个家庭成员一个独立 Hermes profile，用于独立绑定微信。
- Relay 插件：从网关收到消息后转发给主网关，由主网关统一处理。
- Web UI：负责新建网关、端口分配、按网关配置频道、改成员显示名、管理家庭日志。

## 主要特色

### 多微信家庭网关

- 支持在 Web UI 的“网关”页点击“新建网关”。
- 每新建一个从网关，自动分配下一个端口。
- 新网关会 clone `home-master` profile，但会清空频道配置和微信凭据。
- 每个从网关可以独立扫码绑定一个微信账号。
- 从网关之间微信 token、account id、扫码状态互不影响。

### 主从架构，不改 Hermes 本体

- Hermes Agent 本体保持原样。
- 家庭逻辑放在 `/opt/hermes-home/master_gateway.py`。
- 从网关通过 `home-slave-relay` 插件把消息转给主网关。
- 后续升级 Hermes 时，不需要把家庭逻辑打进 Hermes 源码。

### 首次绑定身份初始化

新微信绑定成功后，第一次发消息会触发身份询问。

用户可以回复：

- `我是妈妈`
- `我叫张三`
- `叫我小王`

系统会自动把该微信从网关的显示名同步到 Web UI。也可以在“网关”页手动点击“改名”。

### 多网关频道配置

原 Web UI 的频道页面只面向单网关。这个版本增加了动态网关选项卡：

- 页面上方显示当前已运行网关。
- 点击不同网关后，频道配置读写对应 profile。
- 微信、企业微信、QQ、飞书等频道配置都按网关隔离。
- 新建网关的频道设置默认为空，避免复制主网关或其他成员的登录态。

### 家庭日志

家庭日志是独立的长期家庭记忆，不直接混入个人上下文。

适合保存：

- 多人共同提及或确认的信息
- 家庭决定
- 预约、日程、旅行、学校、工作事件
- 健康和照护信息
- 成就、里程碑、大事件
- 长期偏好、禁忌和家庭约束

Web UI 支持：

- 搜索家庭日志
- 按重要度筛选
- 新增
- 编辑
- 删除

Hermes 在需要时会像使用联网搜索结果一样检索家庭日志，而不是把它一直塞进每个人的聊天上下文。

## 目录说明

```text
hermes-home/
  master_gateway.py                 # 家庭主网关
  config.example.yaml               # 脱敏示例配置
  plugins/home_slave_relay/          # 从网关转发插件
  skills/family-logs/SKILL.md        # 告诉 Hermes 如何使用家庭日志
  systemd/hermes-home-master.service # systemd 服务模板
  scripts/install-home-master.sh     # 主网关安装脚本

docs/HERMES_HOME_ZH.md               # 家庭版详细说明
docs/RELEASE_SANITIZE.md             # 发布前脱敏检查清单
```

## 安装概览

先安装并配置 Hermes Agent 与本 Web UI，然后安装家庭主网关：

```bash
cd hermes-home
sudo bash scripts/install-home-master.sh
sudo nano /opt/hermes-home/config.yaml
sudo systemctl start hermes-home-master.service
```

启动 Web UI 后，在“网关”页面点击“新建网关”，再到“频道”页面选择对应网关进行微信扫码绑定。

## 发布包不包含什么

本仓库发布前已清理运行态数据。不要把下面内容提交到仓库：

- 模型 API key
- provider 登录态
- 微信 token、account ID、扫码状态、cookie、OpenID
- Hermes 会话历史
- 个人记忆、用户画像、persona 私有内容
- `/opt/hermes-home/home.db`
- Web UI token、数据库和日志
- 服务器 IP、密码、SSH key

## 当前状态

这是家庭版初版，已验证：

- 多网关创建
- 端口自动递增
- 多微信扫码绑定
- 按网关配置频道
- 首次绑定身份询问和显示名同步
- 家庭日志保存、检索、编辑、删除
- Hermes 本体保持可更新

## License

本仓库继承上游 Hermes Web UI 的许可约束。原始项目及依赖项目的版权归各自作者所有。
