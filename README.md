# Hermes Home WebUI

中文说明见 [README_zh.md](README_zh.md).

Hermes Home WebUI is a household-focused fork/customization of Hermes Web UI. It turns Hermes Agent into a multi-member family agent without modifying the Hermes Agent upstream package.

## Source Attribution

This project is based on:

- Hermes Agent: https://github.com/NousResearch/hermes-agent
- Hermes Web UI: https://github.com/EKKOLearnAI/hermes-web-ui

Original copyrights and licenses belong to their respective authors. This repository keeps the upstream Web UI foundation and adds the household gateway layer, multi-WeChat gateway management, family logs, and the phase-2 family state system foundation.

## What This Fork Adds

- Multi-member WeChat gateways, one independent Hermes profile per family member.
- A `home-master` gateway that aggregates messages and owns the family agent brain.
- Slave gateway relay plugin that forwards member messages to the home master.
- Web UI gateway creation with automatic port allocation.
- Per-gateway channel configuration tabs.
- First-message onboarding that asks a newly bound WeChat user who they are.
- Gateway display-name sync based on replies such as `我是妈妈`, `我叫张三`, or `叫我小王`.
- Long-term family logs stored separately from personal chat context.
- Family log search, importance filtering, manual add, edit, and delete.
- Phase 2 family state infrastructure: Event Bus, State Engine, Privacy Scope, Memory Router, Relationship Graph, Decay Worker, and expert analyzers.

## Why It Exists

Hermes works well as a personal agent, but a household setup needs stronger isolation:

- each family member needs a separate WeChat login state;
- WeChat credentials must not be copied between profiles;
- shared family facts should be durable but should not pollute each person's normal chat context;
- private raw messages should not be forwarded as shared family memory;
- Hermes itself should stay updateable.

This fork solves that by adding a home layer around Hermes rather than patching Hermes core.

## Repository Layout

```text
hermes-home/
  master_gateway.py
  config.example.yaml
  core/
  analyzers/
  plugins/home_slave_relay/
  skills/family-logs/SKILL.md
  systemd/hermes-home-master.service
  scripts/install-home-master.sh

docs/HERMES_HOME_ZH.md
docs/RELEASE_SANITIZE.md
```

## Install Sketch

```bash
cd hermes-home
sudo bash scripts/install-home-master.sh
sudo nano /opt/hermes-home/config.yaml
sudo systemctl start hermes-home-master.service
```

Then start the Web UI, create slave gateways from the Gateway page, and bind WeChat separately for each gateway from the Channels page.

## Privacy And Release Hygiene

This repository must not include:

- model API keys;
- provider credentials;
- WeChat tokens, account IDs, OpenIDs, cookies, or QR login state;
- Hermes sessions, memories, user profiles, or persona files;
- `/opt/hermes-home/home.db`;
- Web UI auth tokens, logs, or local databases;
- server IPs, passwords, or SSH keys.

See [docs/RELEASE_SANITIZE.md](docs/RELEASE_SANITIZE.md).

## License

This fork inherits the upstream Hermes Web UI license constraints. Upstream project rights remain with their original authors.
