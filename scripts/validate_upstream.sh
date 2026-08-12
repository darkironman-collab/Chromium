#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROMIUM_REF="${CHROMIUM_REF:-main}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

SRC="$TMP/src"
git clone --filter=blob:none --no-checkout --depth=1 \
  https://chromium.googlesource.com/chromium/src.git "$SRC"

cd "$SRC"
git sparse-checkout init --no-cone
cat > .git/info/sparse-checkout <<'EOF'
/net/android/java/src/org/chromium/net/NetworkChangeNotifierAutoDetect.java
/chrome/android/java/src/org/chromium/chrome/browser/ChromeApplicationImpl.java
/chrome/android/java/src/org/chromium/chrome/browser/download/DownloadController.java
/chrome/android/chrome_java_sources.gni
/chrome/android/java/AndroidManifest.xml
/chrome/browser/browser_process_impl.cc
/components/content_settings/core/browser/cookie_settings.cc
/chrome/browser/profiles/profile.cc
/chrome/browser/preloading/preloading_prefs.cc
/chrome/browser/ui/browser_ui_prefs.cc
EOF

if [[ "$CHROMIUM_REF" == "main" ]]; then
  git checkout main
else
  git fetch origin "$CHROMIUM_REF" --depth=1
  git checkout --detach FETCH_HEAD
fi

python3 "$ROOT/scripts/apply_privacy_patches.py" "$SRC"
git diff --check
git diff --stat

echo "Privacy patches apply cleanly to Chromium ref: $CHROMIUM_REF"
