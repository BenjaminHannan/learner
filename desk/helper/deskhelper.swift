// deskhelper: screen-control CLI for Premonition Desk (macOS 13+, Apple Silicon).
// Build: swiftc -O deskhelper.swift -o deskhelper
// Prints JSON on stdout. Errors: {"error": "..."} with exit code 1.
import AppKit
import ApplicationServices
import AVFoundation
import CoreGraphics
import Foundation

// MARK: - Output

func emit(_ obj: Any, code: Int32 = 0) -> Never {
    var opts: JSONSerialization.WritingOptions = [.sortedKeys]
    opts.insert(.withoutEscapingSlashes)
    if let data = try? JSONSerialization.data(withJSONObject: obj, options: opts),
       let s = String(data: data, encoding: .utf8) {
        print(s)
    } else {
        print("{\"error\":\"could not encode output\"}")
        exit(1)
    }
    fflush(stdout)
    exit(code)
}

func fail(_ msg: String) -> Never {
    emit(["error": msg], code: 1)
}

// MARK: - AX helpers

func axAttr(_ el: AXUIElement, _ name: String) -> CFTypeRef? {
    var v: CFTypeRef?
    let r = AXUIElementCopyAttributeValue(el, name as CFString, &v)
    return r == .success ? v : nil
}

func axString(_ el: AXUIElement, _ name: String) -> String? {
    guard let v = axAttr(el, name) else { return nil }
    if let s = v as? String { return s }
    if let n = v as? NSNumber { return n.stringValue }
    return nil
}

func axChildren(_ el: AXUIElement) -> [AXUIElement] {
    guard let v = axAttr(el, "AXChildren") else { return [] }
    return (v as? [AXUIElement]) ?? []
}

func axElements(_ el: AXUIElement, _ name: String) -> [AXUIElement] {
    guard let v = axAttr(el, name) else { return [] }
    return (v as? [AXUIElement]) ?? []
}

func axElement(_ el: AXUIElement, _ name: String) -> AXUIElement? {
    guard let v = axAttr(el, name), CFGetTypeID(v) == AXUIElementGetTypeID() else { return nil }
    return (v as! AXUIElement)
}

func axActions(_ el: AXUIElement) -> [String] {
    var names: CFArray?
    guard AXUIElementCopyActionNames(el, &names) == .success, let a = names as? [String] else { return [] }
    return a
}

func axFrame(_ el: AXUIElement) -> CGRect? {
    guard let pv = axAttr(el, "AXPosition"), CFGetTypeID(pv) == AXValueGetTypeID(),
          let sv = axAttr(el, "AXSize"), CFGetTypeID(sv) == AXValueGetTypeID() else { return nil }
    var p = CGPoint.zero
    var s = CGSize.zero
    guard AXValueGetValue(pv as! AXValue, .cgPoint, &p),
          AXValueGetValue(sv as! AXValue, .cgSize, &s) else { return nil }
    return CGRect(origin: p, size: s)
}

func trim80(_ s: String) -> String {
    let t = s.replacingOccurrences(of: "\n", with: " ")
        .trimmingCharacters(in: .whitespacesAndNewlines)
    return t.count > 80 ? String(t.prefix(80)) : t
}

func axLabel(_ el: AXUIElement) -> String {
    for name in ["AXTitle", "AXDescription", "AXValue", "AXPlaceholderValue", "AXHelp"] {
        if let s = axString(el, name) {
            let t = trim80(s)
            if !t.isEmpty { return t }
        }
    }
    return ""
}

func screenUnion() -> CGRect {
    var ids = [CGDirectDisplayID](repeating: 0, count: 16)
    var n: UInt32 = 0
    CGGetActiveDisplayList(16, &ids, &n)
    var r = CGRect.null
    for i in 0..<Int(n) { r = r.union(CGDisplayBounds(ids[i])) }
    return r.isNull ? CGDisplayBounds(CGMainDisplayID()) : r
}

// MARK: - look

let actionableRoles: Set<String> = [
    "AXButton", "AXTextField", "AXTextArea", "AXCheckBox", "AXRadioButton", "AXPopUpButton",
    "AXMenuItem", "AXMenuBarItem", "AXLink", "AXCell", "AXTab", "AXSlider", "AXComboBox", "AXSearchField",
]
let textRoles: Set<String> = ["AXTextField", "AXTextArea", "AXComboBox", "AXSearchField"]
// Roles whose children only repeat the label, so we do not descend into them.
let leafRoles: Set<String> = [
    "AXButton", "AXCheckBox", "AXRadioButton", "AXPopUpButton", "AXMenuItem", "AXMenuBarItem",
    "AXTab", "AXSlider", "AXTextField", "AXTextArea", "AXComboBox", "AXSearchField",
]
let pressActions: Set<String> = ["AXPress", "AXConfirm", "AXShowMenu"]

struct Found {
    var path: [Int]
    var role: String
    var label: String
    var value: String
    var frame: CGRect
    var isText: Bool
}

final class Walker {
    var visited = 0
    let budget = 3000
    let maxDepth = 30
    let maxText = 40
    var textCount = 0
    var found: [Found] = []
    let screen = screenUnion()

    func visible(_ f: CGRect?) -> CGRect? {
        guard let f = f, f.width > 0, f.height > 0, f.intersects(screen) else { return nil }
        return f
    }

