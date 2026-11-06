/* Scroll reveal, part 2 of 2: load with `defer`. Blocks rise into view once, in reading order.
   Exact behaviour of the mosque site (2026), with generic selectors: mark single blocks with [data-reveal] and
   containers whose children should reveal one by one with [data-reveal-group]. To reuse existing class names
   instead (as the original did), put them in SELECTOR here and in scroll-reveal.css. */
(function () {
  var SELECTOR = '[data-reveal-group] > *, [data-reveal]';
  var STEP = 80;        // ms between blocks that arrive together
  var MAX_STEPS = 5;    // cap: the 6th+ block in a batch waits no longer than 400 ms
  var root = document.documentElement;
  window.__revealReady = true;
  if (!root.classList.contains('reveal-on')) return;
  var items = Array.prototype.slice.call(document.querySelectorAll(SELECTOR));
  if (!('IntersectionObserver' in window)) { items.forEach(function (el) { el.classList.add('revealed'); }); return; }
  var batch = 0, timer = 0;
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting) return;
      var el = en.target;
      el.style.setProperty('--rd', Math.min(batch++, MAX_STEPS) * STEP + 'ms');
      el.classList.add('revealed');
      io.unobserve(el);                                           // once only
      clearTimeout(timer); timer = setTimeout(function () { batch = 0; }, 120);  // a new batch starts after a pause
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.06 });
  items.forEach(function (el) { io.observe(el); });
  // After the reveal finishes, drop the delay so hover lifts respond at once.
  document.addEventListener('transitionend', function (e) {
    if (e.propertyName === 'opacity' && e.target.classList && e.target.classList.contains('revealed')) e.target.style.removeProperty('--rd');
  });
})();
