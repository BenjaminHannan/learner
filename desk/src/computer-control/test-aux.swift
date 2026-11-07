// Test-only monitor and simulated physical event source. No training or model.
import Foundation
import CoreGraphics
import ApplicationServices
import Darwin

private var output: Int32 = -1
private let outputLock = NSLock()
private let testTag: Int64 = 0x48414e4453544553
private let tagLock = NSLock()
private var allowedTags = Set<Int64>([testTag])
private func emit(_ row: [String:Any]) {
    outputLock.lock(); defer { outputLock.unlock() }
    guard let data = try? JSONSerialization.data(withJSONObject:row), let s = String(data:data, encoding:.utf8) else { return }
    let bytes = Array((s + "\n").utf8)
    bytes.withUnsafeBytes { ptr in
        var n = 0
        while n < ptr.count { let wrote = write(output, ptr.baseAddress!.advanced(by:n), ptr.count-n); if wrote <= 0 { break }; n += wrote }
    }
}
private func readCommand(_ fd: Int32) -> String? {
    var bytes = [UInt8](), c: UInt8 = 0
    while read(fd, &c, 1) == 1 { if c == 10 { return String(bytes:bytes, encoding:.utf8) }; bytes.append(c); if bytes.count > 512 { return nil } }
    return nil
}
private func monitor(_ fd: Int32) {
    guard CGPreflightListenEventAccess() else { emit(["error":"test monitor lacks input permission"]); return }
    let types:[CGEventType] = [.keyDown,.keyUp,.flagsChanged,.mouseMoved,.leftMouseDown,.leftMouseUp,.rightMouseDown,.rightMouseUp,.otherMouseDown,.otherMouseUp,.leftMouseDragged,.rightMouseDragged,.otherMouseDragged,.scrollWheel]
    var mask: CGEventMask = 0; for t in types { mask |= CGEventMask(1) << CGEventMask(t.rawValue) }
    let callback: CGEventTapCallBack = { _, kind, event, _ in
        if kind == .tapDisabledByTimeout || kind == .tapDisabledByUserInput { emit(["event":"monitor-disabled"]) }
        else {
            let tag = event.getIntegerValueField(.eventSourceUserData)
            tagLock.lock(); let ours = allowedTags.contains(tag); tagLock.unlock()
            if !ours { emit(["event":"real-input", "atNs":DispatchTime.now().uptimeNanoseconds]) }
        }
        return Unmanaged.passUnretained(event)
    }
    guard let tap = CGEvent.tapCreate(tap:.cgSessionEventTap,place:.headInsertEventTap,options:.listenOnly,eventsOfInterest:mask,callback:callback,userInfo:nil), let source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault,tap,0) else { emit(["error":"test monitor unavailable"]); return }
    let loop = CFRunLoopGetCurrent()
    CFRunLoopAddSource(loop,source,.commonModes); CGEvent.tapEnable(tap:tap,enable:true)
    DispatchQueue.global().async {
        while let command = readCommand(fd) {
            if command.hasPrefix("tag "), let tag = Int64(command.dropFirst(4)), tag > 0 {
                tagLock.lock(); allowedTags.insert(tag); tagLock.unlock(); emit(["event":"tagged","tag":String(tag)])
            } else { break }
        }
        CFRunLoopStop(loop)
    }
    let any = CGEventType(rawValue:0xFFFFFFFF)!
    emit(["ready":true,"idleSeconds":CGEventSource.secondsSinceLastEventType(.combinedSessionState,eventType:any)])
    CFRunLoopRun(); CGEvent.tapEnable(tap:tap,enable:false); CFRunLoopRemoveSource(loop,source,.commonModes); CFMachPortInvalidate(tap)
}
private func inject(_ fd: Int32) {
    guard AXIsProcessTrusted() else { emit(["error":"test sender lacks accessibility permission"]); return }
    emit(["ready":true])
    while let line = readCommand(fd) {
        guard line == "fire", let down = CGEvent(keyboardEventSource:nil,virtualKey:105,keyDown:true), let up = CGEvent(keyboardEventSource:nil,virtualKey:105,keyDown:false) else { break }
        down.setIntegerValueField(.eventSourceUserData,value:testTag); up.setIntegerValueField(.eventSourceUserData,value:testTag)
        let sent = DispatchTime.now().uptimeNanoseconds
        down.post(tap:.cghidEventTap); up.post(tap:.cghidEventTap)
        emit(["event":"posted", "atNs":sent])
    }
}
@_cdecl("glim_hands_socket") public func testAux(_ socketPath: UnsafePointer<CChar>?, _ monitorMode: Int32) {
    guard let socketPath = socketPath else { return }
    let path = String(cString:socketPath), capacity = MemoryLayout.size(ofValue:sockaddr_un().sun_path)
    guard path.utf8.count < capacity else { return }
    let fd = socket(AF_UNIX,SOCK_STREAM,0); guard fd >= 0 else { return }; defer { close(fd) }
    var noSig: Int32 = 1; setsockopt(fd,SOL_SOCKET,SO_NOSIGPIPE,&noSig,socklen_t(MemoryLayout<Int32>.size))
    var addr = sockaddr_un(); addr.sun_family = sa_family_t(AF_UNIX)
    withUnsafeMutablePointer(to:&addr.sun_path) { p in p.withMemoryRebound(to:CChar.self,capacity:capacity) { dst in _ = path.withCString { strlcpy(dst,$0,capacity) } } }
    let ok = withUnsafePointer(to:&addr) { p in p.withMemoryRebound(to:sockaddr.self,capacity:1) { connect(fd,$0,socklen_t(MemoryLayout<sockaddr_un>.size)) } }
    guard ok == 0 else { return }; output = fd
    if monitorMode != 0 { monitor(fd) } else { inject(fd) }
}
