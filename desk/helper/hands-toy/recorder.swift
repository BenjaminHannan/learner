// Local foreground-window capture + event tap. Never posts input or runs a policy.
// --preflight is read-only. --capture requires the outer OFF/release gate.
import Foundation
import AppKit
import CoreGraphics
import ScreenCaptureKit
import CoreMedia
import Carbon
import Darwin
let args=Set(CommandLine.arguments.dropFirst())
func emit(_ row:[String:Any]) {if let d=try? JSONSerialization.data(withJSONObject:row){var out=d;out.append(10);FileHandle(fileDescriptor:3,closeOnDealloc:false).write(out)}}
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
 let t=Double(DispatchTime.now().uptimeNanoseconds)/1e6
 if kind == .keyDown || kind == .keyUp {
  var count=0;var chars=[UniChar](repeating:0,count:64);event.keyboardGetUnicodeString(maxStringLength:64,actualStringLength:&count,unicodeString:&chars)
  emit(["type":"key","t":t,"keyCode":event.getIntegerValueField(.keyboardEventKeycode),"down":kind == .keyDown,"text":String(utf16CodeUnits:chars,count:count)])
 }else{if kind == .mouseMoved || kind == .leftMouseDragged || kind == .rightMouseDragged {if t-lastMotion<8.333{return Unmanaged.passUnretained(event)};lastMotion=t};let p=event.location;emit(["type":"mouse","t":t,"x":p.x,"y":p.y,"button":event.getIntegerValueField(.mouseEventButtonNumber),"down":kind == .leftMouseDown || kind == .rightMouseDown,"wheel":event.getIntegerValueField(.scrollWheelEventDeltaAxis1)])}
 return Unmanaged.passUnretained(event)
}
let types:[CGEventType]=[.keyDown,.keyUp,.flagsChanged,.mouseMoved,.leftMouseDown,.leftMouseUp,.rightMouseDown,.rightMouseUp,.leftMouseDragged,.rightMouseDragged,.scrollWheel]
let mask:CGEventMask=types.reduce(0) { $0 | (CGEventMask(1)<<CGEventMask($1.rawValue)) }
final class Output:NSObject,SCStreamOutput,SCStreamDelegate {
 var count=0
 func stream(_ stream:SCStream,didStopWithError error:Error){emit(["type":"source_error","reason":"capture stopped"]);exit(5)}
 func stream(_ stream:SCStream,didOutputSampleBuffer sampleBuffer:CMSampleBuffer,of type:SCStreamOutputType){
  guard type == .screen,let buffer=CMSampleBufferGetImageBuffer(sampleBuffer) else{return}
  CVPixelBufferLockBaseAddress(buffer,.readOnly);defer{CVPixelBufferUnlockBaseAddress(buffer,.readOnly)}
  guard let base=CVPixelBufferGetBaseAddress(buffer) else{return};let stride=CVPixelBufferGetBytesPerRow(buffer),width=CVPixelBufferGetWidth(buffer),height=CVPixelBufferGetHeight(buffer)
  guard width==1280 && height==720 else{return}
  for y in 0..<height {FileHandle.standardOutput.write(Data(bytes:base.advanced(by:y*stride),count:width*4))}
  count += 1;emit(["type":"frame","frameId":count,"t":Double(DispatchTime.now().uptimeNanoseconds)/1e6])
 }
}
let output=Output();var stream:SCStream?;var lastWindow:CGWindowID=0
func update() async {
 do {
  let content=try await SCShareableContent.excludingDesktopWindows(true,onScreenWindowsOnly:true)
  if args.contains("--scratch-benchmark") {
   if stream != nil{return}
   guard let display=content.displays.first(where:{$0.displayID==CGMainDisplayID()}) else{throw NSError(domain:"screen",code:1)}
   let filter=SCContentFilter(display:display,excludingWindows:[])
   let cfg=SCStreamConfiguration();cfg.width=1280;cfg.height=720;cfg.pixelFormat=kCVPixelFormatType_32BGRA;cfg.minimumFrameInterval=CMTime(value:1,timescale:20);cfg.queueDepth=3;cfg.showsCursor=true;cfg.capturesAudio=false
   let next=SCStream(filter:filter,configuration:cfg,delegate:output);try next.addStreamOutput(output,type:.screen,sampleHandlerQueue:DispatchQueue(label:"glim.scratch.frames"));stream=next;try await next.startCapture();return
  }
  guard let front=NSWorkspace.shared.frontmostApplication,let window=content.windows.filter({$0.owningApplication?.processID==front.processIdentifier && $0.windowLayer==0 && $0.frame.width>10}).max(by:{$0.frame.width*$0.frame.height<$1.frame.width*$1.frame.height}) else{if let old=stream {try? await old.stopCapture();stream=nil};return}
  if window.windowID==lastWindow && stream != nil{return}
  let filter=SCContentFilter(desktopIndependentWindow:window)
  if let old=stream {try await old.updateContentFilter(filter)}else{
   let cfg=SCStreamConfiguration();cfg.width=1280;cfg.height=720;cfg.pixelFormat=kCVPixelFormatType_32BGRA;cfg.minimumFrameInterval=CMTime(value:1,timescale:20);cfg.queueDepth=3;cfg.showsCursor=true;cfg.capturesAudio=false
   let next=SCStream(filter:filter,configuration:cfg,delegate:output);try next.addStreamOutput(output,type:.screen,sampleHandlerQueue:DispatchQueue(label:"hands.recorder.frames"));stream=next;try await next.startCapture()
  };lastWindow=window.windowID
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
if args.contains("--scratch-benchmark") {_ = Timer.scheduledTimer(withTimeInterval:120,repeats:false){_ in exit(0)}}
if !CGPreflightScreenCaptureAccess() || !CGPreflightListenEventAccess() {fputs("capture/input permission missing; no permission prompt, no recording\n",stderr);exit(3)}
app.setActivationPolicy(.prohibited)
tap=CGEvent.tapCreate(tap:.cgSessionEventTap,place:.headInsertEventTap,options:.listenOnly,eventsOfInterest:mask,callback:callback,userInfo:nil)
guard let tap=tap else{exit(3)}
CFRunLoopAddSource(CFRunLoopGetMain(),CFMachPortCreateRunLoopSource(nil,tap,0),.commonModes);CGEvent.tapEnable(tap:tap,enable:true)
var updating=false
_ = Timer.scheduledTimer(withTimeInterval:0.25,repeats:true){_ in let secure=IsSecureEventInputEnabled();if secure != wasSecure {emit(["type":secure ? "secure_input_on":"secure_input_off","t":Double(DispatchTime.now().uptimeNanoseconds)/1e6]);wasSecure=secure};if !updating {updating=true;Task{await update();updating=false}}}
// Closing the parent pipe stops all capture, including after parent crash.
DispatchQueue.global().async {while readLine() != nil{};exit(0)}
app.run()

}
