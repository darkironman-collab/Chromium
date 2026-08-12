#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${WORK_DIR:-$ROOT/work/chromium}"
DEPOT_TOOLS_DIR="${DEPOT_TOOLS_DIR:-$ROOT/work/depot_tools}"
CHROMIUM_REF="${CHROMIUM_REF:-main}"

mkdir -p "$ROOT/work"

if [[ ! -d "$DEPOT_TOOLS_DIR/.git" ]]; then
  git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git "$DEPOT_TOOLS_DIR"
fi
export PATH="$DEPOT_TOOLS_DIR:$PATH"

if [[ ! -f "$WORK_DIR/.gclient" ]]; then
  mkdir -p "$WORK_DIR"
  pushd "$WORK_DIR" >/dev/null
  fetch --nohooks --no-history android
  popd >/dev/null
fi

pushd "$WORK_DIR/src" >/dev/null
git fetch origin "$CHROMIUM_REF" --depth=1
if [[ "$CHROMIUM_REF" == "main" ]]; then
  git checkout -B extreme-upstream FETCH_HEAD
else
  git checkout -B extreme-upstream "$CHROMIUM_REF" || git checkout -B extreme-upstream FETCH_HEAD
fi

gclient sync -D --force --reset --no-history
popd >/dev/null

printf 'Chromium checkout ready at %s\n' "$WORK_DIR/src"
