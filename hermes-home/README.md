# Hermes Home

Hermes Home is a thin household layer around Hermes Agent. Hermes remains updateable and replaceable; the family logic lives outside Hermes in this directory.

## Runtime Shape

- `home-master` is the main household gateway.
- Slave profiles such as `wechat2` and `wechat3` each bind one WeChat account independently.
- Each slave runs `home-slave-relay` and forwards incoming messages to the master gateway.
- Web UI creates slave gateways, allocates ports, clears copied channel credentials, and registers slaves in `/opt/hermes-home/config.yaml`.

## Phase 1

Phase 1 built the family chat layer:

- multi-WeChat independent profiles
- master/slave gateway relay
- Web UI gateway creation
- per-gateway channel configuration
- first binding identity onboarding
- gateway display-name sync
- independent family logs
- family-log skill for Hermes

## Phase 2

Phase 2 starts the family state system:

- `core/event_bus.py`: canonical event entry point for WeChat messages and future device/NAS events.
- `core/state_engine.py`: turns events into structured long-term states.
- `core/privacy.py`: defines privacy scopes for event, memory, and state.
- `core/decay_worker.py`: applies TTL, importance, confidence, decay, and archival.
- `core/memory_router.py`: chooses relevant state/log retrieval and filters by privacy scope.
- `core/relationship_graph.py`: tracks trust, tension, and support between members.
- `analyzers/`: low-token expert analyzers for emotion, sleep, family relation, and elderly health.

## Privacy

Hermes Home should transfer state, not private raw content.

Example:

- Raw child message: "I hate mom"
- Raw scope: `private`
- Shared output: "child family relationship tension is elevated"
- Shared scope: `summary_only`

## Install

```bash
cd hermes-home
sudo bash scripts/install-home-master.sh
sudo nano /opt/hermes-home/config.yaml
sudo systemctl start hermes-home-master.service
```

## Do Not Publish Runtime State

Do not commit:

- model API keys or provider credentials
- WeChat token, account ID, QR login state, cookies, or OpenIDs
- `/root/.hermes` profiles, sessions, memories, and credentials
- `/opt/hermes-home/home.db`
- Web UI auth token and Web UI runtime database
