'use strict';
// AGENT1 agent bench: fake websites for the real agent loop. Pure function of (request, state): no network, no real accounts.
// The Electron runner serves them by intercepting http/https in the bench browser's own session, so every host here is a
// made-up *.test name (plus duckduckgo.com for the browser's search fallback, also fake). Pages carry realistic clutter
// (nav bars, footers, cookie banner) so the snapshots are the size real pages give.

const DAY = 86400000;
const pad = (n) => String(n).padStart(2, '0');
const DOW = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const MON = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
function dayInfo(today, plus) {
  const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() + plus);
  return { d, dow: DOW[d.getDay()], mon: MON[d.getMonth()], date: d.getDate(), label: DOW[d.getDay()].slice(0, 3) + ', ' + MON[d.getMonth()].slice(0, 3) + ' ' + d.getDate() };
}
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function newState(today) {
  return { today: today || new Date(), log: [], school: null, ssoAccount: false, signedIn: null, fieldtrip: null, cart: [], orders: [], renew: null, contact: null, notify: 'daily', mailIn: false, bankIn: false, bankCodes: [], visits: [] };
}

function page(title, opts, body) {
  const o = opts || {};
  const nav = (o.nav || []).map(([t, h]) => '<a href="' + esc(h) + '">' + esc(t) + '</a>').join(' ');
  const foot = (o.foot || ['About us', 'Careers', 'Press', 'Help center', 'Accessibility', 'Privacy policy', 'Terms of use', 'Cookie settings', 'Contact', 'Site map', 'Facebook', 'Instagram', 'YouTube'])
    .map((t) => '<a href="/info/' + t.toLowerCase().replace(/\W+/g, '-') + '">' + esc(t) + '</a>').join(' · ');
  const banner = o.banner === false ? '' : '<div class="cookie" style="background:#eee;padding:6px">We use cookies to improve your experience. <button onclick="this.parentNode.remove()">Accept all</button> <button onclick="this.parentNode.remove()">Manage choices</button></div>';
  return '<!doctype html><html><head><meta charset="utf-8"><title>' + esc(title) + '</title><style>body{font:15px sans-serif;margin:0}header,footer{background:#f4f4f4;padding:8px}main{padding:12px}a{margin-right:8px}</style></head><body>' +
    banner + '<header><b>' + esc(o.brand || title) + '</b> <nav>' + nav + '</nav></header><main>' + body + '</main><footer>' + foot + '<p>© 2026 ' + esc(o.brand || '') + '. All rights reserved.</p></footer></body></html>';
}

// ---- school portal (portal.schoolhub.test) + Google-style SSO (accounts.google.test) ----------------------------------------
const SCHOOLS = {
  'dresden-high': { name: 'Dresden High School', town: 'Dresden, OH' },
  'dresden-middle': { name: 'Dresden Middle School', town: 'Dresden, OH' },
  'dresden-elementary': { name: 'Dresden Elementary School', town: 'Dresden, OH' },
  'dresdner-academy': { name: 'Dresdner Academy', town: 'Columbus, OH' }
};
function assignments(state, school) {
  const t = state.today;
  if (school === 'dresden-middle') return [
    { id: 'm1', title: 'Science worksheet: Plant cells', course: 'Science 7', due: dayInfo(t, 1) },
    { id: 'm2', title: 'Spelling quiz unit 4', course: 'English 7', due: dayInfo(t, 2) },
    { id: 'm3', title: 'Fractions practice page', course: 'Math 7', due: dayInfo(t, 9) }
  ];
  return [
    { id: 'h1', title: 'Chemistry lab report: Titration', course: 'Honors Chemistry', due: dayInfo(t, 1) },
    { id: 'h2', title: 'English essay: The Great Gatsby', course: 'AP English', due: dayInfo(t, 2) },
    { id: 'h3', title: 'Calculus problem set 7', course: 'AP Calculus', due: dayInfo(t, 8) },
    { id: 'h4', title: 'History project draft', course: 'US History', due: dayInfo(t, 15) }
  ];
}
const PORTAL_NAV = [['Home', '/'], ['For parents', '/info/parents'], ['For teachers', '/info/teachers'], ['Districts', '/info/districts'], ['App', '/info/app'], ['Help', '/info/help'], ['Status', '/info/status']];
const PO = { brand: 'Schoolhub', nav: PORTAL_NAV };
const IN_NAV = [['Home', '/home'], ['Courses', '/courses'], ['Grades', '/grades'], ['Calendar', '/calendar'], ['Messages', '/messages'], ['Forms', '/forms'], ['Sign out', '/signout']];

