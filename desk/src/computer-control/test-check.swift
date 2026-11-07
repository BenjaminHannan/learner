// Independent, read-only accessibility checks for the requested test tasks.
import Foundation
import AppKit
import ApplicationServices
import Darwin

private func connectSocket(_ path: String) -> Int32 {
    let cap = MemoryLayout.size(ofValue:sockaddr_un().sun_path)
    guard path.utf8.count < cap else { return -1 }
    let fd = socket(AF_UNIX,SOCK_STREAM,0); guard fd >= 0 else { return -1 }
    var addr = sockaddr_un(); addr.sun_family = sa_family_t(AF_UNIX)
    withUnsafeMutablePointer(to:&addr.sun_path) { p in p.withMemoryRebound(to:CChar.self,capacity:cap) { dst in _ = path.withCString { strlcpy(dst,$0,cap) } } }
    let ok = withUnsafePointer(to:&addr) { p in p.withMemoryRebound(to:sockaddr.self,capacity:1) { connect(fd,$0,socklen_t(MemoryLayout<sockaddr_un>.size)) } }
    if ok != 0 { close(fd); return -1 }; return fd
}
private func emit(_ fd:Int32,_ row:[String:Any]) {
    guard let d = try? JSONSerialization.data(withJSONObject:row), let line = String(data:d,encoding:.utf8) else { return }
    let bytes = Array((line+"\n").utf8); bytes.withUnsafeBytes { ptr in _ = write(fd,ptr.baseAddress!,ptr.count) }
}
private func attr(_ element:AXUIElement,_ name:String) -> CFTypeRef? {
    var value:CFTypeRef?; return AXUIElementCopyAttributeValue(element,name as CFString,&value) == .success ? value : nil
}
private func str(_ value:CFTypeRef?) -> String { (value as? String) ?? "" }
private func children(_ element:AXUIElement) -> [AXUIElement] { (attr(element,"AXChildren") as? [AXUIElement]) ?? [] }
private func bold(_ element:AXUIElement, text:String, needle:String) -> Bool {
    guard let start = text.range(of:needle), let utf16 = start.lowerBound.samePosition(in:text.utf16), let end = start.upperBound.samePosition(in:text.utf16) else { return false }
    var range = CFRange(location:text.utf16.distance(from:text.utf16.startIndex,to:utf16), length:text.utf16.distance(from:utf16,to:end))
    guard let encoded = AXValueCreate(.cfRange,&range) else { return false }
    var result:CFTypeRef?
    guard AXUIElementCopyParameterizedAttributeValue(element,"AXAttributedStringForRange" as CFString,encoded,&result) == .success,
          let value = result as? NSAttributedString, value.length > 0 else { return false }
    var ok = true
    value.enumerateAttributes(in:NSRange(location:0,length:value.length)) { attributes,_,_ in
        if let font = attributes[.font] as? NSFont, NSFontManager.shared.traits(of:font).contains(.boldFontMask) { return }
        if let info = attributes[NSAttributedString.Key("AXFont")] as? [String:Any] {
            let style = (info["AXFontStyle"] as? String ?? "").lowercased()
            let name = (info["AXFontName"] as? String ?? "").lowercased()
            if style.range(of:"\\b(bold|semibold|demibold|heavy|black)\\b",options:.regularExpression) != nil || name.range(of:"[- ](bold|semibold|demibold|heavy|black)(italic)?$",options:.regularExpression) != nil { return }
        }
        ok = false
    }
    return ok
}
private func check(_ request:[String:Any]) -> [String:Any] {
    guard AXIsProcessTrusted(), let name = request["app"] as? String, let target = request["target"] as? String, !target.isEmpty else { return ["ok":false,"error":"accessibility or target unavailable"] }
    guard let app = NSWorkspace.shared.runningApplications.first(where:{ $0.localizedName?.lowercased() == name.lowercased() }) else { return ["ok":false,"error":"app not running"] }
    var stack:[(AXUIElement,Int,Bool)] = [(AXUIElementCreateApplication(app.processIdentifier),0,false)], seen = 0, found = false, exact = false, selected = false, isBold = false
    while let (el,depth,parentSelected) = stack.popLast(), seen < 2500 {
        seen += 1
        let isSelected = parentSelected || (attr(el,"AXSelected") as? Bool) == true
        let value = str(attr(el,"AXValue")), title = str(attr(el,"AXTitle")), description = str(attr(el,"AXDescription"))
        if value.localizedCaseInsensitiveContains(target) || title.localizedCaseInsensitiveContains(target) || description.localizedCaseInsensitiveContains(target) {
            found = true
            if value.trimmingCharacters(in:.newlines) == target { exact = true }
            if isSelected && (value == target || title == target || description == target) { selected = true }
            if value.contains(target) && bold(el,text:value,needle:target) { isBold = true }
        }
        if let selectedChildren = attr(el,"AXSelectedChildren") as? [AXUIElement] {
            for child in selectedChildren {
                let value = str(attr(child,"AXValue")), title = str(attr(child,"AXTitle")), description = str(attr(child,"AXDescription"))
                if value == target || title == target || description == target { selected = true; found = true }
            }
        }
        if depth < 18 {
            for child in children(el) { stack.append((child,depth+1,isSelected)) }
            if let selectedChildren = attr(el,"AXSelectedChildren") as? [AXUIElement] { for child in selectedChildren { stack.append((child,depth+1,true)) } }
        }
    }
    return ["ok":true,"found":found,"exact":exact,"selected":selected,"bold":isBold,"nodesChecked":seen]
}
@_cdecl("glim_hands_socket") public func testCheck(_ socketPath:UnsafePointer<CChar>?,_ ignored:Int32) {
    guard let socketPath = socketPath else { return }
    let fd = connectSocket(String(cString:socketPath)); guard fd >= 0 else { return }; defer { close(fd) }
    var noSig:Int32 = 1; setsockopt(fd,SOL_SOCKET,SO_NOSIGPIPE,&noSig,socklen_t(MemoryLayout<Int32>.size))
    emit(fd,["ready":true]); var bytes=[UInt8](), c:UInt8=0
    while read(fd,&c,1) == 1 && bytes.count < 4096 { if c == 10 { break }; bytes.append(c) }
    guard let request = (try? JSONSerialization.jsonObject(with:Data(bytes))) as? [String:Any] else { emit(fd,["ok":false,"error":"invalid check"]); return }
    emit(fd,check(request))
}