    func walk(_ el: AXUIElement, path: [Int], depth: Int) {
        if visited >= budget || depth > maxDepth { return }
        visited += 1
        let role = axString(el, "AXRole") ?? ""
        var descend = true
        if let frame = visible(axFrame(el)) {
            if role == "AXStaticText" {
                let v = trim80(axString(el, "AXValue") ?? "")
                if !v.isEmpty && textCount < maxText {
                    textCount += 1
                    found.append(Found(path: path, role: role, label: v, value: "", frame: frame, isText: true))
                }
            } else {
                let label = axLabel(el)
                var keep = false
                if actionableRoles.contains(role) {
                    keep = role != "AXCell" || !label.isEmpty
                } else if !label.isEmpty {
                    keep = !pressActions.isDisjoint(with: axActions(el))
                }
                if keep {
                    var value = ""
                    if textRoles.contains(role) { value = trim80(axString(el, "AXValue") ?? "") }
                    found.append(Found(path: path, role: role, label: label, value: value, frame: frame, isText: false))
                    if leafRoles.contains(role) || (role == "AXLink" && !label.isEmpty) { descend = false }
                }
            }
        }
        if !descend { return }
        for (i, c) in axChildren(el).enumerated() {
            if visited >= budget { break }
            walk(c, path: path + [i], depth: depth + 1)
        }
    }
}

// Path root codes: -1 = menu bar, -2 = focused window (when not in AXWindows), >= 0 = index in AXWindows.
func resolveRoot(_ app: AXUIElement, _ code: Int) -> AXUIElement? {
    switch code {
    case -1: return axElement(app, "AXMenuBar")
    case -2: return axElement(app, "AXFocusedWindow")
    default:
        let w = axElements(app, "AXWindows")
        return code < w.count ? w[code] : nil
    }
}

func resolvePath(_ app: AXUIElement, _ path: [Int]) -> AXUIElement? {
    guard let first = path.first, var cur = resolveRoot(app, first) else { return nil }
    for idx in path.dropFirst() {
        let ch = axChildren(cur)
        guard idx >= 0, idx < ch.count else { return nil }
        cur = ch[idx]
    }
    return cur
}

func findApp(_ name: String?) -> NSRunningApplication {
    if let name = name, !name.isEmpty {
        let q = name.lowercased()
        let apps = NSWorkspace.shared.runningApplications.filter { $0.localizedName != nil }
        if let a = apps.first(where: { $0.localizedName!.lowercased() == q && $0.activationPolicy == .regular }) { return a }
        if let a = apps.first(where: { $0.localizedName!.lowercased().hasPrefix(q) && $0.activationPolicy == .regular }) { return a }
        if let a = apps.first(where: { $0.localizedName!.lowercased().hasPrefix(q) }) { return a }
        fail("no running app matches '\(name)'")
    }
    guard let a = NSWorkspace.shared.frontmostApplication else { fail("no frontmost application") }
    return a
}

let cacheDir = NSString(string: "~/Library/Caches/premonition-desk").expandingTildeInPath
let cacheFile = cacheDir + "/last_look.json"

func frameArr(_ f: CGRect) -> [Int] {
    [Int(f.origin.x.rounded()), Int(f.origin.y.rounded()), Int(f.width.rounded()), Int(f.height.rounded())]
}

func cmdLook(app appName: String?, max: Int) -> Never {
    guard AXIsProcessTrusted() else { fail("accessibility permission not granted") }
    let target = findApp(appName)
    let pid = target.processIdentifier
    let axApp = AXUIElementCreateApplication(pid)
    AXUIElementSetMessagingTimeout(axApp, 1.0)

    let windows = axElements(axApp, "AXWindows")
    let focused = axElement(axApp, "AXFocusedWindow")
    var winInfo: [[String: Any]] = []
    for w in windows {
        var d: [String: Any] = ["title": trim80(axString(w, "AXTitle") ?? "")]
        if let f = axFrame(w) { d["frame"] = frameArr(f) }
        winInfo.append(d)
    }

    let walker = Walker()
    var roots: [(Int, AXUIElement)] = []
    if let f = focused {
        if let idx = windows.firstIndex(where: { CFEqual($0, f) }) { roots.append((idx, f)) } else { roots.append((-2, f)) }
    } else {
        for (i, w) in windows.enumerated() { roots.append((i, w)) }
    }
    for (code, w) in roots { walker.walk(w, path: [code], depth: 0) }

    // Menu bar: top-level items only, no submenus.
    if let mb = axElement(axApp, "AXMenuBar") {
        for (i, item) in axChildren(mb).enumerated() {
            let role = axString(item, "AXRole") ?? ""
            let label = axLabel(item)
            if let f = walker.visible(axFrame(item)), !label.isEmpty {
                walker.found.append(Found(path: [-1, i], role: role.isEmpty ? "AXMenuBarItem" : role,
                                          label: label, value: "", frame: f, isText: false))
            }
        }
    }

    // Prefer actionable elements when over the cap, then fill with static text.
    var chosen = walker.found.filter { !$0.isText }
    if chosen.count > max { chosen = Array(chosen.prefix(max)) }
    if chosen.count < max {
        chosen += walker.found.filter { $0.isText }.prefix(max - chosen.count)
    }
    chosen.sort { a, b in
        if a.frame.origin.y != b.frame.origin.y { return a.frame.origin.y < b.frame.origin.y }
        return a.frame.origin.x < b.frame.origin.x
    }

    var elements: [[String: Any]] = []
    var cache: [[String: Any]] = []
    for (i, e) in chosen.enumerated() {
        let id = i + 1
        elements.append(["id": id, "role": e.role, "title": e.label, "value": e.value, "frame": frameArr(e.frame)])
        cache.append(["id": id, "path": e.path, "role": e.role, "label": e.label, "frame": frameArr(e.frame)])
    }
    do {
        try FileManager.default.createDirectory(atPath: cacheDir, withIntermediateDirectories: true)
        let data = try JSONSerialization.data(withJSONObject: ["pid": Int(pid), "elements": cache] as [String: Any])
        try data.write(to: URL(fileURLWithPath: cacheFile))
    } catch {
        fail("could not write look cache: \(error.localizedDescription)")
    }
    emit(["app": target.localizedName ?? "", "pid": Int(pid), "windows": winInfo, "elements": elements] as [String: Any])
}