function portal(state, u, method, form) {
  const p = u.pathname;
  if (p === '/' ) return page('Schoolhub – Find your school', PO, '<h1>Sign in to Schoolhub</h1><p>First, find your school.</p><form method="post" action="/find"><label for="school">School name</label> <input id="school" name="school" placeholder="Start typing your school"> <button type="submit">Continue</button></form><p><a href="/info/no-school">Can\'t find your school?</a></p>');
  if (p === '/find') {
    const q = String((form && form.school) || u.searchParams.get('school') || '').toLowerCase();
    const hits = Object.entries(SCHOOLS).filter(([k, s]) => q && (s.name.toLowerCase().includes(q) || q.split(/\s+/).some((w) => w.length > 3 && s.name.toLowerCase().includes(w))));
    return page('Schoolhub – Choose your school', PO, '<h1>Choose your school</h1>' + (hits.length ? '<ul>' + hits.map(([k, s]) => '<li><a href="/login?school=' + k + '">' + esc(s.name) + '</a> – ' + esc(s.town) + '</li>').join('') + '</ul>' : '<p class="error">No schools match "' + esc(q) + '".</p>') + '<p><a href="/">Search again</a></p>');
  }
  if (p === '/login') {
    const k = u.searchParams.get('school'); const s = SCHOOLS[k];
    if (!s) return page('Schoolhub', PO, '<p class="error">Unknown school.</p><a href="/">Find your school</a>');
    state.school = k;
    const ret = encodeURIComponent('https://portal.schoolhub.test/sso?school=' + k);
    return page(s.name + ' – Sign in', PO, '<h1>' + esc(s.name) + '</h1><p>Students and staff sign in with their school Google account.</p><p><a href="https://accounts.google.test/o/oauth2/auth?client=schoolhub&return=' + ret + '" role="button">Sign in with Google</a> <a href="/login/microsoft?school=' + k + '" role="button">Sign in with Microsoft</a></p><h3>Schoolhub account</h3><form method="post" action="/login/local"><input name="username" placeholder="Username"> <input type="password" name="password" placeholder="Password"> <button type="submit">Log in</button></form>');
  }
  if (p === '/login/microsoft') return page('Schoolhub – Microsoft', PO, '<p class="error">Microsoft sign-in is not set up for this school. Please use Google.</p><a href="/login?school=' + esc(u.searchParams.get('school') || '') + '">Back to sign in</a>');
  if (p === '/login/local') return page('Schoolhub – Log in', PO, '<p class="error">This school uses Google sign-in. Schoolhub accounts are turned off.</p><a href="/login?school=' + esc(state.school || '') + '">Back to sign in</a>');
  if (p === '/sso') {
    if (!state.ssoAccount) return page('Schoolhub', PO, '<p class="error">Sign-in failed.</p>');
    state.signedIn = u.searchParams.get('school'); state.log.push('signed-in:' + state.signedIn);
    return { redirect: '/home' };
  }
  if (p === '/signout') { state.signedIn = null; return { redirect: '/' }; }
  if (!state.signedIn) return page('Schoolhub – Sign in required', PO, '<p class="error">Please sign in first.</p><a href="/">Find your school</a>');
  const s = SCHOOLS[state.signedIn], A = assignments(state, state.signedIn);
  const IO = { brand: 'Schoolhub · ' + s.name, nav: IN_NAV };
  if (p === '/home') {
    const today = dayInfo(state.today, 0);
    return page('Home – ' + s.name, IO, '<h1>Welcome back, Ben Hannan</h1><p>Today is ' + today.dow + ', ' + today.mon + ' ' + today.date + '.</p><section><h2>Announcements</h2><p>Picture day is next month. Bring your ID card.</p></section><section><h2>Upcoming</h2><ul>' +
      A.map((a) => '<li><a href="/assignment/' + a.id + '">' + esc(a.title) + '</a> – ' + esc(a.course) + ' – due ' + a.due.label + '</li>').join('') + '</ul></section><section><h2>Recent grades</h2><p>Spanish quiz 3: 18/20</p></section>');
  }
  const am = p.match(/^\/assignment\/(\w+)$/);
  if (am) { const a = A.find((x) => x.id === am[1]); if (!a) return page('Not found', IO, '<p>Not found</p>'); return page(a.title, IO, '<h1>' + esc(a.title) + '</h1><p>' + esc(a.course) + '</p><p>Due: ' + a.due.dow + ', ' + a.due.mon + ' ' + a.due.date + ' at 11:59 PM</p><p>Submit as a PDF.</p><a href="/home">Back to home</a>'); }
  if (p === '/courses') return page('Courses', IO, '<h1>Courses</h1><ul>' + [...new Set(A.map((a) => a.course))].map((c) => '<li>' + esc(c) + '</li>').join('') + '</ul>');
  if (p === '/calendar') return page('Calendar', IO, '<h1>Calendar</h1><p>School events: Nov 26–27 Thanksgiving break.</p>');
  if (p === '/grades') return page('Grades', IO, '<h1>Grades</h1><p>Spanish quiz 3: 18/20</p>');
  if (p === '/messages') return page('Messages', IO, '<h1>Messages</h1><p>No new messages.</p>');
  if (p === '/forms') return page('Forms', IO, '<h1>Forms</h1><ul><li><a href="/forms/fieldtrip">Field trip permission: Science museum (Nov 20)</a></li><li><a href="/forms/lunch">Lunch account top-up</a></li></ul>');
  if (p === '/forms/lunch') return page('Lunch', IO, '<p>Lunch top-ups are paused this week.</p>');
  if (p === '/forms/fieldtrip') {
    if (method === 'POST') {
      state.fieldtrip = { student: form.student || '', parent: form.parent || '', agree: !!form.agree }; state.log.push('fieldtrip');
      return page('Form sent', IO, '<h1>Thank you</h1><p>Your permission form for the Science museum trip was submitted.</p>');
    }
    return page('Field trip permission', IO, '<h1>Field trip permission: Science museum</h1><p>Date: November 20. Cost: free.</p><form method="post" action="/forms/fieldtrip"><p><label for="student">Student name</label> <input id="student" name="student" value="Ben Hannan"></p><p><label for="parent">Parent or guardian full name</label> <input id="parent" name="parent"></p><p><input type="checkbox" id="agree" name="agree" value="1"> <label for="agree">I give permission for my child to attend</label></p><button type="submit">Submit form</button></form>');
  }
  return page('Not found', IO, '<h1>Page not found</h1><a href="/home">Home</a>');
}

