'use strict';
// Tool-use details (the step list under "Glim is working") fold all together: one choice for every thread and message.
// Pure helpers so the stored value and the body attribute are testable in node.
(function (root) {
  const KEY = 'actsCollapsed';
  const parse = (stored) => stored === '1' || stored === 'true';        // anything else (null, junk) = expanded
  const attr = (collapsed) => (collapsed ? 'closed' : 'open');          // value of body[data-acts]
  const isCollapsed = (bodyAttr) => bodyAttr === 'closed';
  const api = { KEY, parse, attr, isCollapsed };
  root.Acts = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
