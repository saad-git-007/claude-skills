// Example shot list (the Moraine Lake app): skip the intro, open a place card, click Sunset / Night, punch in on the
// toolbar while its buttons are clicked, scroll-zoom. Adapt selectors and hooks to your app.
const btn = t => `.mui-seg button[data-t="${t}"]`;
const click = (cursor, events, t, at) => { cursor.push({ t: t - 0.1, at }, { t: t + 0.35, at }); events.push({ kind: 'click', t }); };
const cursor = [{ t: 0, at: [1500, 900] }], events = [];
click(cursor, events, 1.0, '.mui-skip');                                       // Skip intro
click(cursor, events, 3.0, { call: 'pickMarker', arg: 'Mount Perren', aim: '.dot' });   // a moving marker, followed per frame
click(cursor, events, 6.0, '.mui-cardwrap .mui-x');                            // close the card
click(cursor, events, 7.2, btn('sunset'));
click(cursor, events, 9.5, btn('night'));
events.push({ kind: 'wheel', t: 11, t1: 12, dy: -500 });

export default {
  duration: 13,
  url: '/?quality=high&q=1',
  ready: 'window.__ready === true',
  loaderGone: '.mui-load.off',
  settleMs: 3500,
  hide: '.mui-fps',
  async setup(page) {
    await page.evaluate(() => {
      // a window function the recorder can call to get an Element that moves with the camera
      window.pickMarker = name => [...document.querySelectorAll('.mui-poi')].find(b => b.getAttribute('aria-label')?.startsWith(name) && +getComputedStyle(b).opacity > 0.5) || null;
    });
  },
  async start(page) { await page.evaluate(() => { if (window.__intro) { window.__intro.active = true; window.__intro.t = 0.05; } }); },   // restart the fly-in
  cursor, events,
  zoom: [
    { t: 0, z: 1 }, { t: 6.9, z: 1 },
    { t: 7.1, z: 2.4, at: '.mui-dock' }, { t: 10.6, z: 2.4, at: '.mui-dock' }, { t: 11.2, z: 1 },
  ],
};