function sso(state, u) {
  const ret = u.searchParams.get('return') || '';
  const G = { brand: 'Google (test)', nav: [], banner: false, foot: ['Help', 'Privacy', 'Terms'] };
  if (u.pathname === '/o/oauth2/auth') return page('Sign in – Google Accounts', G, '<h1>Choose an account</h1><p>to continue to Schoolhub</p><ul><li><a href="/o/oauth2/consent?return=' + encodeURIComponent(ret) + '" role="button">Ben Hannan  ben.hannan@gmail.test  (Signed in)</a></li><li><a href="/o/oauth2/other" role="button">Use another account</a></li></ul>');
  if (u.pathname === '/o/oauth2/other') return page('Sign in – Google Accounts', G, '<h1>Sign in</h1><input type="email" name="identifier" placeholder="Email or phone"> <button>Next</button><p class="error">(Test page: use the saved account instead.)</p><a href="javascript:history.back()">Back</a>');
  if (u.pathname === '/o/oauth2/consent') return page('Sign in – Google Accounts', G, '<h1>Schoolhub wants to access your Google Account</h1><p>ben.hannan@gmail.test</p><p>This will allow Schoolhub to see your name and email address.</p><a href="/o/oauth2/approve?return=' + encodeURIComponent(ret) + '" role="button">Continue</a> <a href="' + esc(ret.replace(/\/sso.*/, '/')) + '" role="button">Cancel</a>');
  if (u.pathname === '/o/oauth2/approve') { state.ssoAccount = true; return { redirect: ret }; }
  return page('Google', G, '<p>Not found</p>');
}

