'use strict';
// Choosing what to download: the llama.cpp release asset, the GGUF in the Hugging Face repo, python-build-standalone.
const C = require('./constants');

const tagNumber = (tag) => { const m = /(\d+)/.exec(String(tag || '')); return m ? Number(m[1]) : 0; };

/**
 * pickLlamaAsset(releases, {flavor, platform, minPublished, minTag}) -> {tag, name, url, size, sha256, published} | null
 * releases: GitHub API list (newest first or not: we sort). Skips drafts (llama.cpp marks every release a prerelease, so those are fine) and anything published before the LFM3 floor
 * date. Takes the newest release that has the wanted asset (llama-<tag>-bin-win-<flavor>-x64.zip, or on platform 'darwin'
 * llama-<tag>-bin-macos-arm64.tar.gz).
 */
function pickLlamaAsset(releases, o) {
  if (!Array.isArray(releases)) return null; // an API error object (rate limit) or garbage
  o = o || {};
  const platform = o.platform || 'win32';
  const flavor = o.flavor || (platform === 'darwin' ? 'metal' : 'vulkan');
  const floor = Date.parse(o.minPublished || C.LLAMA_MIN_PUBLISHED);
  const minTag = o.minTag == null ? C.LLAMA_MIN_TAG_NUMBER : o.minTag;
  const list = releases.filter((r) => r && !r.draft && Date.parse(r.published_at) >= floor && tagNumber(r.tag_name) >= minTag)
    .sort((a, b) => Date.parse(b.published_at) - Date.parse(a.published_at));
  for (const r of list) {
    const want = C.llamaAssetName(r.tag_name, flavor, platform);
    const a = (r.assets || []).find((x) => x.name === want);
    if (a) return { tag: r.tag_name, name: a.name, url: a.browser_download_url, size: a.size || 0, sha256: /^sha256:([0-9a-f]{64})$/i.test(a.digest || '') ? a.digest.slice(7).toLowerCase() : null, published: r.published_at };
  }
  return null;
}

/**
 * pickGguf(files, preferred) -> {path, size, sha256} | null. files: Hugging Face /api/models/<repo>/tree/main list.
 * The preferred exact name wins; otherwise the smallest .gguf whose name has q4_0 (case-insensitive) and no 'mmproj'.
 */
function pickGguf(files, preferred) {
  const ggufs = (files || []).filter((f) => f && f.type !== 'directory' && /\.gguf$/i.test(f.path || '') && !/mmproj/i.test(f.path));
  const pick = ggufs.find((f) => f.path === (preferred || C.MODEL_FILE)) || ggufs.filter((f) => /q4_0/i.test(f.path)).sort((a, b) => (a.size || 0) - (b.size || 0))[0];
  if (!pick) return null;
  return { path: pick.path, size: (pick.lfs && pick.lfs.size) || pick.size || 0, sha256: (pick.lfs && pick.lfs.oid) ? String(pick.lfs.oid).toLowerCase() : null };
}
const hfResolveUrl = (repo, file) => 'https://huggingface.co/' + repo + '/resolve/main/' + file.split('/').map(encodeURIComponent).join('/');
const hfTreeUrl = (repo) => 'https://huggingface.co/api/models/' + repo + '/tree/main';

// python-build-standalone: cpython-3.12.x+<date>-x86_64-pc-windows-msvc-install_only(_stripped).tar.gz in the newest release
function pickPython(releases, series) {
  series = series || C.PYTHON_SERIES;
  const re = new RegExp('^cpython-(' + series.replace('.', '\\.') + '\\.\\d+)\\+\\d+-x86_64-pc-windows-msvc-install_only\\.tar\\.gz$');
  for (const r of (releases || []).slice().sort((a, b) => Date.parse(b.published_at) - Date.parse(a.published_at))) {
    const hits = (r.assets || []).filter((a) => re.test(a.name)).sort((a, b) => b.name.localeCompare(a.name, 'en', { numeric: true }));
    if (hits[0]) return { name: hits[0].name, url: hits[0].browser_download_url, size: hits[0].size || 0, sha256: /^sha256:([0-9a-f]{64})$/i.test(hits[0].digest || '') ? hits[0].digest.slice(7).toLowerCase() : null, tag: r.tag_name };
  }
  return null;
}
const llamaSourceUrl = (tag) => 'https://github.com/' + C.LLAMA_REPO + '/archive/' + (/^[0-9a-f]{40}$/.test(tag) ? '' : 'refs/tags/') + tag + '.zip';

module.exports = { pickLlamaAsset, pickGguf, pickPython, hfResolveUrl, hfTreeUrl, llamaSourceUrl, tagNumber };
