// Copyright 2026
// Use of this source code is governed by a BSD-style license.
package org.chromium.chrome.browser.privacy;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.os.Process;
import android.util.Log;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Strict VPN kill-switch for the browser process.
 *
 * The browser process is explicitly bound to an accessible VPN Network. Android guarantees that
 * sockets and DNS created through a process binding stop working if that Network disconnects.
 * We additionally terminate the browser process on loss of the bound VPN so Chromium cannot fall
 * back to an underlying Wi-Fi/cellular default network during a network transition.
 */
public final class ExtremeVpnGuard {
    private static final String TAG = "ExtremeVpnGuard";
    private static final AtomicBoolean sInstalled = new AtomicBoolean(false);
    private static final AtomicReference<Network> sBoundVpn = new AtomicReference<>();

    private ExtremeVpnGuard() {}

    /** Enforces VPN-only networking. The browser exits immediately if no usable VPN exists. */
    public static void enforceOrExit(Context context) {
        if (!sInstalled.compareAndSet(false, true)) return;

        final Context appContext = context.getApplicationContext();
        final ConnectivityManager connectivityManager =
                (ConnectivityManager) appContext.getSystemService(Context.CONNECTIVITY_SERVICE);
        if (connectivityManager == null) {
            terminate("ConnectivityManager unavailable");
            return;
        }

        final Network vpn = findUsableVpn(connectivityManager);
        if (vpn == null || !connectivityManager.bindProcessToNetwork(vpn)) {
            terminate("VPN required");
            return;
        }
        sBoundVpn.set(vpn);

        final NetworkRequest request =
                new NetworkRequest.Builder()
                        .addTransportType(NetworkCapabilities.TRANSPORT_VPN)
                        .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                        .build();

        connectivityManager.registerNetworkCallback(
                request,
                new ConnectivityManager.NetworkCallback() {
                    @Override
                    public void onLost(Network network) {
                        final Network bound = sBoundVpn.get();
                        if (bound != null && bound.equals(network)) {
                            terminate("Bound VPN disconnected");
                        }
                    }

                    @Override
                    public void onCapabilitiesChanged(
                            Network network, NetworkCapabilities capabilities) {
                        final Network bound = sBoundVpn.get();
                        if (bound == null || !bound.equals(network)) return;
                        if (!capabilities.hasTransport(NetworkCapabilities.TRANSPORT_VPN)
                                || !capabilities.hasCapability(
                                        NetworkCapabilities.NET_CAPABILITY_INTERNET)) {
                            terminate("VPN lost required capabilities");
                        }
                    }
                });
    }

    private static Network findUsableVpn(ConnectivityManager connectivityManager) {
        for (Network network : connectivityManager.getAllNetworks()) {
            final NetworkCapabilities capabilities =
                    connectivityManager.getNetworkCapabilities(network);
            if (capabilities == null) continue;
            if (!capabilities.hasTransport(NetworkCapabilities.TRANSPORT_VPN)) continue;
            if (!capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)) continue;
            return network;
        }
        return null;
    }

    private static void terminate(String reason) {
        Log.e(TAG, reason + "; refusing non-VPN networking");
        Process.killProcess(Process.myPid());
        System.exit(0);
    }
}