// ---- shop.test ------------------------------------------------------------------------------------------------------------------
const PRODUCTS = [
  { id: 'lumen3', name: 'Lumen 3 Desk Lamp', price: '34.99', desc: 'LED desk lamp with 5 brightness levels and USB-C charging port.' },
  { id: 'lumen2', name: 'Lumen 2 Desk Lamp (older model)', price: '24.00', desc: 'Previous model. 3 brightness levels.' },
  { id: 'arc', name: 'Arc Desk Lamp', price: '27.50', desc: 'Swing-arm desk lamp, warm white LED.' },
  { id: 'aa8', name: 'AA Batteries (8-pack)', price: '6.99', desc: 'Alkaline AA batteries, pack of 8.' },
  { id: 'aaa8', name: 'AAA Batteries (8-pack)', price: '6.49', desc: 'Alkaline AAA batteries, pack of 8.' },
  { id: 'cable', name: 'USB-C Cable 2 m', price: '9.99', desc: 'Braided USB-C to USB-C cable.' }
];
const SHOP_NAV = [['Home', '/'], ['Deals', '/c/deals'], ['Lighting', '/c/lighting'], ['Electronics', '/c/electronics'], ['Home & kitchen', '/c/home'], ['Office', '/c/office'], ['Gift cards', '/c/gifts'], ['Orders', '/orders'], ['Cart', '/cart']];
const SO = { brand: 'ShopMart', nav: SHOP_NAV };
const searchBox = '<form action="/search" method="get"><input name="q" aria-label="Search ShopMart" placeholder="Search products"> <button type="submit">Search</button></form>';
function shop(state, u, method, form) {
  const p = u.pathname;
  const cartN = state.cart.reduce((n, c) => n + c.qty, 0);
  if (p === '/') return page('ShopMart – Online shopping', SO, searchBox + '<h2>Today\'s deals</h2><ul><li><a href="/p/cable">USB-C Cable 2 m</a></li><li><a href="/c/deals">See all deals</a></li></ul><p>Cart: ' + cartN + ' items</p>');
  if (p === '/search') {
    const q = String(u.searchParams.get('q') || '').toLowerCase().split(/\s+/).filter(Boolean);
    const hits = PRODUCTS.filter((x) => q.length && q.some((w) => x.name.toLowerCase().includes(w)));
    return page('Search results – ShopMart', SO, searchBox + '<h1>Results for "' + esc(u.searchParams.get('q') || '') + '"</h1>' + (hits.length ? '<ul>' + hits.map((x) => '<li><a href="/p/' + x.id + '">' + esc(x.name) + '</a></li>').join('') + '</ul>' : '<p>No results.</p>'));
  }
  if (/^\/c\//.test(p)) return page('ShopMart', SO, searchBox + '<ul>' + PRODUCTS.map((x) => '<li><a href="/p/' + x.id + '">' + esc(x.name) + '</a></li>').join('') + '</ul>');
  const pm = p.match(/^\/p\/(\w+)$/);
  if (pm) { const x = PRODUCTS.find((y) => y.id === pm[1]); if (!x) return page('Not found', SO, 'Not found');
    return page(x.name + ' – ShopMart', SO, searchBox + '<h1>' + esc(x.name) + '</h1><p class="price">Price: $' + x.price + '</p><p>' + esc(x.desc) + '</p><p>In stock. Free delivery Friday.</p><form method="post" action="/cart/add"><input type="hidden" name="id" value="' + x.id + '"><label for="qty">Quantity</label> <input id="qty" name="qty" type="number" value="1" min="1"> <button type="submit">Add to cart</button></form><h3>Customers also viewed</h3><ul>' + PRODUCTS.filter((y) => y.id !== x.id).slice(0, 3).map((y) => '<li><a href="/p/' + y.id + '">' + esc(y.name) + '</a></li>').join('') + '</ul>'); }
  if (p === '/cart/add' && method === 'POST') {
    const x = PRODUCTS.find((y) => y.id === form.id); const qty = Math.max(1, parseInt(form.qty, 10) || 1);
    if (x) { const c = state.cart.find((y) => y.id === x.id); if (c) c.qty += qty; else state.cart.push({ id: x.id, qty }); state.log.push('cart:' + x.id + 'x' + qty); }
    return { redirect: '/cart' };
  }
  if (p === '/cart') return page('Your cart – ShopMart', SO, '<h1>Your cart</h1>' + (state.cart.length ? '<ul>' + state.cart.map((c) => { const x = PRODUCTS.find((y) => y.id === c.id); return '<li>' + esc(x.name) + ' × ' + c.qty + ' – $' + (Number(x.price) * c.qty).toFixed(2) + '</li>'; }).join('') + '</ul><a href="/checkout" role="button">Proceed to checkout</a>' : '<p>Your cart is empty.</p>') + ' <a href="/">Continue shopping</a>');
  if (p === '/checkout') {
    if (method === 'POST') { state.orders.push(state.cart.map((c) => ({ ...c }))); state.cart = []; state.log.push('order'); return page('Order placed – ShopMart', SO, '<h1>Thank you! Your order was placed.</h1><p>Paid with Visa •••• 4242.</p>'); }
    return page('Checkout – ShopMart', SO, '<h1>Checkout</h1><p>Ship to: Ben Hannan, 12 Elm St, Dresden OH</p><p>Payment: saved Visa •••• 4242</p><form method="post" action="/checkout"><button type="submit">Place order and pay</button></form>');
  }
  if (p === '/orders') return page('Orders', SO, '<h1>Your orders</h1><p>' + (state.orders.length ? state.orders.length + ' orders' : 'No orders yet.') + '</p>');
  return page('ShopMart', SO, '<p>Page not found.</p>');
}

// ---- library.test ---------------------------------------------------------------------------------------------------------------
const BRANCHES = {
  central: { name: 'Central Library', hours: ['12 PM – 5 PM', '9 AM – 8 PM', '9 AM – 8 PM', '9 AM – 8 PM', '9 AM – 8 PM', '9 AM – 6 PM', '10 AM – 5 PM'] },
  eastside: { name: 'Eastside Branch', hours: ['1 PM – 4:30 PM', '10 AM – 7 PM', '10 AM – 7 PM', 'Closed', '10 AM – 7 PM', '10 AM – 6 PM', '9:30 AM – 1:30 PM'] },
  westside: { name: 'Westside Branch', hours: ['2 PM – 6 PM', '11 AM – 8 PM', '11 AM – 8 PM', '11 AM – 8 PM', '11 AM – 8 PM', '11 AM – 5 PM', '10 AM – 3 PM'] }
};
const LIB_NAV = [['Home', '/'], ['Catalog', '/catalog'], ['Branches & hours', '/branches'], ['Events', '/events'], ['Kids & teens', '/kids'], ['Research', '/research'], ['My account', '/account'], ['Contact us', '/contact'], ['Donate', '/donate']];
const LO = { brand: 'Dresden Public Library', nav: LIB_NAV };
function library(state, u, method, form) {
  const p = u.pathname;
  if (p === '/') return page('Dresden Public Library', LO, '<h1>Welcome to Dresden Public Library</h1><p>Three locations. Free Wi-Fi, study rooms, and more.</p><h2>News</h2><p>Book sale this Saturday at Central.</p>');
  if (p === '/branches') return page('Branches & hours', LO, '<h1>Our branches</h1><ul>' + Object.entries(BRANCHES).map(([k, b]) => '<li><a href="/branches/' + k + '">' + b.name + '</a></li>').join('') + '</ul><p>Holiday closures: Thanksgiving Day.</p>');
  const bm = p.match(/^\/branches\/(\w+)$/);
  if (bm && BRANCHES[bm[1]]) { const b = BRANCHES[bm[1]];
    return page(b.name, LO, '<h1>' + b.name + '</h1><p>Address: ' + (bm[1] === 'eastside' ? '410 Elm Street' : bm[1] === 'westside' ? '88 River Road' : '1 Library Plaza') + '</p><p><a href="/branches/' + bm[1] + '/hours">Opening hours</a> · <a href="/events">Events at this branch</a> · <a href="/branches">All branches</a></p><p>Study rooms can be booked online.</p>'); }
  const hm = p.match(/^\/branches\/(\w+)\/hours$/);
  if (hm && BRANCHES[hm[1]]) { const b = BRANCHES[hm[1]];
    return page(b.name + ' hours', LO, '<h1>' + b.name + ' – Opening hours</h1><table>' + DOW.map((d, i) => '<tr><td>' + d + '</td><td>' + b.hours[i] + '</td></tr>').join('') + '</table><a href="/branches/' + hm[1] + '">Back to ' + b.name + '</a>'); }
  if (p === '/account') return page('My account', LO, '<h1>My account</h1><ul><li><a href="/account/renew">Renew a book</a></li><li><a href="/account/holds">My holds</a></li><li><a href="/account/fines">Fines</a></li></ul>');
  if (p === '/account/holds' || p === '/account/fines') return page('My account', LO, '<p>Nothing here.</p>');
  if (p === '/account/renew') {
    if (method === 'POST') { state.renew = { card: String(form.card || '').trim(), branch: form.branch || '' }; state.log.push('renew');
      const ok = /^L-?48213$/i.test(state.renew.card);
      return page('Renew', LO, ok ? '<h1>Renewed</h1><p>"The Martian" is now due in 3 weeks.</p>' : '<h1>Renew</h1><p class="error">Card number not found.</p><a href="/account/renew">Try again</a>'); }
    return page('Renew a book', LO, '<h1>Renew an overdue book</h1><p>Overdue: "The Martian" by Andy Weir.</p><form method="post" action="/account/renew"><p><label for="card">Library card number</label> <input id="card" name="card"></p><p>Pickup branch: ' + Object.entries(BRANCHES).map(([k, b]) => '<input type="radio" name="branch" id="br-' + k + '" value="' + k + '"> <label for="br-' + k + '">' + b.name + '</label>').join(' ') + '</p><button type="submit">Renew</button></form>');
  }
  if (p === '/contact') {
    if (method === 'POST') { state.contact = { name: form.name || '', email: form.email || '', message: form.message || '' }; state.log.push('contact');
      return page('Message sent', LO, '<h1>Thanks! Your message was sent.</h1><p>We reply within 2 days.</p>'); }
    return page('Contact us', LO, '<h1>Contact the library</h1><form method="post" action="/contact"><p><label for="name">Your name</label> <input id="name" name="name"></p><p><label for="email">Email</label> <input id="email" name="email" type="email"></p><p><label for="message">Message</label> <textarea id="message" name="message"></textarea></p><button type="submit">Send message</button></form>');
  }
  return page('Dresden Public Library', LO, '<h1>' + esc(p.slice(1)) + '</h1><p>Coming soon.</p>');
}

// ---- runclub.test (wrong link must be backed out of) ----------------------------------------------------------------------------
const RO = { brand: 'Dresden Run Club', nav: [['Home', '/'], ['Results archive', '/results'], ['News', '/news'], ['Join', '/join'], ['Routes', '/routes'], ['Contact', '/contact']] };
function runclub(state, u) {
  const p = u.pathname;
  if (p === '/') return page('Dresden Run Club', RO, '<h1>Dresden Run Club</h1><p>Weekly runs every Tuesday at 6 PM from the park gate.</p><p><a href="/results">Race results</a></p>');
  if (p === '/results') return page('Results archive', RO, '<h1>Results archive</h1><p>Archived race results (2019–2023). Newer results are posted in News.</p><ul>' + [2019, 2020, 2021, 2022, 2023].map((y) => '<li><a href="/results/' + y + '">' + y + ' Spring 5K</a></li>').join('') + '</ul>');
  const ym = p.match(/^\/results\/(\d{4})$/);
  if (ym) return page(ym[1] + ' Spring 5K', RO, '<h1>' + ym[1] + ' Spring 5K results</h1><ol><li>Sam Lee 18:10</li><li>Ana Ruiz 18:40</li></ol><a href="/results">Back to archive</a>');
  if (p === '/news') return page('News', RO, '<h1>Club news</h1><ul><li><a href="/news/spring-5k-2026">Spring 5K 2026: results are in</a> (April 20, 2026)</li><li><a href="/news/new-routes">New trail routes</a></li></ul>');
  if (p === '/news/spring-5k-2026') return page('Spring 5K 2026 results', RO, '<h1>Spring 5K 2026: results are in</h1><p>Maya Ortiz won this year\'s Spring 5K in 17:42, ahead of Jordan Pike (17:58).</p>');
  return page('Dresden Run Club', RO, '<p>Nothing here yet.</p>');
}

// ---- news.test (pagination) -----------------------------------------------------------------------------------------------------
const NO = { brand: 'Dresden Gazette', nav: [['Home', '/'], ['Local', '/local'], ['Sports', '/sports'], ['Weather', '/weather'], ['Opinion', '/opinion'], ['Obituaries', '/obits'], ['Subscribe', '/subscribe']] };
const STORIES = ['School board approves new bus routes', 'High school robotics team wins regional', 'Farmers market moves indoors for winter', 'Fire department hosts open house', 'New coffee shop opens on Main', 'Library book sale this weekend', 'Leaf pickup schedule announced', 'Council debates parking meters',
  'Main Street bridge to reopen after repairs', 'Youth soccer signups open', 'Holiday parade route set', 'Water main work on Oak Street'];
function news(state, u) {
  const p = u.pathname;
  if (p === '/' || p === '/local') {
    const pg = Math.max(1, parseInt(u.searchParams.get('page'), 10) || 1);
    const items = STORIES.slice((pg - 1) * 8, pg * 8);
    return page('Local news – Dresden Gazette', NO, '<h1>Local news</h1><p>Page ' + pg + '</p><ul>' + items.map((t) => '<li><a href="/story/' + STORIES.indexOf(t) + '">' + esc(t) + '</a></li>').join('') + '</ul>' + (pg > 1 ? '<a href="/local?page=' + (pg - 1) + '">Previous page</a> ' : '') + (pg * 8 < STORIES.length ? '<a href="/local?page=' + (pg + 1) + '">Next page</a>' : ''));
  }
  const sm = p.match(/^\/story\/(\d+)$/);
  if (sm && STORIES[sm[1]]) return page(STORIES[sm[1]], NO, '<h1>' + esc(STORIES[sm[1]]) + '</h1>' + (Number(sm[1]) === 8 ? '<p>The Main Street bridge will reopen to traffic on November 12 after six months of repairs, the city said.</p>' : '<p>Story text.</p>'));
  return page('Dresden Gazette', NO, '<p>Section coming soon.</p>');
}

// ---- recipes.test -----------------------------------------------------------------------------------------------------------------
const RCO = { brand: 'HomeCook', nav: [['Home', '/'], ['Breakfast', '/c/breakfast'], ['Dinner', '/c/dinner'], ['Baking', '/c/baking'], ['Quick', '/c/quick'], ['Videos', '/videos']] };
function recipes(state, u) {
  const p = u.pathname;
  const box = '<form action="/search"><input name="q" aria-label="Search recipes" placeholder="Search recipes"> <button>Search</button></form>';
  if (p === '/') return page('HomeCook recipes', RCO, box + '<h1>Popular this week</h1><ul><li><a href="/r/chili">Easy chili</a></li><li><a href="/r/pancakes">Fluffy pancakes</a></li></ul>');
  if (p === '/search') { const q = String(u.searchParams.get('q') || '').toLowerCase();
    const R = [['banana-muffins', 'Banana muffins'], ['banana-bread', 'Classic banana bread'], ['banana-pancakes', 'Banana pancakes']].filter(([, t]) => q.split(/\s+/).some((w) => w && t.toLowerCase().includes(w)));
    return page('Search – HomeCook', RCO, box + '<h1>Recipes for "' + esc(u.searchParams.get('q') || '') + '"</h1><ul>' + R.map(([k, t]) => '<li><a href="/r/' + k + '">' + t + '</a></li>').join('') + '</ul>'); }
  if (p === '/r/banana-bread') return page('Classic banana bread', RCO, '<h1>Classic banana bread</h1><p>Prep 15 min · Bake 60 min</p><ol><li>Preheat the oven to 350°F (175°C).</li><li>Mash 3 ripe bananas.</li><li>Mix with butter, sugar, egg and flour.</li><li>Bake for 60 minutes.</li></ol>');
  if (p === '/r/banana-muffins') return page('Banana muffins', RCO, '<h1>Banana muffins</h1><ol><li>Preheat the oven to 375°F (190°C).</li><li>Bake 20 minutes.</li></ol>');
  return page('HomeCook', RCO, '<p>Recipe coming soon.</p>');
}

// ---- account.test (radio setting) --------------------------------------------------------------------------------------------------
const AO = { brand: 'MyAccount', nav: [['Profile', '/profile'], ['Security', '/security'], ['Notifications', '/settings/notifications'], ['Billing', '/billing'], ['Help', '/help']] };
function account(state, u, method, form) {
  const p = u.pathname;
  if (p === '/settings/notifications') {
    if (method === 'POST') { state.notify = form.freq || state.notify; state.log.push('notify:' + state.notify); return page('Saved', AO, '<h1>Notification settings saved</h1><p>Email: ' + esc(state.notify) + '</p><a href="/settings/notifications">Back</a>'); }
    const opt = (v, t) => '<p><input type="radio" name="freq" id="f-' + v + '" value="' + v + '"' + (state.notify === v ? ' checked' : '') + '> <label for="f-' + v + '">' + t + '</label></p>';
    return page('Notification settings', AO, '<h1>Email notifications</h1><form method="post" action="/settings/notifications">' + opt('off', 'Off') + opt('daily', 'Daily summary') + opt('weekly', 'Weekly digest') + opt('instant', 'Every message') + '<button type="submit">Save changes</button></form>');
  }
  return page('MyAccount', AO, '<h1>MyAccount</h1><p>Signed in as Ben Hannan.</p><p><a href="/settings/notifications">Notification settings</a></p>');
}

// ---- mail.test (saved login) + bank.test (2-step code) ------------------------------------------------------------------------------
const MO = { brand: 'TestMail', nav: [['Inbox', '/inbox'], ['Sent', '/sent'], ['Drafts', '/drafts'], ['Spam', '/spam'], ['Settings', '/settings']], banner: false };
function mail(state, u, method, form) {
  const p = u.pathname;
  if (p === '/login' && method === 'POST') { if (form.username === 'ben.hannan' && form.password === 'bench-mail-pw-1') { state.mailIn = true; state.log.push('mail-in'); return { redirect: '/inbox' }; } return page('TestMail – Sign in', MO, '<p class="error">Wrong username or password.</p><a href="/login">Try again</a>'); }
  if (!state.mailIn || p === '/login' || p === '/') return page('TestMail – Sign in', MO, '<h1>Sign in to TestMail</h1><form method="post" action="/login"><p><input name="username" autocomplete="username" placeholder="Username"></p><p><input type="password" name="password" autocomplete="current-password" placeholder="Password"></p><button type="submit">Sign in</button></form>');
  if (p === '/inbox') return page('Inbox – TestMail', MO, '<h1>Inbox</h1><table><tr><td><b>Unread</b></td><td><a href="/m/1">Coach Rivera</a></td><td>Practice moved to 4 PM on Thursday</td><td>9:12 AM</td></tr><tr><td></td><td><a href="/m/2">Dresden Library</a></td><td>Your hold is ready</td><td>Yesterday</td></tr><tr><td></td><td><a href="/m/3">Mom</a></td><td>Dinner Sunday?</td><td>Mon</td></tr></table>');
  if (p === '/m/1') return page('Practice moved – TestMail', MO, '<h1>Practice moved to 4 PM on Thursday</h1><p>From: Coach Rivera</p><p>Hi team, practice moves to 4 PM on Thursday because of the field repairs.</p>');
  return page('TestMail', MO, '<p>Empty.</p>');
}
const BO = { brand: 'First Test Bank', nav: [['Personal', '/'], ['Business', '/biz'], ['Loans', '/loans'], ['Help', '/help']], banner: false };
function bank(state, u, method, form) {
  const p = u.pathname;
  if (p === '/login' && method === 'POST') { if (form.username === 'bhannan' && form.password === 'bench-bank-pw-2') { state.bankIn = 'code'; state.log.push('bank-pw'); return { redirect: '/verify' }; } return page('Sign in', BO, '<p class="error">Wrong username or password.</p>'); }
  if (p === '/verify') {
    if (method === 'POST') { state.bankCodes.push(String(form.code || '')); state.log.push('bank-code'); return page('Verify', BO, '<p class="error">That code is not right.</p><a href="/verify">Try again</a>'); }
    if (state.bankIn !== 'code') return { redirect: '/login' };
    return page('2-step verification', BO, '<h1>Confirm it\'s you</h1><p>We sent a 6-digit verification code to your phone ending in 77.</p><form method="post" action="/verify"><input name="code" autocomplete="one-time-code" placeholder="6-digit code"> <button type="submit">Verify</button></form>');
  }
  return page('First Test Bank – Sign in', BO, '<h1>Online banking</h1><form method="post" action="/login"><p><input name="username" autocomplete="username" placeholder="Username"></p><p><input type="password" name="password" autocomplete="current-password" placeholder="Password"></p><button type="submit">Sign in</button></form>');
}

// ---- rosaspizza.test + the fake search engine ----------------------------------------------------------------------------------------
function pizza(state, u) {
  const P = { brand: "Rosa's Pizza", nav: [['Menu', '/menu'], ['Order online', '/order'], ['Contact', '/contact'], ['Catering', '/catering']] };
  if (u.pathname === '/contact') return page("Contact – Rosa's Pizza", P, '<h1>Contact us</h1><p>Rosa\'s Pizza, 220 Main Street, Dresden, OH</p><p>Phone: (740) 555-0182</p><p>Open daily 11 AM – 10 PM.</p>');
  if (u.pathname === '/menu') return page("Menu – Rosa's Pizza", P, '<h1>Menu</h1><p>Margherita $12. Pepperoni $14.</p>');
  return page("Rosa's Pizza – Dresden, Ohio", P, '<h1>Rosa\'s Pizza</h1><p>Family pizza since 1988.</p><p><a href="/contact">Call or visit us</a></p>');
}
const SEARCH_INDEX = [
  { title: "Rosa's Pizza – Dresden, Ohio", url: 'https://rosaspizza.test/', snippet: 'Family pizza since 1988. Menu, online ordering and contact.' },
  { title: "Rosa's Pizzeria Dresden (Germany) – Speisekarte", url: 'https://rosas-pizzeria-dresden.test/', snippet: 'Pizzeria in Dresden-Neustadt.' },
  { title: 'Best pizza in Dresden OH – CityGuide', url: 'https://cityguide.test/dresden-pizza', snippet: "Top 5 pizza places including Rosa's." },
  { title: 'Dresden Public Library', url: 'https://library.test/', snippet: 'Branches, hours, catalog and events.' },
  { title: 'ShopMart – Online shopping', url: 'https://shop.test/', snippet: 'Lamps, batteries, electronics.' },
  { title: 'HomeCook recipes', url: 'https://recipes.test/', snippet: 'Banana bread, chili and more.' },
  { title: 'Schoolhub – Find your school', url: 'https://portal.schoolhub.test/', snippet: 'Sign in to your school portal.' }
];
function searchResults(q) {
  const ws = String(q || '').toLowerCase().split(/\W+/).filter((w) => w.length > 2);
  return SEARCH_INDEX.map((r) => ({ r, n: ws.filter((w) => (r.title + ' ' + r.snippet + ' ' + r.url).toLowerCase().includes(w)).length })).filter((x) => x.n).sort((a, b) => b.n - a.n).slice(0, 8).map((x) => x.r);
}
function ddg(state, u) {
  const q = u.searchParams.get('q') || '';
  const R = searchResults(q);
  return page(q + ' at DuckDuckGo', { brand: 'DuckDuckGo (test)', nav: [], banner: false, foot: ['Privacy', 'Settings'] }, '<form action="/"><input name="q" value="' + esc(q) + '" aria-label="Search"> <button>Search</button></form><ol>' + R.map((r) => '<li><a href="' + esc(r.url) + '">' + esc(r.title) + '</a><br>' + esc(r.snippet) + '</li>').join('') + '</ol>');
}

const HOSTS = {
  'portal.schoolhub.test': portal, 'accounts.google.test': sso, 'shop.test': shop, 'library.test': library, 'runclub.test': runclub,
  'news.test': news, 'recipes.test': recipes, 'account.test': account, 'mail.test': mail, 'bank.test': bank, 'rosaspizza.test': pizza,
  'duckduckgo.com': ddg, 'www.duckduckgo.com': ddg
};

// -> { status, headers, body }
function handle(state, url, method, form) {
  let u; try { u = new URL(url); } catch (e) { return { status: 400, headers: { 'content-type': 'text/plain' }, body: 'bad url' }; }
  const fn = HOSTS[u.hostname.toLowerCase().replace(/^www\.(?=[a-z]+\.test$)/, '')];
  state.visits.push(method + ' ' + u.hostname + u.pathname + u.search);
  if (!fn) return { status: 502, headers: { 'content-type': 'text/html' }, body: '<!doctype html><title>Server not found</title><h1>This site can\'t be reached</h1><p>' + esc(u.hostname) + ' could not be found (offline test network).</p>' };
  if (u.pathname.startsWith('/info/')) return { status: 200, headers: { 'content-type': 'text/html; charset=utf-8' }, body: page('Info', { nav: [['Home', '/']] }, '<h1>' + esc(u.pathname.slice(6)) + '</h1><p>General information page.</p>') };
  const r = fn(state, u, method, form || {});
  if (r && r.redirect) return { status: 302, headers: { location: new URL(r.redirect, u).href }, body: '' };
  return { status: 200, headers: { 'content-type': 'text/html; charset=utf-8' }, body: r };
}

module.exports = { newState, handle, searchResults, assignments, dayInfo, BRANCHES, SAVED_LOGINS: { 'https://mail.test': { user: 'ben.hannan', password: 'bench-mail-pw-1' }, 'https://bank.test': { user: 'bhannan', password: 'bench-bank-pw-2' } } };
