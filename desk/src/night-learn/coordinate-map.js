'use strict';
const {displayPointToBacking,displayPointToVideo}=require('../screen-learning/display-map');
// CG events are global points. Subtract this display's point origin before
// multiplying by its backing scale. Then apply the recorder's compositor.
function coordinateMap(point,display,captureBounds,video) {
 const backingPixels=displayPointToBacking(point,display);
 const capturePoint={x:display.bounds.x+backingPixels.x/display.scaleX,y:display.bounds.y+backingPixels.y/display.scaleY};
 return {globalPoints:point,display,backingPixels,videoPixels:displayPointToVideo(capturePoint,captureBounds,video)};
}
module.exports={coordinateMap};