// MARK: - Mouse / keyboard

func postMouse(_ type: CGEventType, _ p: CGPoint, button: CGMouseButton, clickState: Int64 = 1) {
    guard let ev = CGEvent(mouseEventSource: nil, mouseType: type, mouseCursorPosition: p, mouseButton: button) else { return }
    ev.setIntegerValueField(.mouseEventClickState, value: clickState)
    ev.post(tap: .cghidEventTap)
}

func doClick(_ p: CGPoint, right: Bool, double: Bool) {
    let button: CGMouseButton = right ? .right : .left
    let down: CGEventType = right ? .rightMouseDown : .leftMouseDown
    let up: CGEventType = right ? .rightMouseUp : .leftMouseUp
    postMouse(.mouseMoved, p, button: button, clickState: 0)
    usleep(30_000)
    postMouse(down, p, button: button, clickState: 1)
    postMouse(up, p, button: button, clickState: 1)
    if double {
        usleep(40_000)
        postMouse(down, p, button: button, clickState: 2)
        postMouse(up, p, button: button, clickState: 2)
    }
}

func postKey(_ code: CGKeyCode, flags: CGEventFlags = []) {
    for isDown in [true, false] {
        guard let ev = CGEvent(keyboardEventSource: nil, virtualKey: code, keyDown: isDown) else { continue }
        ev.flags = flags
        ev.post(tap: .cghidEventTap)
    }
}

func typeChunk(_ units: [UniChar]) {
    for isDown in [true, false] {
        guard let ev = CGEvent(keyboardEventSource: nil, virtualKey: 0, keyDown: isDown) else { continue }
        var u = units
        ev.keyboardSetUnicodeString(stringLength: u.count, unicodeString: &u)
        ev.post(tap: .cghidEventTap)
    }
}

func typeText(_ text: String) {
    let lines = text.replacingOccurrences(of: "\r\n", with: "\n").split(separator: "\n", omittingEmptySubsequences: false)
    for (li, line) in lines.enumerated() {
        let units = Array(String(line).utf16)
        var i = 0
        while i < units.count {
            var end = min(i + 20, units.count)
            // Do not split a surrogate pair across chunks.
            if end < units.count, UTF16.isLeadSurrogate(units[end - 1]) { end += 1 }
            typeChunk(Array(units[i..<end]))
            usleep(8_000)
            i = end
        }
        if li < lines.count - 1 {
            postKey(36)
            usleep(8_000)
        }
    }
}

let keyCodes: [String: CGKeyCode] = [
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12,
    "w": 13, "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23,
    "=": 24, "9": 25, "7": 26, "-": 27, "8": 28, "0": 29, "]": 30, "o": 31, "u": 32, "[": 33, "i": 34,
    "p": 35, "l": 37, "j": 38, "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43, "/": 44, "n": 45, "m": 46,
    ".": 47, "`": 50,
    "return": 36, "enter": 36, "tab": 48, "space": 49, "delete": 51, "backspace": 51, "esc": 53, "escape": 53,
    "forwarddelete": 117, "home": 115, "end": 119, "pageup": 116, "pagedown": 121,
    "left": 123, "right": 124, "down": 125, "up": 126,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97, "f7": 98, "f8": 100,
    "f9": 101, "f10": 109, "f11": 103, "f12": 111,
    "minus": 27, "equals": 24, "comma": 43, "period": 47, "slash": 44, "semicolon": 41, "quote": 39,
    "backslash": 42, "leftbracket": 33, "rightbracket": 30, "grave": 50,
]

func parseCombo(_ combo: String) -> (CGKeyCode, CGEventFlags)? {
    var parts = combo.split(separator: "+", omittingEmptySubsequences: true).map { String($0).lowercased() }
    if combo.hasSuffix("++") || combo == "+" { parts.append("plus") }
    var flags: CGEventFlags = []
    var keyName: String?
    for p in parts {
        switch p {
        case "cmd", "command": flags.insert(.maskCommand)
        case "shift": flags.insert(.maskShift)
        case "alt", "opt", "option": flags.insert(.maskAlternate)
        case "ctrl", "control": flags.insert(.maskControl)
        case "fn": flags.insert(.maskSecondaryFn)
        default: keyName = p
        }
    }
    guard let k = keyName else { return nil }
    if k == "plus" { flags.insert(.maskShift); return (24, flags) }
    guard let code = keyCodes[k] else { return nil }
    return (code, flags)
}

