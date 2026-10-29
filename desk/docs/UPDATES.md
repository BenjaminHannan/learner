# Updating Emma, Jacob and anyone else who has the app

Current copies check `desk/dist/latest.json` on GitHub (main) at launch and every 5 minutes. Version 1.2.0 checked every 6 hours; use Settings > Updates > **Check for updates** to check immediately on an older copy. When the feed's `version` is newer than the app's own version, a bar at the top says "Premonition x.y.z is ready" with **Update now**. Settings > Updates also has a switch for the automatic check.

Update now downloads the zip named in latest.json, checks its sha256, unpacks it beside the app, quits, swaps the app (Mac: the old one is kept in `~/Library/Application Support/Premonition/previous-version`; the new one is signed the same way `install-mac.sh` does so macOS keeps the permission switches), and opens it again. Chats, memory and settings are kept. The app only updates when the person presses the button.

## To publish an update

1. Bump `version` in `desk/package.json` and `desk/package-lock.json` (x.y.z; the app updates only when the number goes up).
2. Build the zips: the Mac zip on a Mac (`build-mac.sh`, so it has `deskhelper` and the speech files), the Windows zip with `build-win.sh`. Put the real zips in `desk/dist/` (they are Git LFS files).
3. Verify each ZIP’s package version and CRC with the build validation, then commit the package metadata before or with the zips. Keep their real contents in the working tree: the manifest command checks each present zip against the Git blob or LFS pointer at the current commit and requires the local package version to match that commit. It refuses uncommitted, mismatched or pointer-only files, and requires at least one zip.
4. `cd desk && node scripts/release-manifest.js "One plain sentence about what changed."` writes `dist/latest.json` with each zip's SHA-256 and a URL pinned to that artifact commit.
5. Commit `latest.json` separately and merge both commits to main, with the LFS objects available on GitHub. Current builds check within 5 minutes, or at once after Check for updates. Installing still requires clicking Update now.

Copies installed before this feature existed (Emma's and Jacob's first build) have no button: they need one last manual install (`dist/install-mac.sh` on a Mac, the Windows zip on Windows). After that, updates come from the button.
