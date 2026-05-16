# Release Sanitize Checklist

Before publishing this repository or a source archive, verify that no runtime state is included.

## Must Not Be Included

- Model API keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, provider pool keys, custom provider keys.
- WeChat state: `WEIXIN_TOKEN`, `WEIXIN_ACCOUNT_ID`, QR login state, cookies, OpenIDs.
- Hermes runtime state: profiles, sessions, memories, credentials, `state.db`, `gateway.pid`.
- Hermes Home runtime state: `/opt/hermes-home/config.yaml`, `/opt/hermes-home/home.db`, logs, pid files.
- Web UI runtime state: auth token, local DB, logs, uploads.
- Server login credentials, IP addresses, SSH keys, passwords.

## Safe To Include

- Source code.
- Sanitized examples such as `config.example.yaml`.
- Unit tests with placeholder values like `sk-test`, `old-token`, or `acct-1`.
- Documentation that names environment variables without assigning real values.

## Suggested Scan

```bash
rg -n --hidden --glob '!node_modules/**' --glob '!dist/**' --glob '!.git/**' "API_KEY|WEIXIN_|openid|home.db|auth token"
```

Review matches manually. Field names and test placeholders are acceptable; real values are not.
