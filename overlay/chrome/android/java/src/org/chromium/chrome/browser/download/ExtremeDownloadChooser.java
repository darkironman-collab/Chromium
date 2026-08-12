// Copyright 2026
// Use of this source code is governed by a BSD-style license.
package org.chromium.chrome.browser.download;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.text.TextUtils;
import android.widget.Toast;

import org.chromium.base.ApplicationStatus;

/** Presents an explicit chooser before a request is handed to Android DownloadManager. */
final class ExtremeDownloadChooser {
    private ExtremeDownloadChooser() {}

    static void show(DownloadInfo info, Runnable builtInDownload) {
        Activity activity = ApplicationStatus.getLastTrackedFocusedActivity();
        if (activity == null || activity.isFinishing()) {
            // There is no safe UI surface. Keep the request inside Chromium rather than silently
            // exposing the URL to another application.
            builtInDownload.run();
            return;
        }

        final String url = info.getUrl().getSpec();
        final String mimeType = info.getMimeType();
        final CharSequence[] choices = {
            "Private download",
            "Download with another app",
            "Copy download link"
        };

        new AlertDialog.Builder(activity)
                .setTitle("Download with…")
                .setItems(
                        choices,
                        (dialog, which) -> {
                            switch (which) {
                                case 0:
                                    builtInDownload.run();
                                    break;
                                case 1:
                                    launchExternalDownloader(activity, url, mimeType);
                                    break;
                                case 2:
                                    copyLink(activity, url);
                                    break;
                                default:
                                    break;
                            }
                        })
                .setNegativeButton(android.R.string.cancel, null)
                .show();
    }

    private static void launchExternalDownloader(Activity activity, String url, String mimeType) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW);
            Uri uri = Uri.parse(url);
            if (!TextUtils.isEmpty(mimeType)) {
                intent.setDataAndType(uri, mimeType);
            } else {
                intent.setData(uri);
            }
            intent.addCategory(Intent.CATEGORY_BROWSABLE);

            // Intentionally do NOT copy Chromium cookies, Authorization headers, referrer, or user
            // agent into the Intent. The selected external app receives only the download URL/MIME.
            activity.startActivity(Intent.createChooser(intent, "Download with…"));
        } catch (ActivityNotFoundException | SecurityException exception) {
            Toast.makeText(activity, "No compatible downloader found", Toast.LENGTH_SHORT).show();
        }
    }

    private static void copyLink(Context context, String url) {
        ClipboardManager clipboard =
                (ClipboardManager) context.getSystemService(Context.CLIPBOARD_SERVICE);
        if (clipboard == null) return;
        clipboard.setPrimaryClip(ClipData.newPlainText("Download link", url));
        Toast.makeText(context, "Download link copied", Toast.LENGTH_SHORT).show();
    }
}
