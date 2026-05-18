# Hermes 家庭版说明

这个版本把 Hermes 改造成“家庭 agent”形态，但不修改 Hermes 本体，方便后续继续升级 Hermes。

## 核心设计

- `home-master` 是主网关，负责家庭数据归总、家庭日志检索、统一生成回复。
- 每个家庭成员使用一个独立从网关，例如 `wechat2`、`wechat3`。
- 每个从网关独立绑定一个微信账号，互不污染登录状态和频道配置。
- 从网关通过 `home-slave-relay` 插件把消息转发给主网关。
- Web UI 负责创建从网关、自动分配端口、切换网关配置、改显示名、管理家庭日志。

## 发布包不包含的内容

发布源码前必须去掉：

- 模型 API key 和 provider 登录态
- 微信 token、account ID、扫码状态、cookie、OpenID
- Hermes 会话、历史、个人记忆、用户画像、persona 私有内容
- `/opt/hermes-home/home.db`
- Web UI token、数据库、日志

仓库只保留源码、示例配置和安装文档。

## 安装主网关

```bash
cd hermes-home
sudo bash scripts/install-home-master.sh
sudo nano /opt/hermes-home/config.yaml
sudo systemctl start hermes-home-master.service
```

然后启动 Web UI，在“网关”页面点击“新建网关”。

## 新建网关

点击“新建网关”后：

- 自动 clone `home-master` profile。
- 自动清空频道配置和微信凭据。
- 自动分配下一个端口。
- 自动安装并启用 `home-slave-relay` 插件。
- 自动写入 `/opt/hermes-home/config.yaml`。
- 自动启动该网关。

## 微信首次绑定

新微信绑定成功后，第一次发消息会触发初始化询问。用户可以回复：

- `我是妈妈`
- `我叫张三`
- `叫我小王`

系统会自动把该从网关显示名更新为对应成员名。也可以在 Web UI 网关页面手动点击“改名”。

## 家庭日志

家庭日志是长期家庭记忆，不混入个人聊天上下文。只有在问题需要家庭历史、安排、成员关系、重要事件时才检索。

Web UI 支持：

- 搜索家庭日志
- 按重要度过滤
- 新增
- 编辑
- 删除

AI 自动保存时会按多维度判断，例如多人提及、家庭决定、成就、大事件、健康、日程、长期偏好等。
