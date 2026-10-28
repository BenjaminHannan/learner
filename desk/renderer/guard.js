'use strict';
// Composer guard: warn before a password or one-time code goes into the chat. Works in the page and in node (tests).
(function (root) {
  const PASSWORD = /\b(password|passwd|passcode|pass\s?word|pwd|pw)\b(\s+for\s+[\w.@-]+)?\s*(=|:|\bis\b|\bwas\b)/i;
  const CODE = /\b(verification|security|2fa|otp|login|sign.?in|one.?time)\s+(code|pin)\b[^.\n]{0,15}?(\bis\b|=|:)\s*\d{4,8}/i;
  const looksLikeSecret = (text) => PASSWORD.test(String(text || '')) || CODE.test(String(text || ''));
  const api = { looksLikeSecret };
  root.Guard = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
