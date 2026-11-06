/* Scroll reveal, part 1 of 2: load in <head> (blocking, tiny) so the class is set BEFORE first paint.
   Without it, blocks would flash visible and then hide. If scroll-reveal.js never runs (blocked, error, offline),
   the class is removed after 2.5 s so nothing stays hidden. Reduced motion: never set, so everything is just visible. */
(function () {
  var root = document.documentElement;
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  root.classList.add('reveal-on');
  setTimeout(function () { if (!window.__revealReady) root.classList.remove('reveal-on'); }, 2500);
})();
