import Foundation
import CoreGraphics
import ApplicationServices
import Darwin
import Carbon
import ImageIO
import AppKit

// This helper owns both the watcher and all event posting. A physical event,
// expiry, broken pipe, or a disabled tap revokes under the same lock used by
// the sender, then releases only events that Glim itself put down.
// A fresh tag distinguishes this owner's events from another Glim process.
private var tag: Int64 = 0
private let lock = NSLock()
private var live = false
private var cancelled = false
private var expires: UInt64 = 0
private var ownKeys = Set<CGKeyCode>()
private var ownButtons = Set<CGMouseButton>()
private var ioFD: Int32 = STDOUT_FILENO
private var watcher: CFMachPort?
private let emitLock = NSLock()
private func ns() -> UInt64 { DispatchTime.now().uptimeNanoseconds }
private func emit(_ row: [String: Any]) {
    emitLock.lock(); defer { emitLock.unlock() }
    guard let data = try? JSONSerialization.data(withJSONObject: row, options: [.sortedKeys]),
          let line = String(data: data, encoding: .utf8) else { return }
    let bytes = Array((line + "\n").utf8)
    bytes.withUnsafeBytes { ptr in
        var sent = 0
        while sent < ptr.count {
            let n = write(ioFD, ptr.baseAddress!.advanced(by: sent), ptr.count - sent)
            if n <= 0 { break }; sent += n
        }
    }
}
private func post(_ event: CGEvent?) {
    guard let e = event else { return }
    e.setIntegerValueField(.eventSourceUserData, value: tag)
    e.post(tap: .cghidEventTap)
}
private func flags() -> CGEventFlags {
    var f: CGEventFlags = []
    if ownKeys.contains(55) || ownKeys.contains(54) { f.insert(.maskCommand) }
    if ownKeys.contains(56) || ownKeys.contains(60) { f.insert(.maskShift) }
    if ownKeys.contains(58) || ownKeys.contains(61) { f.insert(.maskAlternate) }
    if ownKeys.contains(59) || ownKeys.contains(62) { f.insert(.maskControl) }
    return f
}
private func releaseLocked() {
    for key in ownKeys { post(CGEvent(keyboardEventSource: nil, virtualKey: key, keyDown: false)) }
    ownKeys.removeAll()
    let pos = CGEvent(source: nil)?.location ?? .zero
    for button in ownButtons {
        let type: CGEventType = button == .left ? .leftMouseUp : button == .right ? .rightMouseUp : .otherMouseUp
        post(CGEvent(mouseEventSource: nil, mouseType: type, mouseCursorPosition: pos, mouseButton: button))
    }
    ownButtons.removeAll()
}
private func revoke(_ reason: String, terminal: Bool) {
    lock.lock()
    if terminal && cancelled { lock.unlock(); return }
    let time = ns(); live = false; expires = 0
    if terminal { cancelled = true }
    let released = ownKeys.count + ownButtons.count
    releaseLocked()
    let finished = ns()
    lock.unlock()
    emit(["event":"revoked", "reason":reason, "timeNs":time, "releaseDoneNs":finished, "released":released, "terminal":terminal])
}
private func current() -> Bool { live && !cancelled && ns() < expires }
private func point(_ x: Any?, _ y: Any?) -> CGPoint? {
    guard let x = x as? NSNumber, let y = y as? NSNumber else { return nil }
    let p = CGPoint(x: x.doubleValue, y: y.doubleValue)
    guard p.x.isFinite && p.y.isFinite else { return nil }
    var count: UInt32 = 0
    guard CGGetActiveDisplayList(0, nil, &count) == .success, count > 0, count < 64 else { return nil }
    var displays = [CGDirectDisplayID](repeating: 0, count: Int(count))
    guard CGGetActiveDisplayList(count, &displays, &count) == .success else { return nil }
    return displays.prefix(Int(count)).contains { CGDisplayBounds($0).contains(p) } ? p : nil
}
private func button(_ s: String) -> CGMouseButton? {
    switch s { case "left": return .left; case "right": return .right; case "middle": return .center; default: return nil }
}
private func mouseType(_ b: CGMouseButton, _ down: Bool) -> CGEventType {
    if b == .left { return down ? .leftMouseDown : .leftMouseUp }
    if b == .right { return down ? .rightMouseDown : .rightMouseUp }
    return down ? .otherMouseDown : .otherMouseUp
}
private func displayInfo(_ id: CGDirectDisplayID) -> [String:Any] {
    let b = CGDisplayBounds(id)
    return ["id":String(id), "bounds":["x":b.origin.x,"y":b.origin.y,"width":b.width,"height":b.height]]
}
private func screenshot(_ displayID: String?) -> [String:Any]? {
    guard !IsSecureEventInputEnabled(), CGPreflightScreenCaptureAccess() else { return nil }
    var count: UInt32 = 0
    guard CGGetActiveDisplayList(0, nil, &count) == .success, count > 0, count < 64 else { return nil }
    var displays = [CGDirectDisplayID](repeating:0, count:Int(count))
    guard CGGetActiveDisplayList(count, &displays, &count) == .success else { return nil }
    let ids = Array(displays.prefix(Int(count)))
    let selected = displayID.flatMap { UInt32($0) } ?? CGMainDisplayID()
    guard ids.contains(selected), let original = CGDisplayCreateImage(selected) else { return nil }
    let b = CGDisplayBounds(selected), scale = min(1, 1280 / b.width, 900 / b.height)
    let width = max(1, Int((b.width * scale).rounded())), height = max(1, Int((b.height * scale).rounded()))
    guard let context = CGContext(data:nil, width:width, height:height, bitsPerComponent:8, bytesPerRow:0,
                                  space:CGColorSpaceCreateDeviceRGB(), bitmapInfo:CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }
    context.interpolationQuality = .high
    context.draw(original, in:CGRect(x:0,y:0,width:width,height:height))
    guard let image = context.makeImage() else { return nil }
    guard let small = CGContext(data:nil,width:160,height:100,bitsPerComponent:8,bytesPerRow:640,
                                space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }
    small.interpolationQuality = .high; small.draw(image,in:CGRect(x:0,y:0,width:160,height:100))
    guard let pixels = small.data else { return nil }
    let fingerprint = Data(bytes:pixels,count:160*100*4).base64EncodedString()
    let data = NSMutableData()
    guard let encoder = CGImageDestinationCreateWithData(data, "public.png" as CFString, 1, nil) else { return nil }
    CGImageDestinationAddImage(encoder, image, nil)
    guard CGImageDestinationFinalize(encoder) else { return nil }
    let cursor = CGEvent(source:nil)?.location ?? .zero
    return ["png":(data as Data).base64EncodedString(), "fingerprint":fingerprint, "displayId":String(selected), "bounds":displayInfo(selected)["bounds"]!,
            "size":["width":width,"height":height], "displays":ids.map(displayInfo),
            "cursor":[(cursor.x-b.origin.x)/b.width, (cursor.y-b.origin.y)/b.height], "frontApp":NSWorkspace.shared.frontmostApplication?.localizedName ?? ""]
}
private func send(_ j: [String:Any]) -> String? {
    lock.lock(); defer { lock.unlock() }
    guard current() else { return "lease expired or cancelled" }
    guard !IsSecureEventInputEnabled(), let tap = watcher, CGEvent.tapIsEnabled(tap:tap) else { return "watcher or secure input unavailable" }
    switch j["kind"] as? String {
    case "mouse":
        guard let p = point(j["x"], j["y"]), let b = button(j["button"] as? String ?? "left"),
              let state = j["state"] as? String else { return "invalid mouse event" }
        let kind: CGEventType
        switch state {
        case "move": kind = ownButtons.contains(b) ? (b == .left ? .leftMouseDragged : b == .right ? .rightMouseDragged : .otherMouseDragged) : .mouseMoved
        case "down": guard !ownButtons.contains(b) else { return "button already held" }; ownButtons.insert(b); kind = mouseType(b, true)
        case "up": guard ownButtons.contains(b) else { return "button not held" }; ownButtons.remove(b); kind = mouseType(b, false)
        default: return "invalid mouse state"
        }
        guard let e = CGEvent(mouseEventSource: nil, mouseType: kind, mouseCursorPosition: p, mouseButton: b) else { return "cannot create mouse event" }
        if let count = j["count"] as? Int, count >= 1 && count <= 3 { e.setIntegerValueField(.mouseEventClickState, value: Int64(count)) }
        e.flags = flags(); post(e)
    case "key":
        guard let n = j["code"] as? Int, n >= 0, n < 128, let down = j["down"] as? Bool else { return "invalid key event" }
        let key = CGKeyCode(n)
        if down { guard !ownKeys.contains(key) else { return "key already held" }; ownKeys.insert(key) }
        else { guard ownKeys.contains(key) else { return "key not held" }; ownKeys.remove(key) }
        guard let e = CGEvent(keyboardEventSource: nil, virtualKey: key, keyDown: down) else { return "cannot create key event" }
        e.flags = flags(); post(e)
    case "character":
        guard let text = j["text"] as? String, text.count == 1, text.utf16.count <= 8,
              !text.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) else { return "invalid character" }
        guard let down = CGEvent(keyboardEventSource: nil, virtualKey: 0, keyDown: true),
              let up = CGEvent(keyboardEventSource: nil, virtualKey: 0, keyDown: false) else { return "cannot create character event" }
        let units = Array(text.utf16)
        units.withUnsafeBufferPointer { buf in down.keyboardSetUnicodeString(stringLength: buf.count, unicodeString: buf.baseAddress); up.keyboardSetUnicodeString(stringLength: buf.count, unicodeString: buf.baseAddress) }
        post(down); post(up)
    case "scroll":
        guard let n = j["dy"] as? Int, n >= -120, n <= 120 else { return "invalid scroll" }
        guard let e = CGEvent(scrollWheelEvent2Source: nil, units: .pixel, wheelCount: 1, wheel1: Int32(n), wheel2: 0, wheel3: 0) else { return "cannot create scroll event" }
        post(e)
    default: return "unknown event"
    }
    expires = ns() + 50_000_000
    return nil
}

