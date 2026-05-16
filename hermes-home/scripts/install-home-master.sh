#!/usr/bin/env bash
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="${HERMES_HOME_MASTER_DIR:-/opt/hermes-home}"
SERVICE_FILE="/etc/systemd/system/hermes-home-master.service"

install -d "$INSTALL_DIR"
install -m 0755 "$SRC_DIR/master_gateway.py" "$INSTALL_DIR/master_gateway.py"
cp -R "$SRC_DIR/core" "$INSTALL_DIR/core"
cp -R "$SRC_DIR/analyzers" "$INSTALL_DIR/analyzers"

if [ ! -f "$INSTALL_DIR/config.yaml" ]; then
  install -m 0644 "$SRC_DIR/config.example.yaml" "$INSTALL_DIR/config.yaml"
fi

if command -v systemctl >/dev/null 2>&1; then
  install -m 0644 "$SRC_DIR/systemd/hermes-home-master.service" "$SERVICE_FILE"
  systemctl daemon-reload
  systemctl enable hermes-home-master.service
  echo "Installed hermes-home-master.service. Start it with: systemctl start hermes-home-master.service"
else
  echo "systemctl not found. Run manually: python3 $INSTALL_DIR/master_gateway.py"
fi
