// Local foreground-window capture + event tap. Never posts input or runs a policy.
// --preflight is read-only. --capture requires the outer OFF/release gate.
import Foundation
import AppKit
import CoreGraphics
import ScreenCaptureKit
import CoreMedia
import Carbon
import Darwin
import CryptoKit
let args=Set(CommandLine.arguments.dropFirst())
let arguments=Array(CommandLine.arguments.dropFirst())
let proofSession:String? = {guard let index=arguments.firstIndex(of:"--proof-session"),index+1<arguments.count,!arguments[index+1].isEmpty else{return nil};return arguments[index+1]}()
let emitLock=NSLock()
func emitLocked(_ row:[String:Any]) -> Bool {
 guard let data=try? JSONSerialization.data(withJSONObject:row) else{return false}
 var out=data;out.append(10)
 return out.withUnsafeBytes { bytes in
  guard let address=bytes.baseAddress else{return false};var offset=0
  while offset<bytes.count {let amount=Darwin.write(3,address.advanced(by:offset),bytes.count-offset);if amount<0 && errno==EINTR {continue};if amount<=0 {return false};offset += amount};return true
 }
}
func emit(_ row:[String:Any]) {emitLock.lock();defer{emitLock.unlock()};if proofSession == nil {if let data=try? JSONSerialization.data(withJSONObject:row){var out=data;out.append(10);FileHandle(fileDescriptor:3,closeOnDealloc:false).write(out)}}else if !emitLocked(row){exit(5)}}
func monotonicMs()->Double {Double(DispatchTime.now().uptimeNanoseconds)/1e6}
let app=NSApplication.shared
let sourceTag:Int64=0x474C494D
var tap:CFMachPort?
var wasSecure=IsSecureEventInputEnabled()
var lastMotion:Double=0
let callback:CGEventTapCallBack={_,kind,event,_ in
 if kind == .tapDisabledByTimeout || kind == .tapDisabledByUserInput {emit(["type":"source_error","reason":"event tap disabled"]);exit(4)}
 // Observe only physical input. Do not turn Glim's own attempts into Ben demos.
 if event.getIntegerValueField(.eventSourceUserData)==sourceTag{return Unmanaged.passUnretained(event)}
 if args.contains("--scratch-benchmark") {emit(["type":"source_error","reason":"physical input; scratch capture stopped"]);exit(6)}
 let t=monotonicMs()
 let eventKind:String
 switch kind {case .keyDown:eventKind="key_down";case .keyUp:eventKind="key_up";case .flagsChanged:eventKind="modifiers";case .leftMouseDown,.rightMouseDown:eventKind="mouse_down";case .leftMouseUp,.rightMouseUp:eventKind="mouse_up";case .scrollWheel:eventKind="scroll";default:eventKind="mouse_move"}
 if kind == .keyDown || kind == .keyUp || kind == .flagsChanged {
  var count=0;var chars=[UniChar](repeating:0,count:64);event.keyboardGetUnicodeString(maxStringLength:64,actualStringLength:&count,unicodeString:&chars)
  emit(["type":"key","t":t,"kind":eventKind,"source":"physical_unverified","eventTimestampNs":event.timestamp,"flags":event.flags.rawValue,"keyCode":event.getIntegerValueField(.keyboardEventKeycode),"down":kind == .keyDown,"text":String(utf16CodeUnits:chars,count:count)])
 }else{if kind == .mouseMoved || kind == .leftMouseDragged || kind == .rightMouseDragged {if t-lastMotion<8.333{return Unmanaged.passUnretained(event)};lastMotion=t};let p=event.location;emit(["type":"mouse","t":t,"kind":eventKind,"source":"physical_unverified","eventTimestampNs":event.timestamp,"flags":event.flags.rawValue,"x":p.x,"y":p.y,"button":event.getIntegerValueField(.mouseEventButtonNumber),"down":kind == .leftMouseDown || kind == .rightMouseDown,"wheel":event.getIntegerValueField(.scrollWheelEventDeltaAxis1)])}
 return Unmanaged.passUnretained(event)
}
let types:[CGEventType]=[.keyDown,.keyUp,.flagsChanged,.mouseMoved,.leftMouseDown,.leftMouseUp,.rightMouseDown,.rightMouseUp,.leftMouseDragged,.rightMouseDragged,.scrollWheel]
let mask:CGEventMask=types.reduce(0) { $0 | (CGEventMask(1)<<CGEventMask($1.rawValue)) }
final class Output:NSObject,SCStreamOutput,SCStreamDelegate {
 var count=0
 let lock=NSLock();let frameLock=NSLock();var closed=false;var generation=0;var ambiguous=true;var bounds:[String:Double]=[:]
 func boundary(_ rect:CGRect,_ uncertain:Bool)->Int {lock.lock();defer{lock.unlock()};generation += 1;ambiguous=uncertain;bounds=["x":rect.origin.x,"y":rect.origin.y,"width":rect.width,"height":rect.height];return generation}
 func stream(_ stream:SCStream,didStopWithError error:Error){if proofSession != nil {exit(5)};emit(["type":"source_error","reason":"capture stopped"]);exit(5)}
 func stream(_ stream:SCStream,didOutputSampleBuffer sampleBuffer:CMSampleBuffer,of type:SCStreamOutputType){
  guard type == .screen,let buffer=CMSampleBufferGetImageBuffer(sampleBuffer) else{return}
  if proofSession != nil {guard let attachments=CMSampleBufferGetSampleAttachmentsArray(sampleBuffer,createIfNecessary:false) as? [[SCStreamFrameInfo:Any]],let raw=attachments.first?[.status] as? Int,let status=SCFrameStatus(rawValue:raw),status == .complete else{return}}
  frameLock.lock();defer{frameLock.unlock()}
  if proofSession != nil && closed {return}
  let received=monotonicMs()
  CVPixelBufferLockBaseAddress(buffer,.readOnly);defer{CVPixelBufferUnlockBaseAddress(buffer,.readOnly)}
  guard let base=CVPixelBufferGetBaseAddress(buffer) else{return};let stride=CVPixelBufferGetBytesPerRow(buffer),width=CVPixelBufferGetWidth(buffer),height=CVPixelBufferGetHeight(buffer)
  guard width==1280 && height==720 else{return}
  var frame=Data(capacity:width*height*4);for y in 0..<height {frame.append(base.advanced(by:y*stride).assumingMemoryBound(to:UInt8.self),count:width*4)}
  let written=frame.withUnsafeBytes { bytes -> Bool in
   guard let address=bytes.baseAddress else{return false};var offset=0
   while offset<bytes.count {let amount=Darwin.write(STDOUT_FILENO,address.advanced(by:offset),bytes.count-offset);if amount<0 && errno==EINTR {continue};if amount<=0 {return false};offset += amount};return true
  }
  if !written {exit(5)}
  let pts=CMSampleBufferGetPresentationTimeStamp(sampleBuffer)
  lock.lock();let frameGeneration=generation,frameAmbiguous=ambiguous,frameBounds=bounds;lock.unlock()
  count += 1;var row:[String:Any]=["type":"frame","frameId":count,"t":monotonicMs(),"receiveMonotonicMs":received,"writeCompleteMonotonicMs":monotonicMs(),"presentationValue":pts.value,"presentationTimescale":pts.timescale,"presentationFlags":pts.flags.rawValue,"presentationEpoch":pts.epoch,"generation":frameGeneration,"transitionAmbiguous":frameAmbiguous,"width":width,"height":height,"pixelFormat":"BGRA","transform":["verified":false,"sourceBounds":frameBounds],"encodedMapping":"unavailable"]
  if let session=proofSession {row["sourceContract"]="hands-toy-bgra-frame-v1";row["session"]=session;row["sourcePid"]=getpid();row["rawByteCount"]=frame.count;row["rawSha256"]=SHA256.hash(data:frame).map{String(format:"%02x",$0)}.joined()};emit(row)
 }
}
let output=Output();var stream:SCStream?;var lastWindow:CGWindowID=0;var lastBounds:CGRect = .null
@MainActor var stopping=false
@MainActor var updating=false
@MainActor var updateTask:Task<Void,Never>?
@MainActor func update() async {
 do {
  let content=try await SCShareableContent.excludingDesktopWindows(true,onScreenWindowsOnly:true)
  if proofSession != nil && stopping {return}
  if args.contains("--scratch-benchmark") {
   if stream != nil{return}
   guard let display=content.displays.first(where:{$0.displayID==CGMainDisplayID()}) else{throw NSError(domain:"screen",code:1)}
   let filter=SCContentFilter(display:display,excludingWindows:[])
   let cfg=SCStreamConfiguration();cfg.width=1280;cfg.height=720;cfg.pixelFormat=kCVPixelFormatType_32BGRA;cfg.minimumFrameInterval=CMTime(value:1,timescale:20);cfg.queueDepth=3;cfg.showsCursor=true;cfg.capturesAudio=false
   let next=SCStream(filter:filter,configuration:cfg,delegate:output);try next.addStreamOutput(output,type:.screen,sampleHandlerQueue:DispatchQueue(label:"glim.scratch.frames"));stream=next;try await next.startCapture();return
  }
  guard let front=NSWorkspace.shared.frontmostApplication,let window=content.windows.filter({$0.owningApplication?.processID==front.processIdentifier && $0.windowLayer==0 && $0.frame.width>10}).max(by:{$0.frame.width*$0.frame.height<$1.frame.width*$1.frame.height}) else{if let old=stream {let generation=output.boundary(.zero,true);emit(["type":"capture_boundary","t":monotonicMs(),"reason":"window_gap","generation":generation]);if proofSession != nil {try await old.stopCapture()}else{try? await old.stopCapture()};stream=nil};return}
  if window.windowID==lastWindow && window.frame==lastBounds && stream != nil{return}
  let generation=output.boundary(window.frame,stream != nil || lastWindow != 0)
  emit(["type":"capture_boundary","t":monotonicMs(),"reason":stream == nil ? "start_or_restart":"filter_or_geometry_change","generation":generation,"windowId":window.windowID,"sourceBounds":["x":window.frame.origin.x,"y":window.frame.origin.y,"width":window.frame.width,"height":window.frame.height],"geometry":"unverified","encodedMapping":"unavailable"])
  let filter=SCContentFilter(desktopIndependentWindow:window)
  if let old=stream {try await old.updateContentFilter(filter)}else{
   let cfg=SCStreamConfiguration();cfg.width=1280;cfg.height=720;cfg.pixelFormat=kCVPixelFormatType_32BGRA;cfg.minimumFrameInterval=CMTime(value:1,timescale:20);cfg.queueDepth=3;cfg.showsCursor=true;cfg.capturesAudio=false
   let next=SCStream(filter:filter,configuration:cfg,delegate:output);try next.addStreamOutput(output,type:.screen,sampleHandlerQueue:DispatchQueue(label:"hands.recorder.frames"));stream=next;try await next.startCapture()
  };lastWindow=window.windowID;lastBounds=window.frame
 }catch{emit(["type":"source_error","reason":"capture unavailable"]);exit(5)}
}

