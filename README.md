# Extreme Privacy Chromium

Android privacy browser built as a downstream fork of the **full Chromium browser**, not Android WebView.

## Privacy goals

- **VPN-only networking**: Chromium must see and use only an accessible Android VPN transport. If the VPN disappears, Chromium is told there are no usable networks and network requests fail instead of falling back to Wi-Fi/mobile data.
- **No Google Chrome branding or official Google API keys**.
- **Metrics/crash reporting disabled by policy patching**.
- **Safe Browsing remote lookups disabled** in the privacy build to avoid Google lookup traffic.
- **Widevine disabled** in the privacy build.
- **Third-party-cookie blocking / anti-tracking defaults** are applied by the privacy patcher where supported by the checked-out Chromium revision.
- **Download with…** integration is planned in the Chromium Android download layer so users can choose the built-in downloader or another installed downloader.

> No browser can promise mathematical anonymity. Logging into identifying accounts, VPN-provider metadata, OS/device fingerprinting and destination-site behavior can still identify or correlate a user. The goal here is to minimize browser-originated telemetry and prevent accidental non-VPN traffic.

## Repository model

Chromium's source tree and dependencies are extremely large and are normally checked out with `depot_tools` / `fetch android`, not copied into a normal GitHub repository. This repository is therefore a reproducible **downstream fork/patchset**: CI checks out upstream Chromium, applies our source-level patches directly to Chromium, then builds Chromium's real Android browser target.

## Build

```bash
./scripts/fetch_chromium.sh
./scripts/apply_privacy_patches.py work/chromium/src
./scripts/build_android.sh work/chromium/src
```

The resulting browser is built from Chromium's `chrome_public_apk` target.

## GitHub Actions

Use **Actions → Build Extreme Privacy Chromium → Run workflow**.

A full Chromium Android build is resource-heavy. A large or self-hosted x86-64 Linux runner with substantial disk space is recommended. The workflow intentionally supports a self-hosted runner label.

## Important VPN design

The patch changes Chromium's Android network discovery (`NetworkChangeNotifierAutoDetect`) so only an accessible `TRANSPORT_VPN` network is returned. No VPN means an empty usable-network list and an invalid default network. Chromium already treats Android VPN networks specially; this fork makes that behavior mandatory rather than optional.

For defense in depth, Android's **Always-on VPN + Block connections without VPN** should also be enabled on the device.

## License

Chromium is BSD-licensed. This repository contains original patch/build glue plus source-level modifications applied to Chromium. Chromium's upstream license notices remain applicable to built/source-derived files.
