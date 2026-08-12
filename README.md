# Extreme Privacy Chromium

Android privacy browser built as a downstream fork of the **full Chromium browser**, not Android WebView.

## Implemented privacy protections

- **VPN-only Chromium networking**: Chromium's Android network discovery exposes only an accessible `TRANSPORT_VPN` network. Without one, Chromium has no usable/default network.
- **Browser-process VPN binding + kill switch**: the browser process binds to the VPN network and terminates if that VPN is lost, preventing browser fallback to Wi-Fi/mobile data during transitions.
- **No Google Chrome branding or official Google API keys**.
- **Metrics/crash reporting disabled by default**.
- **Third-party cookies blocked by default**.
- **Remote search suggestions disabled by default**.
- **DNS prefetch / preconnect / page preloading disabled by default** through Chromium's network-prediction preference.
- **HTTPS-Only mode enabled by default**.
- **Safe Browsing disabled in this maximum-privacy build** to avoid its Google-service traffic. This intentionally trades away Chromium's phishing/malware URL reputation protection.
- **Widevine disabled** in the privacy build.
- **Download with… chooser** in Chromium's Android download path:
  - Private download
  - Download with another installed app
  - Copy download link
- External downloader handoff shares the URL/MIME type only; Chromium cookies, Authorization headers, referrer and user-agent are intentionally not exported by the custom chooser.

> No browser can promise mathematical anonymity. Logging into identifying accounts, VPN-provider metadata, OS/device fingerprinting and destination-site behavior can still identify or correlate a user. The goal here is to minimize browser-originated telemetry and prevent accidental non-VPN traffic.

## Repository model

Chromium's source tree and dependencies are extremely large and are normally checked out with `depot_tools` / `fetch android`, not copied into a normal GitHub repository. This repository is therefore a reproducible **downstream Chromium fork/patchset**: CI checks out upstream Chromium, applies our source-level changes directly to Chromium, then builds Chromium's real Android browser target.

The validation workflow also sparse-checks out the current upstream Chromium files touched by this project and applies the complete patcher. If Chromium changes an expected source anchor, validation fails rather than silently weakening a privacy setting.

## Build

```bash
bash ./scripts/fetch_chromium.sh
python3 ./scripts/apply_privacy_patches.py work/chromium/src
bash ./scripts/build_android.sh work/chromium/src
```

The resulting browser is built from Chromium's real `chrome_public_apk` target as an ARM64 Android APK with package id `com.extremeprivacy.browser`.

## GitHub Actions

Use **Actions → Build Extreme Privacy Chromium → Run workflow**.

Normal pushes run two inexpensive checks:

1. overlay/script syntax validation;
2. patch validation against live upstream Chromium source.

The full Chromium build is manual because it is resource-heavy. The default full-build runner labels are `self-hosted`, `linux`, `x64`, `chromium`, and the workflow refuses a host with less than 100 GB free disk.

## Important VPN design

The patch changes Chromium's Android network discovery (`NetworkChangeNotifierAutoDetect`) so only an accessible VPN network is returned. No VPN means an empty usable-network list and no valid default route from Chromium's perspective. The browser process is also explicitly bound to that VPN and killed when the bound VPN disappears.

For defense in depth, Android's **Always-on VPN + Block connections without VPN** should also be enabled on the device. This is especially important for downloads delegated to Android's DownloadManager or another installed downloader, because those components run outside Chromium's browser process.

## Security trade-off

This configuration prioritizes minimum browser-originated network disclosure. Disabling Safe Browsing removes a useful phishing/malware protection layer. A later privacy-preserving reputation/filtering system can be added without restoring Google remote lookups.

## License

Chromium is BSD-licensed. This repository contains original patch/build glue plus source-level modifications applied to Chromium. Chromium's upstream license notices remain applicable to built/source-derived files.