private func runGuard(_ fd: Int32, _ preflight: Bool) {
    ioFD = fd
    if preflight {
        emit(["accessibility":AXIsProcessTrusted(), "screen":CGPreflightScreenCaptureAccess(), "input":CGPreflightListenEventAccess(), "pid":getpid()]); return
    }
    lock.lock(); live = false; cancelled = false; expires = 0; ownKeys.removeAll(); ownButtons.removeAll(); tag = Int64.random(in:1...Int64.max); lock.unlock()
    guard AXIsProcessTrusted(), CGPreflightListenEventAccess(), CGPreflightScreenCaptureAccess(), !IsSecureEventInputEnabled() else { emit(["error":"accessibility, screen recording or input monitoring unavailable, or secure input active"]); return }
    let kinds: [CGEventType] = [.keyDown,.keyUp,.flagsChanged,.mouseMoved,.leftMouseDown,.leftMouseUp,.rightMouseDown,.rightMouseUp,.otherMouseDown,.otherMouseUp,.leftMouseDragged,.rightMouseDragged,.otherMouseDragged,.scrollWheel]
    var mask: CGEventMask = 0
    for kind in kinds { mask |= CGEventMask(1) << CGEventMask(kind.rawValue) }
    let callback: CGEventTapCallBack = { _, kind, event, _ in
        if kind == .tapDisabledByTimeout || kind == .tapDisabledByUserInput { revoke("watcher disabled", terminal:true) }
        else if event.getIntegerValueField(.eventSourceUserData) != tag { revoke("user input", terminal:true) }
        return Unmanaged.passUnretained(event)
    }
    guard let tap = CGEvent.tapCreate(tap:.cgSessionEventTap, place:.headInsertEventTap, options:.listenOnly, eventsOfInterest:mask, callback:callback, userInfo:nil),
          let source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0) else { emit(["error":"input watcher unavailable"]); return }
    lock.lock(); watcher = tap; lock.unlock()
    CFRunLoopAddSource(CFRunLoopGetCurrent(), source, .commonModes); CGEvent.tapEnable(tap:tap, enable:true)
    let timer = DispatchSource.makeTimerSource(queue:DispatchQueue.global())
    timer.schedule(deadline:.now(), repeating:.milliseconds(2))
    timer.setEventHandler {
        if IsSecureEventInputEnabled() || !CGEvent.tapIsEnabled(tap:tap) { revoke("watcher or secure input unavailable", terminal:true); return }
        lock.lock(); let expired = live && ns() >= expires; lock.unlock()
        if expired { revoke("lease expired", terminal:false) }
    }; timer.resume()
    defer { timer.cancel(); lock.lock(); watcher = nil; lock.unlock(); CGEvent.tapEnable(tap:tap, enable:false); CFRunLoopRemoveSource(CFRunLoopGetCurrent(), source, .commonModes); CFMachPortInvalidate(tap) }
    let loop = CFRunLoopGetCurrent()
    DispatchQueue.global().async {
        var pending = [UInt8]()
        while true {
            var byte: UInt8 = 0
            let n = read(fd, &byte, 1)
            if n <= 0 { break }
            if byte != 10 { pending.append(byte); if pending.count > 16384 { revoke("invalid command", terminal:true); break }; continue }
            guard let line = String(bytes:pending, encoding:.utf8) else { revoke("invalid command", terminal:true); break }
            pending.removeAll(keepingCapacity:true)
            guard line.utf8.count <= 16384, let data = line.data(using:.utf8),
                  let j = (try? JSONSerialization.jsonObject(with:data)) as? [String:Any],
                  let id = j["id"] as? String else { revoke("invalid command", terminal:true); continue }
            switch j["op"] as? String {
            case "look":
                lock.lock(); let allowed = !cancelled && !live; lock.unlock()
                if allowed, let image = screenshot(j["displayId"] as? String) { var row = image; row["id"] = id; row["ok"] = true; emit(row) }
                else { emit(["id":id,"ok":false,"error":"screen unavailable or control stopped"]) }
            case "idle":
                let anyEvent = CGEventType(rawValue:0xFFFFFFFF)!
                emit(["id":id,"ok":true,"seconds":CGEventSource.secondsSinceLastEventType(.combinedSessionState, eventType:anyEvent)])
            case "grant":
                let unsafe = IsSecureEventInputEnabled() || !CGEvent.tapIsEnabled(tap:tap)
                lock.lock()
                let ok = !cancelled && !live && !unsafe
                if ok { live = true; expires = ns() + 50_000_000 }
                lock.unlock()
                if unsafe { revoke("watcher or secure input unavailable", terminal:true) }
                emit(["id":id,"ok":ok])
            case "send":
                let error = send(j)
                if error == "watcher or secure input unavailable" { revoke(error!, terminal:true) }
                emit(["id":id,"ok":error == nil,"error":error ?? ""])
            case "end": revoke("step ended", terminal:false); emit(["id":id,"ok":true])
            default: revoke("bad operation", terminal:true); emit(["id":id,"ok":false])
            }
        }
        revoke("parent pipe closed", terminal:true); CFRunLoopStop(loop)
    }
    emit(["ready":true,"pid":getpid(),"tag":String(tag)]); CFRunLoopRun()
}