// MARK: - press

func cmdPress(id: Int) -> Never {
    guard AXIsProcessTrusted() else { fail("accessibility permission not granted") }
    guard let data = FileManager.default.contents(atPath: cacheFile),
          let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let pid = obj["pid"] as? Int,
          let list = obj["elements"] as? [[String: Any]] else { fail("no saved look; run look first") }
    guard let entry = list.first(where: { ($0["id"] as? Int) == id }),
          let path = entry["path"] as? [Int],
          let role = entry["role"] as? String,
          let fr = entry["frame"] as? [Int], fr.count == 4 else { fail("no element with id \(id) in the last look") }
    let center = CGPoint(x: Double(fr[0]) + Double(fr[2]) / 2, y: Double(fr[1]) + Double(fr[3]) / 2)

    func clickFallback(_ why: String) -> Never {
        doClick(center, right: false, double: false)
        emit(["ok": true, "id": id, "method": "click", "note": why] as [String: Any])
    }

    let axApp = AXUIElementCreateApplication(pid_t(pid))
    AXUIElementSetMessagingTimeout(axApp, 1.0)
    guard let el = resolvePath(axApp, path), (axString(el, "AXRole") ?? "") == role else {
        clickFallback("element not found by path")
    }
    if textRoles.contains(role) {
        if AXUIElementSetAttributeValue(el, "AXFocused" as CFString, kCFBooleanTrue) == .success {
            emit(["ok": true, "id": id, "method": "focus"] as [String: Any])
        }
        clickFallback("focus failed")
    }
    for action in ["AXPress", "AXConfirm"] {
        if AXUIElementPerformAction(el, action as CFString) == .success {
            emit(["ok": true, "id": id, "method": "ax"] as [String: Any])
        }
    }
    clickFallback("press failed")
}

// MARK: - open-app

func looksLikeBundleId(_ s: String) -> Bool {
    s.contains(".") && !s.contains(" ") && !s.contains("/") && !s.lowercased().hasSuffix(".app")
}

func findAppURL(_ name: String) -> URL? {
    if looksLikeBundleId(name), let u = NSWorkspace.shared.urlForApplication(withBundleIdentifier: name) { return u }
    let want = (name.lowercased().hasSuffix(".app") ? String(name.dropLast(4)) : name).lowercased() + ".app"
    let home = NSString(string: "~/Applications").expandingTildeInPath
    let dirs = ["/Applications", "/System/Applications", "/System/Applications/Utilities",
                "/Applications/Utilities", home, "/System/Library/CoreServices"]
    for d in dirs {
        if let items = try? FileManager.default.contentsOfDirectory(atPath: d),
           let hit = items.first(where: { $0.lowercased() == want }) {
            return URL(fileURLWithPath: d + "/" + hit)
        }
    }
    return nil
}

func cmdOpenApp(_ name: String) -> Never {
    let q = name.lowercased()
    let running = NSWorkspace.shared.runningApplications.first {
        $0.bundleIdentifier?.lowercased() == q || $0.localizedName?.lowercased() == q
    }
    if let r = running {
        r.activate(options: [.activateIgnoringOtherApps])
        emit(["opened": r.localizedName ?? name, "pid": Int(r.processIdentifier)] as [String: Any])
    }
    guard let url = findAppURL(name) else { fail("app not found: \(name)") }
    let sem = DispatchSemaphore(value: 0)
    var launched: NSRunningApplication?
    var launchError: Error?
    let cfg = NSWorkspace.OpenConfiguration()
    cfg.activates = true
    NSWorkspace.shared.openApplication(at: url, configuration: cfg) { app, err in
        launched = app
        launchError = err
        sem.signal()
    }
    let deadline = Date().addingTimeInterval(20)
    while sem.wait(timeout: .now() + 0.05) == .timedOut {
        RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.01))
        if Date() > deadline { fail("timed out launching \(name)") }
    }
    if let e = launchError { fail("could not open \(name): \(e.localizedDescription)") }
    guard let app = launched else { fail("could not open \(name)") }
    emit(["opened": app.localizedName ?? name, "pid": Int(app.processIdentifier)] as [String: Any])
}

// MARK: - screenshot

typealias DisplayImageFn = @convention(c) (UInt32) -> Unmanaged<CGImage>?

func grabDisplay() -> CGImage? {
    // Looked up at runtime so newer SDKs that hide CGDisplayCreateImage still compile.
    if let sym = dlsym(UnsafeMutableRawPointer(bitPattern: -2), "CGDisplayCreateImage") {
        let fn = unsafeBitCast(sym, to: DisplayImageFn.self)
        if let img = fn(CGMainDisplayID())?.takeRetainedValue() { return img }
    }
    let tmp = NSTemporaryDirectory() + "deskhelper-\(getpid()).jpg"
    let p = Process()
    p.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
    p.arguments = ["-x", "-t", "jpg", tmp]
    do { try p.run() } catch { return nil }
    p.waitUntilExit()
    defer { try? FileManager.default.removeItem(atPath: tmp) }
    guard p.terminationStatus == 0, let ns = NSImage(contentsOfFile: tmp) else { return nil }
    return ns.cgImage(forProposedRect: nil, context: nil, hints: nil)
}

