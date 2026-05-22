# Hermes Home WebUI Maintenance Rules

This repository is not the upstream Hermes Web UI in its original form.
It is the Hermes Home / multi-member gateway fork used to manage one master
gateway and multiple independent slave gateways on a single server.

Any AI agent or maintainer working in this repository must preserve the
following behavior unless the project owner explicitly asks to revert it.

## Non-Negotiable UI Differences

- The Web UI is a single-admin console. Do not restore the upstream profile/user
  selector in the sidebar.
- The admin runtime must default to the master profile:
  `home-master`, displayed as `master`.
- The upstream `default` profile is an implementation artifact and must not be
  shown as a managed gateway when `home-master` exists.
- Channel settings must be edited through dynamic gateway tabs. Selecting a tab
  points the same channel UI at a different gateway/profile.
- Memory/history/persona-style pages that are member-specific should use dynamic
  gateway tabs. Shared memory remains global.
- The chat page is only for master-gateway testing and should point at
  `home-master`.
- Do not restore the upstream profile management page, profile selector, or
  profile-switch-driven UX.
- Do not restore the upstream group-chat UI. Multi-agent or meeting behavior
  belongs in skills/workflows, not in a many-speakers chat panel.

## Architecture Rules

- Do not modify the Hermes Agent core to implement home/multi-member behavior.
  Keep the home layer external so upstream Hermes can still be updated.
- The master gateway is the logical body of the system. Slave gateways are
  independent WeChat/login entrances and relay messages to the master.
- Each slave gateway owns its own Hermes profile, port, WeChat login state, and
  channel configuration.
- Creating a new gateway should allocate the next available port and start with
  empty channel credentials.
- Long-term shared memory should stay separate from personal chat context and
  only be retrieved when relevant.

## Why This File Exists

Future repair work can easily mistake this fork for upstream `hermes-web-ui` and
"fix" the custom behavior away. That is a regression. The absence of the sidebar
profile selector and the presence of gateway tabs are intentional features.