@_cdecl("glim_hands_socket") public func glimHandsSocket(_ socketPath: UnsafePointer<CChar>?, _ preflight: Int32) {
    guard let socketPath = socketPath else { return }
    let path = String(cString:socketPath)
    let capacity = MemoryLayout.size(ofValue: sockaddr_un().sun_path)
    guard path.utf8.count < capacity else { return }
    let fd = socket(AF_UNIX, SOCK_STREAM, 0)
    guard fd >= 0 else { return }
    defer { close(fd) }
    var noSigPipe: Int32 = 1
    setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &noSigPipe, socklen_t(MemoryLayout<Int32>.size))
    var addr = sockaddr_un(); addr.sun_family = sa_family_t(AF_UNIX)
    withUnsafeMutablePointer(to:&addr.sun_path) { pathPtr in
        pathPtr.withMemoryRebound(to:CChar.self, capacity:capacity) { dest in
            _ = path.withCString { strlcpy(dest, $0, capacity) }
        }
    }
    let result = withUnsafePointer(to:&addr) { p in p.withMemoryRebound(to:sockaddr.self, capacity:1) { connect(fd, $0, socklen_t(MemoryLayout<sockaddr_un>.size)) } }
    guard result == 0 else { return }
    runGuard(fd, preflight != 0)
}
