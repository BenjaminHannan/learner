// Local full-display capture + event tap. Never posts input or runs a policy.
// --preflight is read-only. --capture requires the outer OFF/release gate.
import Foundation
import AppKit
import CoreGraphics
import ScreenCaptureKit
import CoreMedia
import Carbon
import Darwin
import CryptoKit
import VideoToolbox
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
 let lock=NSLock();let frameLock=NSLock();var closed=false;var generation=0;var bounds:[String:Double]=[:]
 var displays:[ObjectIdentifier:(rect:CGRect,image:CGImage?)]=[:];var canvas=CGRect.zero;var ready=false
 func configure(_ rect:CGRect) -> Int {lock.lock();defer{lock.unlock()};generation += 1;ready=false;canvas=rect;bounds=["x":rect.origin.x,"y":rect.origin.y,"width":rect.width,"height":rect.height];displays.removeAll();return generation}
 func add(_ stream:SCStream,_ rect:CGRect) {lock.lock();defer{lock.unlock()};displays[ObjectIdentifier(stream)]=(rect,nil)}
 func activate() {lock.lock();defer{lock.unlock()};ready=true}
 func stream(_ stream:SCStream,didStopWithError error:Error){emit(["type":"source_error","reason":"capture stopped"]);exit(5)}
 func stream(_ stream:SCStream,didOutputSampleBuffer sampleBuffer:CMSampleBuffer,of type:SCStreamOutputType){
  guard type == .screen,let buffer=CMSampleBufferGetImageBuffer(sampleBuffer) else{return}
  guard let attachments=CMSampleBufferGetSampleAttachmentsArray(sampleBuffer,createIfNecessary:false) as? [[SCStreamFrameInfo:Any]],let raw=attachments.first?[.status] as? Int,let status=SCFrameStatus(rawValue:raw),status == .complete else{return}
  var image:CGImage?;guard VTCreateCGImageFromCVPixelBuffer(buffer,options:nil,imageOut:&image)==noErr,let image=image else{return}
  lock.lock();defer{lock.unlock()};let id=ObjectIdentifier(stream);if let old=displays[id] {displays[id]=(old.rect,image)}
 }
 func writeFrame() {
  frameLock.lock();defer{frameLock.unlock()};if closed{return}
  lock.lock();let entries=Array(displays.values),rect=canvas,frameGeneration=generation,frameBounds=bounds,isReady=ready;lock.unlock()
  guard isReady,!entries.isEmpty,entries.allSatisfy({$0.image != nil}),rect.width>0,rect.height>0 else{return}
  let received=monotonicMs(),width=1280,height=720
  var frame=Data(count:width*height*4)
  let made=frame.withUnsafeMutableBytes { bytes -> Bool in
   guard let address=bytes.baseAddress,let context=CGContext(data:address,width:width,height:height,bitsPerComponent:8,bytesPerRow:width*4,space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedFirst.rawValue|CGBitmapInfo.byteOrder32Little.rawValue) else{return false}
   context.setFillColor(CGColor(gray:0,alpha:1));context.fill(CGRect(x:0,y:0,width:width,height:height))
   let scale=min(CGFloat(width)/rect.width,CGFloat(height)/rect.height),left=(CGFloat(width)-rect.width*scale)/2,top=(CGFloat(height)-rect.height*scale)/2
   for item in entries {let r=item.rect;let target=CGRect(x:left+(r.minX-rect.minX)*scale,y:CGFloat(height)-top-(r.maxY-rect.minY)*scale,width:r.width*scale,height:r.height*scale);context.draw(item.image!,in:target)}
   return true
  }
  if !made {emit(["type":"source_error","reason":"display composition failed"]);exit(5)}
  let written=frame.withUnsafeBytes { bytes -> Bool in
   guard let address=bytes.baseAddress else{return false};var offset=0
   while offset<bytes.count {let amount=Darwin.write(STDOUT_FILENO,address.advanced(by:offset),bytes.count-offset);if amount<0 && errno==EINTR {continue};if amount<=0 {return false};offset += amount};return true
  }
  if !written {exit(5)}
  let pts=CMClockGetTime(CMClockGetHostTimeClock());count += 1
  var row:[String:Any]=["type":"frame","frameId":count,"t":monotonicMs(),"receiveMonotonicMs":received,"writeCompleteMonotonicMs":monotonicMs(),"presentationValue":pts.value,"presentationTimescale":pts.timescale,"presentationFlags":pts.flags.rawValue,"presentationEpoch":pts.epoch,"generation":frameGeneration,"transitionAmbiguous":false,"width":width,"height":height,"pixelFormat":"BGRA","transform":["verified":false,"sourceBounds":frameBounds],"encodedMapping":"unavailable"]
  if let session=proofSession {row["sourceContract"]="hands-toy-bgra-frame-v1";row["session"]=session;row["sourcePid"]=getpid();row["rawByteCount"]=frame.count;row["rawSha256"]=SHA256.hash(data:frame).map{String(format:"%02x",$0)}.joined()};emit(row)
 }
}
let output=Output();var streams:[SCStream]=[];var displaySignature=""
@MainActor var stopping=false
@MainActor var updating=false
@MainActor var updateTask:Task<Void,Never>?
@MainActor func update() async {
 do {
  let content=try await SCShareableContent.excludingDesktopWindows(false,onScreenWindowsOnly:true)
  if stopping {return}
  let selected=args.contains("--scratch-benchmark") ? content.displays.filter{$0.displayID==CGMainDisplayID()} : content.displays
  guard !selected.isEmpty else{throw NSError(domain:"screen",code:1)}
  let signature=selected.sorted{$0.displayID<$1.displayID}.map{"\($0.displayID):\(CGDisplayBounds($0.displayID))"}.joined(separator:";")
  if signature==displaySignature && !streams.isEmpty{return}
  for old in streams {try await old.stopCapture()};streams=[]
  let rect=selected.map{CGDisplayBounds($0.displayID)}.reduce(CGRect.null){$0.union($1)}
  let generation=output.configure(rect)
  emit(["type":"capture_boundary","t":monotonicMs(),"reason":"display_layout","generation":generation,"displayIds":selected.map{$0.displayID},"sourceBounds":["x":rect.minX,"y":rect.minY,"width":rect.width,"height":rect.height],"encodedMapping":"unavailable"])
  let scale=min(1280/rect.width,720/rect.height)
  for display in selected {
   let bounds=CGDisplayBounds(display.displayID),filter=SCContentFilter(display:display,excludingWindows:[])
   let cfg=SCStreamConfiguration();cfg.width=max(2,Int(bounds.width*scale));cfg.height=max(2,Int(bounds.height*scale));cfg.pixelFormat=kCVPixelFormatType_32BGRA;cfg.minimumFrameInterval=CMTime(value:1,timescale:20);cfg.queueDepth=3;cfg.showsCursor=true;cfg.capturesAudio=false
   let next=SCStream(filter:filter,configuration:cfg,delegate:output);output.add(next,bounds);try next.addStreamOutput(output,type:.screen,sampleHandlerQueue:DispatchQueue(label:"hands.recorder.frames"));streams.append(next);try await next.startCapture()
  }
  output.activate();displaySignature=signature
 }catch{emit(["type":"source_error","reason":"capture unavailable: \(error.localizedDescription)"]);exit(5)}
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
let frameTimer=DispatchSource.makeTimerSource(queue:DispatchQueue(label:"hands.recorder.composite"));frameTimer.schedule(deadline:.now(),repeating:.milliseconds(50));frameTimer.setEventHandler {output.writeFrame()};frameTimer.resume()
let timer=Timer.scheduledTimer(withTimeInterval:1,repeats:true){_ in MainActor.assumeIsolated {if stopping {return};let secure=IsSecureEventInputEnabled();if secure != wasSecure {emit(["type":secure ? "secure_input_on":"secure_input_off","t":Double(DispatchTime.now().uptimeNanoseconds)/1e6]);wasSecure=secure};if !updating {updating=true;updateTask=Task{@MainActor in await update();updating=false}}}}
// Closing the parent pipe stops all capture, including after parent crash.
DispatchQueue.global().async {var input=[UInt8](repeating:0,count:4096);while true {let amount=Darwin.read(STDIN_FILENO,&input,input.count);if amount<0 && errno==EINTR {continue};if amount<0 {exit(5)};if amount==0 {break}};DispatchQueue.main.async {
 guard !stopping else{return};stopping=true;timer.invalidate();frameTimer.cancel();CGEvent.tapEnable(tap:tap,enable:false);CFMachPortInvalidate(tap)
 Task {@MainActor in
  await updateTask?.value
  do {for active in streams {try await active.stopCapture()};streams=[]}catch{emit(["type":"source_error","reason":"capture stop failed"]);exit(5)}
  DispatchQueue.global().async {
   output.frameLock.lock();output.closed=true
   emitLock.lock()
   if let session=proofSession {guard emitLocked(["type":"source_end","sourceContract":"hands-toy-bgra-frame-v1","session":session,"sourcePid":getpid(),"stopCause":"stdin-eof","complete":false,"drainComplete":true,"captureHealth":"callback-quiescence-unverified","frameCount":output.count]) else{exit(5)}}
   exit(0)
  }
 }
}}
app.run()

}
