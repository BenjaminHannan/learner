# Updating Emma, Jacob and anyone else who has the app

Every copy checks `desk/dist/latest.json` on GitHub (main) at launch and every 5 minutes. When its `version` is newer than the app's own version, a bar at the top says "Premonition x.y.z is ready" with **Update now**. Settings > Updates has a **Check for updates** button and a switch for the automatic check.

Update now downloads the zip named in latest.json, checks its sha256, unpacks it beside the app, quits, swaps the app (Mac: the old one is kept in `~/Library/Application Support/Premonition/previous-version`; the new one is signed the same way `install-mac.sh` does so macOS keeps the permission switches), and opens it again. Chats, memory and settings are kept. The app only updates when the person presses the button.

## To publish an update

1. Bump `version` in `desk/package.json` (x.y.z; the app updates only when the number goes up).
2. Build the zips: the Mac zip on a Mac (`build-mac.sh`, so it has `deskhelper` and the speech files), the Windows zip with `build-win.sh`. Put them in `desk/dist/` (they are Git LFS files).
3. `cd desk && node scripts/release-manifest.js "One plain sentence about what changed."` writes `dist/latest.json` with the sha256 of each zip.
4. Commit the zips and `latest.json` and merge to main. Everyone sees the bar within 5 minutes, or at once after Check for updates.

Copies installed before this feature existed (Emma's and Jacob's first build) have no button: they need one last manual install (`dist/install-mac.sh` on a Mac, the Windows zip on Windows). After that, updates come from the button.
