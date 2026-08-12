#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/darkironman-collab/Chromium}"
RUNNER_TOKEN="${RUNNER_TOKEN:-${1:-}}"
RUNNER_DIR="${RUNNER_DIR:-$HOME/actions-runner-chromium}"
RUNNER_NAME="${RUNNER_NAME:-chromium-x64-$(hostname)}"
RUNNER_LABELS="${RUNNER_LABELS:-chromium}"

if [[ -z "$RUNNER_TOKEN" ]]; then
  echo "ERROR: Provide a GitHub self-hosted runner registration token:" >&2
  echo "  RUNNER_TOKEN=... bash scripts/register_github_runner.sh" >&2
  exit 2
fi

if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
  echo "ERROR: This Chromium builder runner must be x86-64 Linux." >&2
  exit 3
fi

mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

if [[ ! -x ./config.sh ]]; then
  VERSION=$(python3 - <<'PY'
import json, urllib.request
with urllib.request.urlopen('https://api.github.com/repos/actions/runner/releases/latest') as r:
    data=json.load(r)
print(data['tag_name'].lstrip('v'))
PY
)
  ARCHIVE="actions-runner-linux-x64-${VERSION}.tar.gz"
  curl -fL --retry 3 -o "$ARCHIVE" \
    "https://github.com/actions/runner/releases/download/v${VERSION}/${ARCHIVE}"
  tar xzf "$ARCHIVE"
  rm -f "$ARCHIVE"
fi

./config.sh \
  --unattended \
  --replace \
  --url "$REPO_URL" \
  --token "$RUNNER_TOKEN" \
  --name "$RUNNER_NAME" \
  --labels "$RUNNER_LABELS" \
  --work "_work"

sudo ./svc.sh install "$(whoami)"
sudo ./svc.sh start
sudo ./svc.sh status

echo "Self-hosted Chromium builder registered for $REPO_URL"
