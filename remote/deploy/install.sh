#!/bin/sh
# Deploy sleepq-remote to a server over SSH: copy the app, build its uv environment, install the unit.
# Usage: deploy/install.sh HOST UNIT_FILE [APP_DIR]
#   HOST       ssh target, e.g. me@server
#   UNIT_FILE  your copy of deploy/sleepq-remote.service.example with the placeholders filled in
#   APP_DIR    on HOST, relative to its home (default apps/sleepq-remote); must match the unit's paths
# Needs uv on HOST (in PATH or ~/.local/bin), sudo, and /etc/sleepq-remote/deploy_key (see README).
set -e
[ $# -ge 2 ] || { sed -n '2,7p' "$0"; exit 2; }
HOST="$1" UNIT="$2" APP="${3:-apps/sleepq-remote}"
if grep -v '^#' "$UNIT" | grep -qE '/home/USER|=USER$|you/sleepq-queue|sleepq-host'; then
    echo "$UNIT still has placeholders"; exit 1
fi
cd "$(dirname "$0")/.."
ssh "$HOST" "mkdir -p '$APP'"
rsync -a --delete --exclude .venv --exclude .python --exclude data --exclude __pycache__ ./ "$HOST:$APP/"
TMP="/tmp/sleepq-remote.service.$$"
scp -q "$UNIT" "$HOST:$TMP"
ssh "$HOST" "set -e
  cd '$APP'
  mkdir -p data && chmod 2775 data
  ./sync.sh
  sudo test -f /etc/sleepq-remote/deploy_key || { echo 'missing /etc/sleepq-remote/deploy_key (see README)'; exit 1; }
  sudo install -m 644 '$TMP' /etc/systemd/system/sleepq-remote.service && rm '$TMP'
  sudo systemctl daemon-reload
  sudo systemctl enable --quiet sleepq-remote.service
  sudo systemctl restart sleepq-remote.service
  sleep 3
  systemctl --no-pager --lines 5 status sleepq-remote.service | head -12
  port=\$(sed -n 's/^Environment=SLEEPQ_REMOTE_LISTEN=.*:\([0-9]*\)\$/\1/p' /etc/systemd/system/sleepq-remote.service)
  curl -fsS -o /dev/null -w \"HTTP %{http_code} from :\${port:-8378}\n\" http://127.0.0.1:\${port:-8378}/"
