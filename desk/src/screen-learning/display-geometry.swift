// Read display geometry only. No screen pixels or input events are accessed.
import AppKit
import CoreGraphics
import Foundation
let rows:[[String:Any]] = NSScreen.screens.compactMap { screen in
    guard let number = screen.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber else { return nil }
    let id = CGDirectDisplayID(number.uint32Value)
    let rect = CGDisplayBounds(id)
    return ["id":id, "bounds":["x":rect.origin.x,"y":rect.origin.y,"width":rect.width,"height":rect.height],
            "scaleX":screen.backingScaleFactor,"scaleY":screen.backingScaleFactor]
}
guard !rows.isEmpty else { fputs("No display geometry available\n",stderr); exit(1) }
let data = try JSONSerialization.data(withJSONObject:rows, options:[.sortedKeys])
print(String(data:data,encoding:.utf8)!)