func cmdScreenshot(path rawPath: String, max: Int) -> Never {
    guard CGPreflightScreenCaptureAccess() else { fail("screen recording permission not granted") }
    guard let src = grabDisplay() else { fail("could not capture the screen") }
    let path = NSString(string: rawPath).expandingTildeInPath
    let pw = src.width, ph = src.height
    let longest = Swift.max(pw, ph)
    let ratio = longest > max ? Double(max) / Double(longest) : 1.0
    let w = Swift.max(1, Int((Double(pw) * ratio).rounded()))
    let h = Swift.max(1, Int((Double(ph) * ratio).rounded()))
    guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                              space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { fail("could not create bitmap") }
    ctx.interpolationQuality = .high
    ctx.draw(src, in: CGRect(x: 0, y: 0, width: w, height: h))
    guard let scaled = ctx.makeImage(),
          let jpeg = NSBitmapImageRep(cgImage: scaled).representation(using: .jpeg, properties: [.compressionFactor: 0.7])
    else { fail("could not encode JPEG") }
    do {
        let dir = (path as NSString).deletingLastPathComponent
        if !dir.isEmpty { try FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true) }
        try jpeg.write(to: URL(fileURLWithPath: path))
    } catch {
        fail("could not write \(path): \(error.localizedDescription)")
    }
    let pointsWide = CGDisplayBounds(CGMainDisplayID()).width
    let scale = pointsWide > 0 ? Double(pointsWide) / Double(w) : 1.0
    emit(["path": path, "width": w, "height": h, "scale": (scale * 10000).rounded() / 10000] as [String: Any])
}

// MARK: - main

func intFlag(_ args: inout [String], _ name: String, default d: Int) -> Int {
    guard let i = args.firstIndex(of: name) else { return d }
    guard i + 1 < args.count, let v = Int(args[i + 1]), v > 0 else { fail("\(name) needs a positive number") }
    args.removeSubrange(i...(i + 1))
    return v
}

func stringFlag(_ args: inout [String], _ name: String) -> String? {
    guard let i = args.firstIndex(of: name) else { return nil }
    guard i + 1 < args.count else { fail("\(name) needs a value") }
    let v = args[i + 1]
    args.removeSubrange(i...(i + 1))
    return v
}

func boolFlag(_ args: inout [String], _ name: String) -> Bool {
    guard let i = args.firstIndex(of: name) else { return false }
    args.remove(at: i)
    return true
}

// MARK: - call (speech to speech; long-running, JSON lines on stdout, commands as JSON lines on stdin)
// out: {"ready"} {"partial"} {"final"} {"level"} {"speaking"} {"bargein"} {"note"} {"error"}. in: {"say"} {"stop"} {"voice"} {"mute"} {"quit"}.
let outLock = NSLock()
func out(_ obj: [String: Any]) {
    outLock.lock(); defer { outLock.unlock() }
    var opts: JSONSerialization.WritingOptions = [.sortedKeys]
    opts.insert(.withoutEscapingSlashes)
    if let d = try? JSONSerialization.data(withJSONObject: obj, options: opts) {
        FileHandle.standardOutput.write(d + Data([10]))
    }
}

