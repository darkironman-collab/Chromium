#!/usr/bin/env bash
set -euo pipefail

MIN_DISK_GB="${MIN_DISK_GB:-150}"
MIN_RAM_GB="${MIN_RAM_GB:-16}"

if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
  echo "ERROR: Chromium Android builder must be x86-64 Linux." >&2
  echo "Detected: $(uname -s) $(uname -m)" >&2
  exit 2
fi

FREE_GB=$(df -Pk . | awk 'NR==2 {print int($4/1024/1024)}')
RAM_GB=$(awk '/MemTotal/ {print int($2/1024/1024)}' /proc/meminfo)
CPU_COUNT=$(nproc)

echo "Builder preflight"
echo "  CPU: ${CPU_COUNT} x86-64 cores"
echo "  RAM: ${RAM_GB} GB"
echo "  Free disk: ${FREE_GB} GB"

if (( FREE_GB < MIN_DISK_GB )); then
  echo "ERROR: Need at least ${MIN_DISK_GB} GB free disk for a practical Chromium Android checkout/build." >&2
  exit 3
fi

if (( RAM_GB < MIN_RAM_GB )); then
  echo "WARNING: Less than ${MIN_RAM_GB} GB RAM. Build may be very slow or fail under memory pressure." >&2
fi

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl git python3 python3-pip unzip zip xz-utils rsync lsb-release

# Chromium's own build/install-build-deps.sh installs the complete compiler/build package set
# after the source tree is fetched. Keep this bootstrap deliberately minimal.

git config --global core.autocrlf false

echo "Builder host is ready for the Extreme Privacy Chromium workflow."
