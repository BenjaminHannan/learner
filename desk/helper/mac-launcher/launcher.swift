// The app's front door (Nov 5, Mac "uncle" build). Built for both Intel and Apple silicon (lipo), it is the bundle's
// CFBundleExecutable. On Apple silicon it simply becomes the real app (execv of Contents/MacOS/Premonition-app, same process).
// On an Intel Mac it shows one plain message instead of macOS's vague "not supported on this Mac": Glim's brain needs Apple silicon.
import Foundation
#if arch(x86_64)
import AppKit
#endif

func appleSilicon() -> Bool {
    var v: Int32 = 0; var n = MemoryLayout<Int32>.size
    return sysctlbyname("hw.optional.arm64", &v, &n, nil, 0) == 0 && v == 1
}

let me = URL(fileURLWithPath: CommandLine.arguments[0]).resolvingSymlinksInPath()
let real = me.deletingLastPathComponent().appendingPathComponent("Premonition-app").path

// PREMONITION_FAKE_INTEL=1 (tests only, run with `arch -x86_64`) takes the Intel path on an Apple-silicon Mac
if appleSilicon() && ProcessInfo.processInfo.environment["PREMONITION_FAKE_INTEL"] != "1" {
    var args = CommandLine.arguments; args[0] = real
    let cargs = args.map { strdup($0) } + [nil]
    execv(real, cargs)
    perror("execv")   // only reached if the real app is missing
    exit(1)
}

#if arch(x86_64)
let app = NSApplication.shared
app.setActivationPolicy(.regular)
NSApp.activate(ignoringOtherApps: true)
let a = NSAlert()
a.messageText = "This Mac can't run Glim's brain"
a.informativeText = "Glim needs a Mac with Apple silicon (an M1, M2, M3, M4 or newer chip). This Mac has an Intel chip, so Glim can't run here.\n\nYou can drag Premonition from Applications to the Trash."
a.alertStyle = .warning
a.addButton(withTitle: "OK")
a.runModal()
#endif
exit(0)
