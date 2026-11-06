// HANDS native guard. No CGEvent posting, recording, or desktop control.
// --self-test exercises the SAME locked revoke path as the physical-input tap.
import Foundation
import CoreGraphics
import Darwin
final class Guard {
 let lock = NSLock()
 var lease: String? = nil
 var keys = Set<String>(), buttons = Set<String>()
 var events = [[String:Any]](), version = 0
 var expiry: UInt64 = 0
 func ns() -> UInt64 { DispatchTime.now().uptimeNanoseconds }
 func revoke(_ reason: String) -> [String:Any] {
  lock.lock(); defer {lock.unlock()}
  let start=ns();lease=nil;expiry=0;version += 1
  let released=keys.count+buttons.count;keys.removeAll();buttons.removeAll()
  let row:[String:Any] = ["kind":"revoked","reason":reason,"released":released,"atNs":ns(),"guardMs":Double(ns()-start)/1e6]
  events.append(row); if events.count>1000 {events.removeFirst()};return row
 }
 func grant() -> String { _ = revoke("new lease");lock.lock();defer{lock.unlock()};let id=UUID().uuidString;lease=id;expiry=ns()+50_000_000;return id }
 func packet(_ id: String, _ held: [String]) -> Bool {lock.lock();defer{lock.unlock()};guard lease==id && ns()<expiry else{return false};keys=Set(held);expiry=ns()+50_000_000;return true}
 func expire() { lock.lock();let stale=lease != nil && ns()>=expiry;lock.unlock();if stale {_ = revoke("expired")} }
}
let g=Guard()
func emit(_ v: [String:Any]) {if let d=try? JSONSerialization.data(withJSONObject:v,options:[.sortedKeys]),let s=String(data:d,encoding:.utf8){print(s);fflush(stdout)}}
let args=Set(CommandLine.arguments.dropFirst())
if args.contains("--self-test") {
 var rows=[[String:Any]]();var failures=0
 for seed in [101,202,303] {for i in 0..<100 {let id=g.grant();if !g.packet(id,["Space","ArrowUp"]) {failures += 1};let r=g.revoke("test physical input \(seed):\(i)");if g.packet(id,["Space"]) {failures += 1};rows.append(r)}}
 emit(["mode":"native synthetic callback self-test, NOT physical-device proof","samples":rows.count,"failures":failures,"guardMs":rows.map{$0["guardMs"]!}]);exit(failures==0 ? 0:1)
}
if !args.contains("--watch") {emit(["error":"use --self-test or --watch; this helper cannot post input"]);exit(2)}
var tap: CFMachPort?
let tag:Int64=0x474C494D
let callback: CGEventTapCallBack = { _,kind,event,_ in
 if kind == .tapDisabledByTimeout || kind == .tapDisabledByUserInput {emit(g.revoke("input watcher disabled"));return Unmanaged.passUnretained(event)}
 if event.getIntegerValueField(.eventSourceUserData) != tag {emit(g.revoke("physical input"))}
 return Unmanaged.passUnretained(event)
}
// Unknown permission => no prompt, no lease. Every physical event stops; no debounce.
let types:[CGEventType]=[.keyDown,.keyUp,.flagsChanged,.mouseMoved,.leftMouseDown,.leftMouseUp,.rightMouseDown,.rightMouseUp,.otherMouseDown,.otherMouseUp,.leftMouseDragged,.rightMouseDragged,.scrollWheel]
var mask:CGEventMask=0;for t in types {mask |= CGEventMask(1)<<CGEventMask(t.rawValue)}
tap=CGEvent.tapCreate(tap:.cgSessionEventTap,place:.headInsertEventTap,options:.listenOnly,eventsOfInterest:mask,callback:callback,userInfo:nil)
guard let watcher=tap else {emit(["error":"physical input watcher unavailable; fail closed"]);exit(3)}
let src=CFMachPortCreateRunLoopSource(kCFAllocatorDefault,watcher,0)
CFRunLoopAddSource(CFRunLoopGetCurrent(),src,.commonModes);CGEvent.tapEnable(tap:watcher,enable:true)
let timer=DispatchSource.makeTimerSource(queue:DispatchQueue.global());timer.schedule(deadline:.now(),repeating:.milliseconds(2));timer.setEventHandler {g.expire()};timer.resume()
DispatchQueue.global().async {while let line=readLine(){guard let d=line.data(using:.utf8),let j=(try? JSONSerialization.jsonObject(with:d)) as? [String:Any] else {continue};switch j["op"] as? String {case "grant":emit(["leaseId":g.grant()]);case "packet":emit(["accepted":g.packet(j["leaseId"] as? String ?? "",j["keys"] as? [String] ?? [])]);default:emit(g.revoke("cancel"))}};emit(g.revoke("parent pipe closed"));exit(0)}
emit(["ready":true,"inputPosting":false]);CFRunLoopRun()
