#!/usr/bin/env bash
set -euo pipefail

SRC="${1:-}"
if [[ -z "$SRC" || ! -d "$SRC/chrome" ]]; then
  echo "usage: $0 /path/to/chromium/src" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPOT_TOOLS_DIR="${DEPOT_TOOLS_DIR:-$ROOT/work/depot_tools}"
export PATH="$DEPOT_TOOLS_DIR:$PATH"

cd "$SRC"

# Chromium documents install-build-deps.sh as the supported Linux dependency setup.
if [[ "${SKIP_BUILD_DEPS:-0}" != "1" ]]; then
  sudo build/install-build-deps.sh --no-prompt
fi

gclient runhooks

mkdir -p out/ExtremePrivacy
cat > out/ExtremePrivacy/args.gn <<'EOF'
target_os = "android"
target_cpu = "arm64"
is_debug = false
is_component_build = false
symbol_level = 0
blink_symbol_level = 0
v8_symbol_level = 0
use_remoteexec = false
treat_warnings_as_errors = false
android_static_analysis = "off"

# Privacy / de-Googling build settings.
is_chrome_branded = false
use_official_google_api_keys = false
enable_widevine = false
safe_browsing_mode = 0

# Separate install identity from stock Chromium/Chrome.
chrome_public_manifest_package = "com.extremeprivacy.browser"
EOF

gn gen out/ExtremePrivacy
autoninja -C out/ExtremePrivacy chrome_public_apk

APK="$(find out/ExtremePrivacy -type f -name 'ChromePublic.apk' -print -quit)"
if [[ -z "$APK" ]]; then
  APK="$(find out/ExtremePrivacy -type f -name '*.apk' -path '*chrome_public*' -print -quit)"
fi
if [[ -z "$APK" ]]; then
  echo "Build completed but APK could not be located." >&2
  exit 3
fi

mkdir -p "$ROOT/dist"
cp "$APK" "$ROOT/dist/ExtremePrivacyBrowser-arm64.apk"
sha256sum "$ROOT/dist/ExtremePrivacyBrowser-arm64.apk" | tee "$ROOT/dist/ExtremePrivacyBrowser-arm64.apk.sha256"
echo "APK: $ROOT/dist/ExtremePrivacyBrowser-arm64.apk"
