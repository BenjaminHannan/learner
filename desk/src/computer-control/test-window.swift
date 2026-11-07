// Throwaway window for the explicitly requested takeover test.
import AppKit
import CoreGraphics
import Foundation

func emit(_ row: [String:Any]) {
    if let d = try? JSONSerialization.data(withJSONObject:row), let s = String(data:d,encoding:.utf8) { print(s); fflush(stdout) }
}
final class TestView: NSView {
    override var acceptsFirstResponder: Bool { true }
    override func mouseDown(with event:NSEvent) { emit(["event":"mouseDown"]) }
    override func mouseUp(with event:NSEvent) { emit(["event":"mouseUp"]) }
    override func flagsChanged(with event:NSEvent) { emit(["event":"flags", "shift":event.modifierFlags.contains(.shift)]) }
    override func keyDown(with event:NSEvent) { emit(["event":"keyDown", "code":event.keyCode]) }
    override func keyUp(with event:NSEvent) { emit(["event":"keyUp", "code":event.keyCode]) }
    override func draw(_ rect:NSRect) { NSColor.windowBackgroundColor.setFill(); rect.fill() }
}
let app = NSApplication.shared
app.setActivationPolicy(.regular)
let frame = NSRect(x:250,y:250,width:420,height:260)
let window = NSWindow(contentRect:frame,styleMask:[.titled,.closable],backing:.buffered,defer:false)
window.title = "Glim hands safety test"
window.contentView = TestView(frame:NSRect(x:0,y:0,width:420,height:260))
window.makeKeyAndOrderFront(nil); window.makeFirstResponder(window.contentView)
app.activate(ignoringOtherApps:true)
let bounds = CGDisplayBounds(CGMainDisplayID())
NotificationCenter.default.addObserver(forName:NSApplication.didResignActiveNotification, object:nil, queue:.main) { _ in emit(["event":"focus-lost"]) }
DispatchQueue.main.asyncAfter(deadline:.now()+0.5) {
    let front = NSWorkspace.shared.frontmostApplication?.processIdentifier == getpid()
    emit(["ready":true,"pid":getpid(),"x":frame.midX,"y":bounds.height-frame.midY,"front":front])
}
app.run()
