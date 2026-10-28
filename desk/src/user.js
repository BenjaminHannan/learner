'use strict';
// Who the assistant works for. The app was written for Ben, so its prompt and messages say "Ben"; on anyone else's Mac (Emma's,
// Jacob's PC) that read as talking about a stranger. NAME comes from the computer account (PREMONITION_USER_NAME wins), fixed for
// the whole run so the cached prompt prefix stays byte-identical; P() rewrites the built-in texts for it.
const os = require('os');

function accountName() {
  if (process.env.PREMONITION_USER_NAME) return process.env.PREMONITION_USER_NAME;
  if (process.env.NODE_TEST_CONTEXT || process.argv.includes('--e2e')) return 'Ben'; // the tests are written for Ben's texts
  let full = '';
  if (process.platform === 'darwin') { try { full = require('child_process').execFileSync('/usr/bin/id', ['-F'], { timeout: 2000 }).toString().trim(); } catch (e) { /* below */ } }
  if (!full) { try { full = os.userInfo().username; } catch (e) { full = ''; } }
  return full;
}
// "ben-hannan" -> Ben, "Emma Parent" -> Emma, "admin" / "user" / "" -> the user
function firstName(full) {
  const w = String(full || '').split(/[\s._-]+/).find((x) => /^[A-Za-z][A-Za-z']{1,}$/.test(x));
  if (!w || /^(admin|administrator|user|owner|guest|mac|macbook|pc|home|student)$/i.test(w)) return 'the user';
  return w[0].toUpperCase() + w.slice(1).toLowerCase();
}
const NAME = firstName(accountName());

// Ben's texts for this user: names, then (for anyone but Ben) he/his/him -> they/their/them, since a name says nothing of pronouns
function P(s) {
  s = String(s);
  if (NAME === 'Ben') return s;
  return s.replace(/\bBen's\b/g, NAME + "'s").replace(/\bBen\b/g, NAME)
    .replace(/\bhis\b/g, 'their').replace(/\bHis\b/g, 'Their').replace(/\bhimself\b/g, 'themselves').replace(/\bhim\b/g, 'them').replace(/\bhe\b/g, 'they').replace(/\bHe\b/g, 'They');
}

module.exports = { NAME, P, firstName };