// dictate = true is `deskhelper dictate`: same listening path, but plain input (no voice processing, so other audio is not ducked), no
// speech, no barge-in. Commands: {"stop"} flushes the words heard so far as a final and exits; {"quit"} / EOF exits.
//
// Speech to text is NOT done here: the app runs a local LFM3-Audio server (stt/lfm_stt.py, passed as `--stt URL`). This process only
// captures the mic, converts it to 16 kHz mono Int16, finds utterance boundaries by energy (speech starts above a gate, ends after
// ~600 ms of quiet), and POSTs the audio-so-far every ~1 s (partial) and at the end (final). No Apple speech recognition is used.
final class CallSession: NSObject, AVSpeechSynthesizerDelegate {
    var dictate = false
    var sttURL: URL!
    let engine = AVAudioEngine()
    let synth = AVSpeechSynthesizer()
    let sttQueue = DispatchQueue(label: "deskhelper.stt")   // all HTTP; the audio thread never waits on it
    let lock = NSLock()               // guards samples, inSpeech, voiced, gen, floorGen, muted, level, lastVoice, partialInFlight (audio thread)
    var samples: [Int16] = []         // 16 kHz mono: a 0.3 s lead-in while quiet, the whole utterance while speaking
    var inSpeech = false
    var voiced = 0                    // samples heard above the gate in this utterance
    var gen = 0                       // bumped at every endpoint / mute; stale partials are dropped
    var floorGen = 0                  // finals from before the last mute are dropped
    var partialInFlight = false
    var muted = false
    var restartingEngine = false      // the config-change handler is mid-restart
    var level: Float = 0
    var lastVoice = Date.distantPast  // last time the mic RMS was above the gate
    var lastPartialAt = Date.distantPast
    var pending = ""                  // newest partial text (main thread)
    var utts = Set<AVSpeechUtterance>()
    var speaking = false
    var bargeSent = false
    var voice: AVSpeechSynthesisVoice?
    var lastLevel: Double = 0
    var monoFmt: AVAudioFormat?
    var converter: AVAudioConverter?
    let outFmt = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 16000, channels: 1, interleaved: true)!
    var timer: Timer?
    var sttFails = 0                  // consecutive failed requests (sttQueue)
    var sttFirst = true               // the first request may wait for the model to load (sttQueue)
    let gate: Float = 0.012
    let silenceEnd = 0.6              // seconds of quiet that end an utterance
    let maxUtterance = 16000 * 25     // samples; longer is cut here

    func begin() {
        AVCaptureDevice.requestAccess(for: .audio) { micOK in
            guard micOK else { out(["error": "mic-denied"]); exit(1) }
            DispatchQueue.main.async { self.setup() }
        }
    }

    func setup() {
        if !dictate {
            voice = bestVoice(); synth.delegate = self
            // voice processing = echo cancellation + noise suppression, so Glim's own voice does not come back as "the user speaking"
            do { try engine.inputNode.setVoiceProcessingEnabled(true) } catch { out(["note": "no-echo-cancel"]) }
            if #available(macOS 14.0, *) {
                var d = AVAudioVoiceProcessingOtherAudioDuckingConfiguration()
                d.enableAdvancedDucking = false; d.duckingLevel = .min
                engine.inputNode.voiceProcessingOtherAudioDuckingConfiguration = d
            }
        }
        do { try startEngine() } catch { out(["error": "audio-failed: \(error.localizedDescription)"]); exit(1) }
        NotificationCenter.default.addObserver(forName: .AVAudioEngineConfigurationChange, object: engine, queue: .main) { [weak self] _ in
            // headphones plugged in, default device changed: rebuild the tap and carry on
            guard let s = self, !s.restartingEngine else { return }
            s.restartingEngine = true; defer { s.restartingEngine = false }
            s.engine.inputNode.removeTap(onBus: 0)
            do { try s.startEngine() } catch { out(["error": "audio-failed: \(error.localizedDescription)"]); exit(1) }
        }
        timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in self?.tick() }
        out(["ready": true])
    }

    func startEngine() throws {
        let input = engine.inputNode
        let fmt = input.outputFormat(forBus: 0)
        guard fmt.sampleRate > 0 else { throw NSError(domain: "call", code: 1, userInfo: [NSLocalizedDescriptionKey: "no microphone input"]) }
        let mono = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: fmt.sampleRate, channels: 1, interleaved: false)
        monoFmt = mono
        converter = mono.flatMap { AVAudioConverter(from: $0, to: outFmt) }
        guard converter != nil else { throw NSError(domain: "call", code: 2, userInfo: [NSLocalizedDescriptionKey: "cannot convert the microphone format"]) }
        input.installTap(onBus: 0, bufferSize: 1024, format: fmt) { [weak self] buf, _ in self?.onBuffer(buf) }
        engine.prepare()
        try engine.start()
    }

    // mono Float32 at the mic rate -> 16 kHz mono Int16 (audio thread)
    func toPCM16(_ b: AVAudioPCMBuffer) -> [Int16] {
        guard let conv = converter else { return [] }
        let cap = AVAudioFrameCount(Double(b.frameLength) * 16000.0 / b.format.sampleRate) + 64
        guard let o = AVAudioPCMBuffer(pcmFormat: outFmt, frameCapacity: cap) else { return [] }
        var fed = false
        var err: NSError?
        conv.convert(to: o, error: &err) { _, st in
            if fed { st.pointee = .noDataNow; return nil }
            fed = true; st.pointee = .haveData; return b
        }
        guard err == nil, let d = o.int16ChannelData else { return [] }
        return Array(UnsafeBufferPointer(start: d[0], count: Int(o.frameLength)))
    }

    // audio thread: measure, convert, append. Never waits on the network.
    func onBuffer(_ buf: AVAudioPCMBuffer) {
        let n = Int(buf.frameLength)
        guard n > 0, let ch = buf.floatChannelData else { return }
        var sum: Float = 0
        let p = ch[0]
        for i in 0..<n { sum += p[i] * p[i] }
        let rms = (sum / Float(n)).squareRoot()
        // voice processing can hand back several channels; take the first
        var b = buf
        if buf.format.channelCount > 1 || buf.format.isInterleaved, let mf = monoFmt, let m = AVAudioPCMBuffer(pcmFormat: mf, frameCapacity: buf.frameLength) {
            m.frameLength = buf.frameLength
            if let md = m.floatChannelData { memcpy(md[0], p, n * MemoryLayout<Float>.size) }
            b = m
        }
        let pcm = toPCM16(b)
        lock.lock(); defer { lock.unlock() }
        if muted { return }
        level = max(level, rms)
        if rms > gate {
            lastVoice = Date()
            inSpeech = true
            voiced += pcm.count
        }
        samples.append(contentsOf: pcm)
        if !inSpeech && samples.count > 4800 { samples.removeFirst(samples.count - 4800) } // 0.3 s lead-in so the first word is not clipped
    }

    func isMuted() -> Bool { lock.lock(); defer { lock.unlock() }; return muted }

    func tick() {
        let now = Date()
        lock.lock(); let lv = level; level = 0; let ago = now.timeIntervalSince(lastVoice); let m = muted; let sp = inSpeech; let n = samples.count; let v = voiced; lock.unlock()
        let l = m ? 0 : (min(1.0, Double(lv) * 10) * 100).rounded() / 100
        if l > 0 || lastLevel > 0 { out(["level": l]) }
        lastLevel = l
        if m || !sp { return }
        if ago > silenceEnd || n > maxUtterance { endpoint(); return }
        // talking over Glim: stop it from the sound alone (0.3 s of voice), not after a transcription comes back
        if speaking && !bargeSent && v >= 4800 { bargeSent = true; out(["bargein": true]) }
        if now.timeIntervalSince(lastPartialAt) >= 1.0 && v >= 4800 { requestPartial(now) }
    }

    // the utterance is over: transcribe all of it and emit the final
    func endpoint() {
        lock.lock()
        let s = samples, v = voiced
        samples = []; inSpeech = false; voiced = 0; gen += 1
        let g = gen
        lock.unlock()
        pending = ""; bargeSent = false
        if v < 3200 { return } // under 0.2 s above the gate: a click or a cough
        sttQueue.async {
            let t = self.transcribe(s, final: true)
            DispatchQueue.main.async {
                self.lock.lock(); let keep = g > self.floorGen && !self.muted; self.lock.unlock()
                if keep, let t = t, !t.isEmpty { out(["final": t]) }
            }
        }
    }

    // utterance so far -> partial text. One at a time; dropped if the utterance ended or was muted meanwhile.
    func requestPartial(_ now: Date) {
        lock.lock()
        if partialInFlight { lock.unlock(); return }
        partialInFlight = true
        let s = samples, g = gen
        lock.unlock()
        lastPartialAt = now
        sttQueue.async {
            let t = self.transcribe(s)
            DispatchQueue.main.async {
                self.lock.lock(); self.partialInFlight = false; let ok = g == self.gen && self.inSpeech && !self.muted; self.lock.unlock()
                guard ok, let t = t, !t.isEmpty, t != self.pending else { return }
                self.pending = t
                out(["partial": t])
                if self.speaking && !self.bargeSent { self.bargeSent = true; out(["bargein": true]) }
            }
        }
    }

    // POST 16 kHz mono Int16 to the local server (sttQueue only). nil on failure; 3 failed finals in a row end the call
    // (a slow or failed partial does not count).
    func transcribe(_ s: [Int16], final: Bool = false) -> String? {
        var req = URLRequest(url: sttURL.appendingPathComponent("transcribe"))
        req.httpMethod = "POST"
        req.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = sttFirst ? 180 : 30 // the first one loads the model
        let body = s.withUnsafeBufferPointer { Data(buffer: $0) } // Apple Silicon is little-endian
        let sem = DispatchSemaphore(value: 0)
        var text: String?, why = "no answer"
        URLSession.shared.uploadTask(with: req, from: body) { data, resp, err in
            defer { sem.signal() }
            if let err = err { why = err.localizedDescription; return }
            let j = data.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
            if let t = j?["text"] as? String { text = t.trimmingCharacters(in: .whitespacesAndNewlines) } else { why = (j?["error"] as? String) ?? "bad reply" }
        }.resume()
        sem.wait()
        if text != nil { sttFails = 0; sttFirst = false; return text }
        if !final { return nil }
        sttFails += 1
        if sttFails >= 3 { out(["error": "stt-failed: \(why)"]); exit(1) }
        return nil
    }

    func bestVoice() -> AVSpeechSynthesisVoice? {
        let en = AVSpeechSynthesisVoice.speechVoices().filter { $0.language == "en-US" }
        func rank(_ v: AVSpeechSynthesisVoice) -> Int { v.quality == .premium ? 3 : v.quality == .enhanced ? 2 : 1 }
        if let best = en.max(by: { rank($0) < rank($1) }), rank(best) > 1 { return best }
        return AVSpeechSynthesisVoice(language: "en-US")
    }

    func say(_ s: String) {
        let t = s.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !t.isEmpty else { return }
        let u = AVSpeechUtterance(string: t)
        u.voice = voice; u.preUtteranceDelay = 0; u.postUtteranceDelay = 0
        utts.insert(u); synth.speak(u)
    }

    func stopSpeaking() {
        synth.stopSpeaking(at: .immediate)
        utts.removeAll()
        if speaking { speaking = false; out(["speaking": false]) }
    }

    func done(_ u: AVSpeechUtterance) {
        utts.remove(u)
        if utts.isEmpty && speaking { speaking = false; out(["speaking": false]) }
    }
    func speechSynthesizer(_ s: AVSpeechSynthesizer, didStart u: AVSpeechUtterance) {
        if !speaking { speaking = true; bargeSent = false; out(["speaking": true]) }
    }
    func speechSynthesizer(_ s: AVSpeechSynthesizer, didFinish u: AVSpeechUtterance) { done(u) }
    func speechSynthesizer(_ s: AVSpeechSynthesizer, didCancel u: AVSpeechUtterance) { done(u) }

    func handle(_ line: String) {
        guard let d = line.data(using: .utf8), let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { return }
        if dictate {
            if j["stop"] as? Bool == true {
                // keep what was heard: transcribe it, then exit once the final has gone out (same queue, same order)
                lock.lock(); let sp = inSpeech; lock.unlock()
                if sp { endpoint() }
                sttQueue.async { DispatchQueue.main.async { self.shutdown() } }
            } else if j["quit"] as? Bool == true { shutdown() }
            return
        }
        if let s = j["say"] as? String { say(s) }
        if j["stop"] as? Bool == true { stopSpeaking() }
        if let id = j["voice"] as? String, let v = AVSpeechSynthesisVoice(identifier: id) { voice = v }
        if let m = j["mute"] as? Bool {
            lock.lock()
            muted = m; samples = []; inSpeech = false; voiced = 0; gen += 1; floorGen = gen // drop half-heard words on mute and on unmute
            lock.unlock()
            pending = ""
        }
        if j["quit"] as? Bool == true { shutdown() }
    }

    func shutdown() -> Never {
        synth.stopSpeaking(at: .immediate)
        engine.inputNode.removeTap(onBus: 0); engine.stop()
        exit(0)
    }
}

