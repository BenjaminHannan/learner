'use strict';

// Match the recorder's full-display compositor: it fits the union of display
// bounds into a 1280x720 image and centers it, preserving aspect ratio.
function displayPointToVideo(point, bounds, video = { width: 1280, height: 720 }) {
  for (const [object, fields] of [[point, ['x', 'y']], [bounds, ['x', 'y', 'width', 'height']], [video, ['width', 'height']]]) {
    if (!object || fields.some(field => !Number.isFinite(object[field]))) throw Error('invalid display geometry');
  }
  if (bounds.width <= 0 || bounds.height <= 0 || video.width <= 0 || video.height <= 0) throw Error('invalid display size');
  if (point.x < bounds.x || point.y < bounds.y || point.x >= bounds.x + bounds.width || point.y >= bounds.y + bounds.height) throw Error('point outside captured bounds');
  const scale = Math.min(video.width / bounds.width, video.height / bounds.height);
  return { x: (video.width - bounds.width * scale) / 2 + (point.x - bounds.x) * scale,
    y: (video.height - bounds.height * scale) / 2 + (point.y - bounds.y) * scale };
}
// Backing pixels on one physical display. CG bounds and event locations are
// global points; scale converts the offset from the display origin to pixels.
function displayPointToBacking(point, display) {
  if (!display || !Number.isFinite(display.scaleX) || !Number.isFinite(display.scaleY) || display.scaleX <= 0 || display.scaleY <= 0) throw Error('invalid backing scale');
  const local = displayPointToVideo(point, display.bounds, {width:display.bounds.width, height:display.bounds.height});
  return {x:local.x * display.scaleX, y:local.y * display.scaleY};
}
module.exports = { displayPointToVideo, displayPointToBacking };