@_cdecl("glim_capture_main") public func glimCaptureMain() {
if args.contains("--request-permissions") {
 _ = CGRequestScreenCaptureAccess()
 _ = CGRequestListenEventAccess()
 print("Enable Premonition in System Settings > Privacy & Security > Screen & System Audio Recording and Input Monitoring. Then quit/restart this helper.")
 exit(0)
}
if args.contains("--preflight") {
 var row:[String:Any] = ["screen":CGPreflightScreenCaptureAccess(),"input":CGPreflightListenEventAccess(),"accessibility":AXIsProcessTrusted(),"pid":getpid(),"parentPid":getppid()]
 // Diagnostic only: the OS responsibility API is private; never use it to grant access.
 if let symbol=dlsym(UnsafeMutableRawPointer(bitPattern:-2),"responsibility_get_pid_responsible_for_pid") {
  let query=unsafeBitCast(symbol,to:(@convention(c)(Int32)->Int32).self)
  let pid=query(getpid());row["responsiblePid"]=pid
  if let owner=NSRunningApplication(processIdentifier:pid) {row["responsibleBundleId"]=owner.bundleIdentifier;row["responsibleName"]=owner.localizedName;row["responsibleBundlePath"]=owner.bundleURL?.path}
 }
 let data=try! JSONSerialization.data(withJSONObject:row,options:[.sortedKeys]);print(String(data:data,encoding:.utf8)!);exit(0)
}
if !args.contains("--capture") && !args.contains("--scratch-benchmark") {exit(2)}
if args.contains("--proof-session") && (proofSession == nil || arguments.filter({$0 == "--proof-session"}).count != 1 || !args.contains("--capture") || args.contains("--scratch-benchmark")) {exit(2)}
if proofSession != nil {signal(SIGPIPE,SIG_IGN)}
emit(["type":"clock_anchor","t":monotonicMs(),"wallTimeMs":Date().timeIntervalSince1970*1000,"clock":"dispatch_uptime_ms","encodedMapping":"unavailable"])
if args.contains("--scratch-benchmark") {_ = Timer.scheduledTimer(withTimeInterval:120,repeats:false){_ in exit(0)}}
if !CGPreflightScreenCaptureAccess() || !CGPreflightListenEventAccess() {fputs("capture/input permission missing; no permission prompt, no recording\n",stderr);exit(3)}
app.setActivationPolicy(.prohibited)
tap=CGEvent.tapCreate(tap:.cgSessionEventTap,place:.headInsertEventTap,options:.listenOnly,eventsOfInterest:mask,callback:callback,userInfo:nil)
guard let tap=tap else{exit(3)}
CFRunLoopAddSource(CFRunLoopGetMain(),CFMachPortCreateRunLoopSource(nil,tap,0),.commonModes);CGEvent.tapEnable(tap:tap,enable:true)
let timer=Timer.scheduledTimer(withTimeInterval:0.25,repeats:true){_ in MainActor.assumeIsolated {if stopping {return};let secure=IsSecureEventInputEnabled();if secure != wasSecure {emit(["type":secure ? "secure_input_on":"secure_input_off","t":Double(DispatchTime.now().uptimeNanoseconds)/1e6]);wasSecure=secure};if !updating {updating=true;updateTask=Task{@MainActor in await update();updating=false}}}}
// Closing the parent pipe stops all capture, including after parent crash.
DispatchQueue.global().async {if proofSession == nil {while readLine() != nil{};exit(0)};var input=[UInt8](repeating:0,count:4096);while true {let amount=Darwin.read(STDIN_FILENO,&input,input.count);if amount<0 && errno==EINTR {continue};if amount<0 {exit(5)};if amount==0 {break}};DispatchQueue.main.async {
 guard !stopping else{return};stopping=true;timer.invalidate();CGEvent.tapEnable(tap:tap,enable:false);CFMachPortInvalidate(tap)
 Task {@MainActor in
  await updateTask?.value
  do {if let active=stream {try await active.stopCapture();stream=nil}}catch{emit(["type":"source_error","reason":"capture stop failed"]);exit(5)}
  DispatchQueue.global().async {
   output.frameLock.lock();output.closed=true
   emitLock.lock()
   guard let session=proofSession,emitLocked(["type":"source_end","sourceContract":"hands-toy-bgra-frame-v1","session":session,"sourcePid":getpid(),"stopCause":"stdin-eof","complete":false,"drainComplete":true,"captureHealth":"callback-quiescence-unverified","frameCount":output.count]) else{exit(5)}
   exit(0)
  }
 }
}}
app.run()

}
