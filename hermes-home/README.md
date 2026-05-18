# Hermes Home

Hermes Home is a thin household layer around Hermes Agent. It keeps the Hermes upstream package updateable while adding multi-member WeChat gateways, a home master gateway, and long-term family logs.

## Architecture

- `home-master` is the main Hermes profile. It owns family aggregation, long-term family logs, and response generation.
- Slave profiles such as `wechat2`, `wechat3`, etc. each bind one WeChat account independently.
- Each slave runs the `home-slave-relay` plugin. Incoming messages are forwarded to the local master gateway at `127.0.0.1:18080`.
- Web UI creates and starts slave gateways, allocates ports, clears copied channel credentials, and registers the slave in `/opt/hermes-home/config.yaml`.
- Family logs are stored in `/opt/hermes-home/home.db`. They are retrieved only when relevant and are not mixed into ordinary personal chat context.

## What Is Not Published

Do not commit runtime state:

- model API keys or provider credentials
- WeChat token, account ID, QR login state, cookies, or OpenIDs
- `/root/.hermes` profiles, sessions, memories, and credentials
- `/opt/hermes-home/home.db`
- Web UI auth token and Web UI runtime database

This repository includes only source code and examples.

## Files

- `master_gateway.py`: local home master HTTP gateway.
- `config.example.yaml`: sanitized example config.
- `plugins/home_slave_relay`: Hermes plugin installed into each slave profile.
- `skills/family-logs/SKILL.md`: skill telling Hermes how to use and save family logs.
- `systemd/hermes-home-master.service`: systemd service template.
- `scripts/install-home-master.sh`: simple installer for the master gateway.

## Install

```bash
cd hermes-home
sudo bash scripts/install-home-master.sh
sudo nano /opt/hermes-home/config.yaml
sudo systemctl start hermes-home-master.service
```

Then start Hermes Web UI. On the Gateway page, click "新建网关" to create slave gateways. Each new gateway uses the next available port and starts with empty channel settings.

## First WeChat Binding

When a newly bound WeChat account sends its first message, the master gateway asks the member to introduce themselves. Replies like these set the gateway display name:

- `我是妈妈`
- `我叫张三`
- `叫我小王`

The display name is saved in `/opt/hermes-home/config.yaml` and shown in Web UI.

## Family Logs

Family logs are durable household facts. Save candidates include:

- multi-person decisions
- appointments, deadlines, travel, school or work events
- health and care facts
- achievements and milestones
- stable household preferences or constraints

Family logs can be searched, filtered by importance, edited, and deleted in Web UI.
