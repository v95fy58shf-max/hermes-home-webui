# Hermes Multi-Member Gateway

This directory contains the external multi-member layer around Hermes Agent. It keeps Hermes updateable while adding independent WeChat gateways, a master gateway, and long-term shared memory.

The same setup can be used for a household, team, studio, or small organization.

## Architecture

- `home-master` is the main profile. It owns aggregation, shared-memory retrieval, and response generation.
- Slave profiles such as `wechat2`, `wechat3`, etc. each bind one WeChat account independently.
- Each slave runs the `home-slave-relay` plugin. Incoming messages are forwarded to the local master gateway at `127.0.0.1:18080`.
- Web UI creates and starts slave gateways, allocates ports, clears copied channel credentials, and registers the slave in `/opt/hermes-home/config.yaml`.
- Shared memory is stored in `/opt/hermes-home/home.db`. The table is still named `family_logs` for compatibility.

## Install

```bash
cd hermes-home
sudo bash scripts/install-home-master.sh
sudo nano /opt/hermes-home/config.yaml
sudo systemctl start hermes-home-master.service
```

Then start Hermes Web UI. On the Gateway page, create slave gateways. Each new gateway uses the next available port and starts with empty channel settings.

## Runtime State Not Published

Do not commit:

- model API keys or provider credentials
- WeChat token, account ID, QR login state, cookies, or OpenIDs
- `/root/.hermes` profiles, sessions, memories, and credentials
- `/opt/hermes-home/home.db`
- Web UI auth token and Web UI runtime database
