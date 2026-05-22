# Hermes Multi-Member WebUI

中文说明见 [README_zh.md](README_zh.md).

This is a multi-member fork/customization of Hermes Web UI. It can be used for households, teams, studios, and small organizations that need multiple independent WeChat gateway profiles without modifying the Hermes Agent upstream package.

## Canonical Repository For Repairs

The canonical source for this customized Hermes Home WebUI is:

https://github.com/v95fy58shf-max/hermes-home-webui

When repairing, redeploying, or comparing behavior, use this repository as the
maintenance baseline. Do not treat the upstream Hermes Web UI repository as the
only source of truth, because this fork intentionally removes the upstream
profile selector and adds master/slave gateway tabs.

## Source Attribution

This project is based on:

- Hermes Agent: https://github.com/NousResearch/hermes-agent
- Hermes Web UI: https://github.com/EKKOLearnAI/hermes-web-ui

Original copyrights and licenses belong to their respective authors. This repository keeps the upstream Web UI foundation and adds the gateway layer, multi-WeChat gateway management, and shared memory.

## What This Fork Adds

- Multi-member WeChat gateways, one independent Hermes profile per member.
- A `home-master` gateway that aggregates messages and owns response generation.
- Slave gateway relay plugin that forwards member messages to the master gateway.
- Web UI gateway creation with automatic port allocation.
- Per-gateway channel configuration tabs.
- First-message onboarding that asks a newly bound WeChat user who they are.
- Gateway display-name sync based on replies such as `我是张三`, `我叫小王`, or `叫我李经理`.
- Long-term shared memory stored separately from personal chat context.
- Shared-memory search, importance filtering, manual add, edit, and delete.

## Why It Exists

Hermes works well as a personal agent, but multi-member setups need stronger isolation:

- each member needs a separate WeChat login state;
- WeChat credentials must not be copied between profiles;
- shared facts should be durable but should not pollute each person's normal chat context;
- Hermes itself should stay updateable.

This fork solves that by adding an external gateway layer around Hermes rather than patching Hermes core.

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
