#!/usr/bin/env python3
"""Apply Extreme Privacy source-level patches to a Chromium checkout.

Designed for current Chromium main and intentionally fails loudly if an expected
source anchor disappears, so upstream changes do not silently weaken privacy.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

MARKER = "EXTREME_PRIVACY_PATCH_V1"


def fail(msg: str) -> None:
    raise SystemExit(f"privacy patch failed: {msg}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def replace_method_body(text: str, signature_needle: str, new_body: str, label: str) -> str:
    start = text.find(signature_needle)
    if start < 0:
        fail(f"{label}: method signature not found")
    brace = text.find("{", start)
    if brace < 0:
        fail(f"{label}: opening brace not found")

    depth = 0
    end = None
    for i in range(brace, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end is None:
        fail(f"{label}: closing brace not found")
    return text[: brace + 1] + "\n" + new_body.rstrip() + "\n" + text[end:]


def patch_vpn_network_discovery(src: Path) -> None:
    path = src / "net/android/java/src/org/chromium/net/NetworkChangeNotifierAutoDetect.java"
    text = path.read_text()
    if MARKER in text:
        print("VPN network discovery already patched")
        return

    sig = "static Network[] getAllNetworksFiltered("
    sig_pos = text.find(sig)
    if sig_pos < 0:
        fail("NetworkChangeNotifierAutoDetect.getAllNetworksFiltered missing")
    sig_end = text.find("{", sig_pos)
    signature = text[sig_pos:sig_end]
    match = re.search(r"(?:ConnectivityManagerWrapper|ConnectivityManagerDelegate)\s+(\w+)", signature)
    if not match:
        fail("cannot determine ConnectivityManager parameter name")
    manager = match.group(1)

    vpn_body = f'''        // {MARKER}: expose only an accessible VPN network to Chromium.
        Network[] networks = {manager}.getAllNetworksUnfiltered();
        for (Network network : networks) {{
            if (network.equals(ignoreNetwork)) continue;
            final NetworkCapabilitiesWrapper capabilities =
                    {manager}.getNetworkCapabilities(network);
            if (capabilities == null
                    || !capabilities.hasCapability(NET_CAPABILITY_INTERNET)
                    || !capabilities.hasTransport(TRANSPORT_VPN)) {{
                continue;
            }}
            if ({manager}.vpnAccessible(network)) {{
                return new Network[] {{network}};
            }}
        }}
        // No VPN means Chromium has no usable network. Never expose Wi-Fi/cellular fallback.
        return new Network[0];'''
    text = replace_method_body(text, sig, vpn_body, "VPN network filtering")

    default_sig = "public @Nullable Network getDefaultNetwork()"
    member = (
        "mConnectivityManagerWrapper"
        if "mConnectivityManagerWrapper" in text
        else "mConnectivityManagerDelegate"
    )
    default_body = f'''        // {MARKER}: default route is valid only when the filtered VPN exists.
        final Network[] networks = getAllNetworksFiltered({member}, null);
        return networks.length == 0 ? null : networks[0];'''
    text = replace_method_body(text, default_sig, default_body, "VPN default network")
    path.write_text(text)
    print("patched Chromium Android network discovery: VPN only")


def patch_browser_process_vpn_guard(src: Path, repo_root: Path) -> None:
    source = repo_root / "overlay/chrome/android/java/src/org/chromium/chrome/browser/privacy/ExtremeVpnGuard.java"
    dest = src / "chrome/android/java/src/org/chromium/chrome/browser/privacy/ExtremeVpnGuard.java"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)

    app = src / "chrome/android/java/src/org/chromium/chrome/browser/ChromeApplicationImpl.java"
    text = app.read_text()
    if "ExtremeVpnGuard.enforceOrExit" not in text:
        import_anchor = "import org.chromium.chrome.browser.accessibility.hierarchysnapshotter.HierarchySnapshotter;"
        text = replace_once(
            text,
            import_anchor,
            import_anchor + "\nimport org.chromium.chrome.browser.privacy.ExtremeVpnGuard;",
            "ChromeApplicationImpl import",
        )
        text = replace_once(
            text,
            "    public void onCreate() {\n        super.onCreate();",
            "    public void onCreate() {\n        super.onCreate();\n\n"
            "        // EXTREME_PRIVACY_PATCH_V1: browser process must be bound to a VPN.\n"
            "        if (SplitCompatApplication.isBrowserProcess()) {\n"
            "            ExtremeVpnGuard.enforceOrExit(getApplication());\n"
            "        }",
            "ChromeApplicationImpl onCreate",
        )
        app.write_text(text)

    sources = src / "chrome/android/chrome_java_sources.gni"
    text = sources.read_text()
    entry = '  "java/src/org/chromium/chrome/browser/privacy/ExtremeVpnGuard.java",\n'
    if entry not in text:
        anchor = '  "java/src/org/chromium/chrome/browser/ChromeApplicationImpl.java",\n'
        text = replace_once(text, anchor, anchor + entry, "chrome_java_sources.gni")
        sources.write_text(text)

    manifest = src / "chrome/android/java/AndroidManifest.xml"
    text = manifest.read_text()
    permission = '<uses-permission android:name="android.permission.CHANGE_NETWORK_STATE" />'
    if permission not in text:
        anchor = '<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />'
        text = replace_once(text, anchor, anchor + "\n    " + permission, "Android manifest VPN permission")
        manifest.write_text(text)

    print("installed browser-process VPN binding/kill switch")


def patch_metrics_reporting(src: Path) -> None:
    path = src / "chrome/browser/browser_process_impl.cc"
    text = path.read_text()
    old = "registry->RegisterBooleanPref(metrics::prefs::kMetricsReportingEnabled,\n                                GoogleUpdateSettings::GetCollectStatsConsent());"
    if old in text:
        text = text.replace(
            old,
            "registry->RegisterBooleanPref(metrics::prefs::kMetricsReportingEnabled, false);  // EXTREME_PRIVACY_PATCH_V1",
            1,
        )
    else:
        pattern = re.compile(
            r"registry->RegisterBooleanPref\(metrics::prefs::kMetricsReportingEnabled,\s*"
            r"GoogleUpdateSettings::GetCollectStatsConsent\(\)\);"
        )
        text, count = pattern.subn(
            "registry->RegisterBooleanPref(metrics::prefs::kMetricsReportingEnabled, false);  // EXTREME_PRIVACY_PATCH_V1",
            text,
            count=1,
        )
        if count != 1 and MARKER not in text:
            fail("metrics reporting registration anchor missing")
    path.write_text(text)
    print("disabled metrics/crash reporting default")


def patch_third_party_cookie_default(src: Path) -> None:
    path = src / "components/content_settings/core/browser/cookie_settings.cc"
    text = path.read_text()
    needle = "static_cast<int>(CookieControlsMode::kIncognitoOnly),"
    if "EXTREME_PRIVACY_COOKIE_DEFAULT" not in text:
        if needle not in text:
            fail("third-party cookie default anchor missing")
        text = text.replace(
            needle,
            "static_cast<int>(CookieControlsMode::kBlockThirdParty),  // EXTREME_PRIVACY_COOKIE_DEFAULT",
            1,
        )
        path.write_text(text)
    print("set third-party cookies blocked by default")


def patch_search_suggestions_default(src: Path) -> None:
    path = src / "chrome/browser/profiles/profile.cc"
    text = path.read_text()
    if "EXTREME_PRIVACY_SEARCH_SUGGEST" in text:
        print("search suggestions already disabled by default")
        return
    pattern = re.compile(
        r"registry->RegisterBooleanPref\(\s*prefs::kSearchSuggestEnabled,\s*true,\s*"
        r"user_prefs::PrefRegistrySyncable::SYNCABLE_PREF\);"
    )
    replacement = (
        "registry->RegisterBooleanPref(\n"
        "      prefs::kSearchSuggestEnabled, false,  // EXTREME_PRIVACY_SEARCH_SUGGEST\n"
        "      user_prefs::PrefRegistrySyncable::SYNCABLE_PREF);"
    )
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        fail("search suggestion default anchor missing")
    path.write_text(text)
    print("disabled remote search suggestions by default")


def patch_preloading_default(src: Path) -> None:
    path = src / "chrome/browser/preloading/preloading_prefs.cc"
    text = path.read_text()
    if "EXTREME_PRIVACY_PRELOADING" in text:
        print("preloading already disabled by default")
        return
    needle = "static_cast<int>(NetworkPredictionOptions::kDefault),"
    if needle not in text:
        fail("network prediction/preloading default anchor missing")
    text = text.replace(
        needle,
        "static_cast<int>(NetworkPredictionOptions::kDisabled),  // EXTREME_PRIVACY_PRELOADING",
        1,
    )
    path.write_text(text)
    print("disabled DNS prefetch/preconnect/page preloading by default")


def patch_https_only_default(src: Path) -> None:
    path = src / "chrome/browser/ui/browser_ui_prefs.cc"
    text = path.read_text()
    if "EXTREME_PRIVACY_HTTPS_ONLY" in text:
        print("HTTPS-Only already enabled by default")
        return
    pattern = re.compile(
        r"registry->RegisterBooleanPref\(\s*prefs::kHttpsOnlyModeEnabled,\s*false,\s*"
        r"user_prefs::PrefRegistrySyncable::SYNCABLE_PREF\);"
    )
    replacement = (
        "registry->RegisterBooleanPref(\n"
        "      prefs::kHttpsOnlyModeEnabled, true,  // EXTREME_PRIVACY_HTTPS_ONLY\n"
        "      user_prefs::PrefRegistrySyncable::SYNCABLE_PREF);"
    )
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        fail("HTTPS-Only default anchor missing")
    path.write_text(text)
    print("enabled HTTPS-Only mode by default")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_privacy_patches.py /path/to/chromium/src")
    src = Path(sys.argv[1]).resolve()
    if not (src / "chrome").is_dir() or not (src / "net").is_dir():
        fail(f"not a Chromium src checkout: {src}")
    repo_root = Path(__file__).resolve().parents[1]

    patch_vpn_network_discovery(src)
    patch_browser_process_vpn_guard(src, repo_root)
    patch_metrics_reporting(src)
    patch_third_party_cookie_default(src)
    patch_search_suggestions_default(src)
    patch_preloading_default(src)
    patch_https_only_default(src)
    print("Extreme Privacy Chromium patches applied successfully")


if __name__ == "__main__":
    main()