func runCall(dictate: Bool = false, stt: String?) -> Never {
    guard let s = stt, let url = URL(string: s) else { out(["error": "stt-missing: the speech server address was not given (--stt URL)"]); exit(1) }
    let session = CallSession()
    session.dictate = dictate
    session.sttURL = url
    session.begin()
    DispatchQueue.global().async {
        while let line = readLine() { DispatchQueue.main.async { session.handle(line) } }
        DispatchQueue.main.async { session.shutdown() } // stdin closed: the app is gone
    }
    dispatchMain()
}

var args = Array(CommandLine.arguments.dropFirst())
guard !args.isEmpty else { fail("usage: deskhelper check|ask-permissions|look|press|click|type|key|scroll|open-app|screenshot|notch|call|dictate") }
let command = args.removeFirst()

switch command {
case "call":
    runCall(stt: stringFlag(&args, "--stt"))

case "dictate":
    runCall(dictate: true, stt: stringFlag(&args, "--stt"))

case "notch":
    // the camera notch of the menu-bar screen: the gap between the two menu-bar areas beside it (macOS 12+); 0 when there is none.
    // Needs no permission. Its width in points changes with the display scaling (16" M3: 250 pt at "More Space").
    if #available(macOS 12.0, *), let s = NSScreen.screens.first, let l = s.auxiliaryTopLeftArea, let r = s.auxiliaryTopRightArea {
        emit(["width": Double(r.minX - l.maxX), "height": Double(s.safeAreaInsets.top)] as [String: Any])
    }
    emit(["width": 0, "height": 0] as [String: Any])

