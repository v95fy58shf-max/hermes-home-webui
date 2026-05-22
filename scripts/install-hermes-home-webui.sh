#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${HERMES_HOME_WEBUI_REPO:-https://github.com/v95fy58shf-max/hermes-home-webui.git}"
BRANCH="${HERMES_HOME_WEBUI_BRANCH:-main}"
SOURCE_DIR="${HERMES_HOME_WEBUI_SOURCE_DIR:-/opt/hermes-home-webui-src}"
INSTALL_DIR="${HERMES_HOME_WEBUI_INSTALL_DIR:-/usr/lib/node_modules/hermes-web-ui}"
SERVICE_FILE="${HERMES_HOME_WEBUI_SERVICE_FILE:-/etc/systemd/system/hermes-web-ui.service}"
WEBUI_HOME="${HERMES_WEB_UI_HOME:-/root/.hermes-web-ui}"
PORT="${PORT:-8648}"
BIND_HOST="${BIND_HOST:-0.0.0.0}"

log() { printf '[hermes-home-webui] %s\n' "$*"; }
warn() { printf '[hermes-home-webui] WARNING: %s\n' "$*" >&2; }
die() { printf '[hermes-home-webui] ERROR: %s\n' "$*" >&2; exit 1; }

need_root() {
  if [ "$(id -u)" -ne 0 ]; then
    die "Please run as root, for example: curl -fsSL ... | sudo bash"
  fi
}

install_packages() {
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends ca-certificates curl git tar build-essential python3
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y ca-certificates curl git tar gcc gcc-c++ make python3
  elif command -v yum >/dev/null 2>&1; then
    yum install -y ca-certificates curl git tar gcc gcc-c++ make python3
  else
    warn "No supported package manager found. Please ensure curl, git, tar, build tools, and python3 are installed."
  fi
}

install_node() {
  local major=0
  if command -v node >/dev/null 2>&1; then
    major="$(node -v | sed 's/^v//' | cut -d. -f1)"
  fi

  if [ "${major:-0}" -ge 23 ] 2>/dev/null; then
    log "Node.js $(node -v) found."
    return
  fi

  if command -v apt-get >/dev/null 2>&1; then
    log "Installing Node.js 23.x via NodeSource."
    curl -fsSL https://deb.nodesource.com/setup_23.x | bash -
    apt-get install -y nodejs
  else
    die "Node.js 23+ is required. Install Node.js first, then rerun this script."
  fi
}

fetch_source() {
  if [ -d "$SOURCE_DIR/.git" ]; then
    log "Updating source in $SOURCE_DIR."
    git -C "$SOURCE_DIR" fetch --depth 1 origin "$BRANCH"
    git -C "$SOURCE_DIR" checkout -B "$BRANCH" "origin/$BRANCH"
  else
    log "Cloning $REPO_URL#$BRANCH to $SOURCE_DIR."
    rm -rf "$SOURCE_DIR"
    git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$SOURCE_DIR"
  fi
}

build_source() {
  log "Installing build dependencies."
  npm --prefix "$SOURCE_DIR" ci
  log "Building Hermes Home WebUI."
  npm --prefix "$SOURCE_DIR" run build
}

install_runtime() {
  log "Installing runtime files to $INSTALL_DIR."
  rm -rf "$INSTALL_DIR"
  install -d "$INSTALL_DIR"
  cp -a "$SOURCE_DIR/bin" "$INSTALL_DIR/bin"
  cp -a "$SOURCE_DIR/dist" "$INSTALL_DIR/dist"
  cp -a "$SOURCE_DIR/package.json" "$INSTALL_DIR/package.json"
  cp -a "$SOURCE_DIR/package-lock.json" "$INSTALL_DIR/package-lock.json"
  cp -a "$SOURCE_DIR/AGENTS.md" "$INSTALL_DIR/AGENTS.md"
  cp -a "$SOURCE_DIR/docs" "$INSTALL_DIR/docs"
  cp -a "$SOURCE_DIR/hermes-home" "$INSTALL_DIR/hermes-home"

  log "Installing production Node dependencies."
  npm --prefix "$INSTALL_DIR" ci --omit=dev --ignore-scripts
  npm --prefix "$INSTALL_DIR" rebuild node-pty || warn "node-pty rebuild failed; terminal features may be unavailable."
}

install_home_layer() {
  log "Installing Hermes Home master layer."
  bash "$SOURCE_DIR/hermes-home/scripts/install-home-master.sh"
  if command -v systemctl >/dev/null 2>&1; then
    systemctl restart hermes-home-master.service || warn "Could not start hermes-home-master.service."
  fi
}

write_service() {
  command -v systemctl >/dev/null 2>&1 || die "systemd is required for the one-click service install."

  log "Writing $SERVICE_FILE."
  cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Hermes Home Web UI
After=network.target hermes-home-master.service
Wants=hermes-home-master.service

[Service]
Type=simple
Environment=NODE_ENV=production
Environment=PORT=$PORT
Environment=BIND_HOST=$BIND_HOST
Environment=HERMES_WEB_UI_HOME=$WEBUI_HOME
Environment=HERMES_HOME_CONFIG=/opt/hermes-home/config.yaml
Environment=HERMES_HOME_MASTER_URL=http://127.0.0.1:18080/incoming
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/node $INSTALL_DIR/dist/server/index.js
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable hermes-web-ui.service
  systemctl restart hermes-web-ui.service
}

post_check() {
  sleep 5
  systemctl is-active --quiet hermes-web-ui.service || {
    systemctl status hermes-web-ui.service --no-pager -l || true
    die "hermes-web-ui.service failed to start."
  }

  log "Hermes Home WebUI is running on port $PORT."
  log "Open: http://SERVER_IP:$PORT"
  if [ -f "$WEBUI_HOME/.token" ]; then
    log "Auth token file: $WEBUI_HOME/.token"
  fi

  if ! command -v hermes >/dev/null 2>&1; then
    warn "Hermes Agent CLI was not found in PATH. Install Hermes Agent before creating gateways."
  fi
}

main() {
  need_root
  install_packages
  install_node
  fetch_source
  build_source
  install_runtime
  install_home_layer
  write_service
  post_check
}

main "$@"
