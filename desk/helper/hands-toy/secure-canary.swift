// Fake-data-only native test. A live plain-field control prevents an empty-tap false pass.
import Foundation
import AppKit
import CoreGraphics
import ApplicationServices
if CommandLine.arguments.contains("--request-permissions") {
 _ = CGRequestListenEventAccess()
 _ = AXIsProcessTrustedWithOptions([kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String:true] as CFDictionary)
 exit(0)
}
let out=CommandLine.arguments.count>1 ? CommandLine.arguments[1]:""
guard !out.isEmpty else{exit(2)}
func result(_ value:[String:Any],_ code:Int32)->Never{if let d=try? JSONSerialization.data(withJSONObject:value,options:[.prettyPrinted,.sortedKeys]){try? d.write(to:URL(fileURLWithPath:out))};exit(code)}
guard CGPreflightListenEventAccess() && AXIsProcessTrusted() else{result(["status":"INCOMPLETE","reason":"native test process has no Input Monitoring/Accessibility permission","normalControl":false,"secureCanaryTyped":false,"savedFilesSearched":false],3)}
let idle=CGEventSource.secondsSinceLastEventType(.hidSystemState,eventType:CGEventType(rawValue:~0)!)
guard idle>=300 else{result(["status":"DEFERRED","reason":"Ben must be away five minutes for the fake-field test"],4)}
let app=NSApplication.shared;app.setActivationPolicy(.accessory)
let window=NSWindow(contentRect:NSRect(x:100,y:100,width:460,height:160),styleMask:[.titled,.closable],backing:.buffered,defer:false);window.title="Glim fake password test — own window only"
let plain=NSTextField(frame:NSRect(x:20,y:90,width:420,height:24)),secure=NSSecureTextField(frame:NSRect(x:20,y:40,width:420,height:24));window.contentView?.addSubview(plain);window.contentView?.addSubview(secure)
let normal="HandsNormalControl42",canary="HandsFakePass7x93";var observed="",tap:CFMachPort?,injecting=false
let callback:CGEventTapCallBack={_,kind,event,_ in
 if kind == .tapDisabledByTimeout || kind == .tapDisabledByUserInput{result(["status":"INCOMPLETE","reason":"tap disabled"],5)}
 if event.getIntegerValueField(.eventSourceUserData) != 0x48414E4453 {result(["status":"DEFERRED","reason":"physical user input; test stopped without recording it"],4)}
 if kind == .keyDown{var n=0;var chars=[UniChar](repeating:0,count:128);event.keyboardGetUnicodeString(maxStringLength:128,actualStringLength:&n,unicodeString:&chars);observed+=String(utf16CodeUnits:chars,count:n)}
 return Unmanaged.passUnretained(event)
}
tap=CGEvent.tapCreate(tap:.cgSessionEventTap,place:.headInsertEventTap,options:.listenOnly,eventsOfInterest:(CGEventMask(1)<<CGEventType.keyDown.rawValue)|(CGEventMask(1)<<CGEventType.keyUp.rawValue)|(CGEventMask(1)<<CGEventType.mouseMoved.rawValue)|(CGEventMask(1)<<CGEventType.leftMouseDown.rawValue)|(CGEventMask(1)<<CGEventType.scrollWheel.rawValue),callback:callback,userInfo:nil)
guard let tap=tap else{result(["status":"INCOMPLETE","reason":"event tap unavailable"],3)}
CFRunLoopAddSource(CFRunLoopGetMain(),CFMachPortCreateRunLoopSource(nil,tap,0),.commonModes);CGEvent.tapEnable(tap:tap,enable:true)
func typeText(_ text:String){for unit in text.utf16 {guard NSWorkspace.shared.frontmostApplication?.processIdentifier==getpid() else{result(["status":"DEFERRED","reason":"test window lost focus"],4)};for down in [true,false]{if let event=CGEvent(keyboardEventSource:nil,virtualKey:0,keyDown:down){var u=unit;event.keyboardSetUnicodeString(stringLength:1,unicodeString:&u);event.setIntegerValueField(.eventSourceUserData,value:0x48414E4453);event.post(tap:.cghidEventTap)}};usleep(20000)}}
window.makeKeyAndOrderFront(nil);app.activate(ignoringOtherApps:true);window.makeFirstResponder(plain)
DispatchQueue.global().asyncAfter(deadline:.now()+1){typeText(normal);DispatchQueue.main.asyncAfter(deadline:.now()+0.4){let control=observed.contains(normal)&&plain.stringValue==normal;window.makeFirstResponder(secure);DispatchQueue.global().asyncAfter(deadline:.now()+0.3){typeText(canary);DispatchQueue.main.asyncAfter(deadline:.now()+0.4){let typed=secure.stringValue==canary;let leak=observed.contains(canary);try? observed.write(toFile:URL(fileURLWithPath:out).deletingLastPathComponent().appendingPathComponent("canary-tap-stream.log").path,atomically:true,encoding:.utf8);window.close();result(["status":control && typed && !leak ? "PASS":"FAIL","normalControl":control,"secureCanaryTyped":typed,"literalSecretSeenByTap":leak,"note":"native NSSecureTextField path only; caller must also search recorder files"],control && typed && !leak ? 0:1)}}}}
app.run()