case "check":
    emit(["accessibility": AXIsProcessTrusted(), "screenRecording": CGPreflightScreenCaptureAccess()] as [String: Any])

case "ask-permissions":
    let opts = ["AXTrustedCheckOptionPrompt": true] as CFDictionary
    let ax = AXIsProcessTrustedWithOptions(opts)
    let sr = CGRequestScreenCaptureAccess()
    emit(["accessibility": ax, "screenRecording": sr] as [String: Any])

case "look":
    let app = stringFlag(&args, "--app")
    let max = intFlag(&args, "--max", default: 150)
    cmdLook(app: app, max: max)

case "press":
    guard let s = args.first, let id = Int(s) else { fail("usage: press ID") }
    cmdPress(id: id)

case "click":
    let right = boolFlag(&args, "--right")
    let double = boolFlag(&args, "--double")
    guard args.count >= 2, let x = Double(args[0]), let y = Double(args[1]) else { fail("usage: click X Y [--double] [--right]") }
    guard AXIsProcessTrusted() else { fail("accessibility permission not granted") }
    doClick(CGPoint(x: x, y: y), right: right, double: double)
    emit(["ok": true])

case "type":
    guard !args.isEmpty else { fail("usage: type TEXT") }
    guard AXIsProcessTrusted() else { fail("accessibility permission not granted") }
    let text = args.joined(separator: " ")
    typeText(text)
    emit(["ok": true, "chars": text.count] as [String: Any])

case "key":
    guard !args.isEmpty else { fail("usage: key COMBO") }
    guard AXIsProcessTrusted() else { fail("accessibility permission not granted") }
    let combo = args.joined(separator: "")
    guard let (code, flags) = parseCombo(combo) else { fail("unknown key combo: \(combo)") }
    postKey(code, flags: flags)
    emit(["ok": true])

case "scroll":
    guard let s = args.first, let dy = Double(s) else { fail("usage: scroll DY") }
    guard AXIsProcessTrusted() else { fail("accessibility permission not granted") }
    guard let ev = CGEvent(scrollWheelEvent2Source: nil, units: .line, wheelCount: 1,
                           wheel1: Int32(dy.rounded()), wheel2: 0, wheel3: 0) else { fail("could not create scroll event") }
    ev.post(tap: .cghidEventTap)
    emit(["ok": true])

case "open-app":
    guard !args.isEmpty else { fail("usage: open-app NAME") }
    cmdOpenApp(args.joined(separator: " "))

case "screenshot":
    let max = intFlag(&args, "--max", default: 1280)
    guard let p = args.first else { fail("usage: screenshot PATH [--max 1280]") }
    cmdScreenshot(path: p, max: max)

default:
    fail("unknown command: \(command)")
}
