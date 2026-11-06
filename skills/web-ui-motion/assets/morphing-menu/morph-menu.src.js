// Morphing bottom menu (phones and narrow windows).
// A vanilla-JS port of Danny Williams's MorphingMenu.tsx, using the same motion springs.
// The markup is rendered by the server (site.ts) so the dock links work before this script loads.
// Bundle: `npm run build:client` -> public/assets/morph-menu.js

import { animate } from "motion/mini";
import { spring as springType } from "motion";

const spring = (duration, bounce) => ({ type: springType, duration, bounce });
const SPRING = { duration: 0.4, bounce: 0.24 };
const COMPRESS = { duration: 0.1, ease: [0.4, 0, 0.2, 1] };
const HOVER_DELAY = 400;
const HOVER_GRACE_PERIOD = 300;

function init(root) {
  const shell = root.querySelector(".morphing-menu__shell");
  const bar = root.querySelector(".morphing-menu__bar");
  const more = bar.querySelector('[data-menu-item="more"]');
  const panels = [...root.querySelectorAll(".morphing-menu__panel")];
  const main = panels[0];
  const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let view = "collapsed";
  let previousView = view;
  let running = [];
  let cancelled = { value: false };
  let returnTarget = "more";
  let openedWithKeyboard = false;
  let restoringFocus = false;
  let suppressHoverUntilMove = false;
  let focusNext = null;
  let tooltipTimer, tooltipResetTimer;
  let hintsRevealed = false;
  let barHovered = false;

  // ---------- tooltips (mouse hover and keyboard focus only) ----------
  const tip = document.createElement("div");
  tip.className = "morphing-menu__tooltip";
  tip.setAttribute("aria-hidden", "true");
  tip.hidden = true;
  root.appendChild(tip);
  const expanded = () => view !== "collapsed";

  function hideTooltip() { clearTimeout(tooltipTimer); tip.hidden = true; }
  function dismissTooltip() { hideTooltip(); clearTimeout(tooltipResetTimer); hintsRevealed = false; }
  function showTooltip(el, text, immediate = false) {
    clearTimeout(tooltipTimer);
    if (expanded() || restoringFocus) return;
    if (suppressHoverUntilMove && !immediate) return;
    // Layout coordinates, so the shell's temporary scale cannot offset hints.
    const x = (root.clientWidth - bar.offsetWidth) / 2 + el.offsetLeft + el.offsetWidth / 2;
    clearTimeout(tooltipResetTimer);
    const reveal = () => { hintsRevealed = true; tip.textContent = text; tip.style.left = x + "px"; tip.hidden = false; };
    if (immediate || hintsRevealed) reveal();
    else tooltipTimer = setTimeout(reveal, HOVER_DELAY);
  }

  // ---------- state changes ----------
  function setView(next) { view = next; render(); }

  function open(origin, keyboard) {
    dismissTooltip();
    if (!expanded()) { returnTarget = origin; openedWithKeyboard = keyboard; }
    focusNext = "first";
    setView("main");
  }

  function close(restoreFocus = true, target = returnTarget) {
    if (!expanded()) return;
    dismissTooltip();
    suppressHoverUntilMove = true;
    focusNext = restoreFocus && openedWithKeyboard ? target : null;
    setView("collapsed");
  }

  // The shell stays mounted. Interrupting an animation cancels its next phase,
  // then the next transition starts from the currently rendered geometry.
  function render() {
    cancelled.value = true;
    running.forEach((a) => { try { a.stop(); } catch (e) { /* already done */ } });
    running = [];
    const token = (cancelled = { value: false });
    const track = (a) => { running.push(a); return a; };

    const isOpen = view !== "collapsed";
    root.dataset.view = view;
    bar.setAttribute("aria-hidden", String(isOpen));
    bar.inert = isOpen;
    main.setAttribute("aria-hidden", String(view !== "main"));
    main.inert = view !== "main";
    more.setAttribute("aria-expanded", String(isOpen));

    const old = previousView;
    previousView = view;
    const panel = panels.find((el) => el.getAttribute("aria-hidden") === "false");
    const targetSize = () => ({ width: (panel ? panel.offsetWidth : bar.offsetWidth) + "px", height: (panel ? panel.offsetHeight : bar.offsetHeight) + "px" });
    const setSize = () => { const s = targetSize(); shell.style.width = s.width; shell.style.height = s.height; };
    const changed = old !== view;
    const crossingBar = (old === "collapsed") !== (view === "collapsed");
    const reduce = reducedMotion();
    const snap = reduce || !changed;

    if (snap) setSize();
    else if (crossingBar) {
      const width = Math.min(bar.offsetWidth, bar.offsetWidth > 250 ? 280 : 200);
      const compression = track(animate(shell, { width: width + "px", height: (bar.offsetHeight > 52 ? 32 : 28) + "px" }, COMPRESS));
      compression.finished.then(() => {
        if (!token.value) track(animate(shell, targetSize(), spring(SPRING.duration, isOpen ? 0.24 : 0.15)));
      }).catch(() => {}); // A stopped transition must never resume its second phase.
    } else {
      track(animate(shell, targetSize(), spring(0.25, 0.1)));
    }

    track(animate(bar, {
      opacity: isOpen ? 0 : 1,
      scale: isOpen && !reduce ? 0.8 : 1,
      filter: isOpen && !reduce ? "blur(8px)" : "blur(0px)",
    }, {
      duration: snap ? 0 : isOpen ? 0.15 : 0.22,
      delay: !snap && !isOpen ? 0.08 : 0,
      ...(!isOpen ? { ease: "easeOut" } : {}),
    }));

    for (const layer of panels) {
      const visible = layer === panel;
      [...layer.querySelectorAll(".morphing-menu__row")].forEach((row, index) => {
        if (visible && crossingBar && !snap) {
          Object.assign(row.style, { opacity: "0", transform: "translateY(48px)", filter: "blur(4px)" });
        }
        const s = spring(snap ? 0.0001 : visible ? (crossingBar ? 0.4 : 0.25) : 0.12, crossingBar ? 0.3 : 0);
        track(animate(row, {
          opacity: visible ? 1 : 0,
          transform: visible || reduce ? "translateY(0px)" : "translateY(16px)",
          filter: visible || reduce ? "blur(0px)" : "blur(2px)",
        }, { ...s, delay: !snap && visible ? (crossingBar ? 0.2 : 0) + index * 0.02 : 0 }));
      });
    }

    const destination = isOpen ? panel : bar;
    const controls = destination ? [...destination.querySelectorAll("[data-menu-item]")] : [];
    const focus = focusNext;
    focusNext = null;
    if (focus) {
      // Restoring navigation position is not a fresh request to show a hint.
      restoringFocus = true;
      const target = focus === "first" ? controls[0] : controls.find((el) => el.dataset.menuItem === focus);
      (target || (!isOpen ? controls.find((el) => el.dataset.menuItem === "more") : undefined))?.focus({ preventScroll: true });
      restoringFocus = false;
    }
  }

  // ---------- events ----------
  more.addEventListener("click", (e) => { if (expanded()) close(); else open("more", e.detail === 0); });

  root.querySelectorAll("[data-menu-item]").forEach((el) => {
    const inBar = el.classList.contains("morphing-menu__shortcut");
    const label = el.getAttribute("aria-label") || el.textContent.trim();
    // Shortcuts that show their name under the icon do not need a hover hint.
    if (inBar && !el.querySelector(".mm-cap")) {
      el.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") showTooltip(el, label); });
      el.addEventListener("focus", () => { if (el.matches(":focus-visible")) showTooltip(el, label, true); });
    }
    el.addEventListener("pointerleave", hideTooltip);
    el.addEventListener("pointerdown", dismissTooltip);
    el.addEventListener("blur", hideTooltip);
    // Choosing a destination collapses the menu; the link then navigates as usual.
    if (el.tagName === "A" && !inBar) el.addEventListener("click", () => close(true, el.dataset.menuItem));
  });

  bar.addEventListener("pointerenter", (e) => { if (e.pointerType !== "mouse") return; barHovered = true; clearTimeout(tooltipResetTimer); });
  bar.addEventListener("pointerleave", (e) => {
    if (e.pointerType !== "mouse") return;
    barHovered = false;
    hideTooltip();
    clearTimeout(tooltipResetTimer);
    // Padding keeps hints ready; only leaving the whole bar starts grace.
    tooltipResetTimer = setTimeout(() => { hintsRevealed = false; }, HOVER_GRACE_PERIOD);
  });

  root.addEventListener("pointermove", (e) => {
    // A collapsing bar can move under a stationary cursor and fire enter.
    // Only an actual pointer movement should revive a dismissed hover hint.
    if (!suppressHoverUntilMove || e.pointerType !== "mouse" || (!e.movementX && !e.movementY)) return;
    suppressHoverUntilMove = false;
    const shortcut = e.target instanceof Element ? e.target.closest(".morphing-menu__shortcut") : null;
    if (shortcut) showTooltip(shortcut, shortcut.getAttribute("aria-label") || "");
  });

  root.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    suppressHoverUntilMove = true;
    dismissTooltip();
    if (!expanded()) return;
    e.preventDefault();
    e.stopPropagation();
    close();
  });

  root.addEventListener("focusout", (e) => {
    if (e.relatedTarget instanceof Node && root.contains(e.relatedTarget)) return;
    if (expanded()) { if (e.relatedTarget instanceof Node) close(false); }
    // Keyboard-only visits have no pointer-leave event to expire the session.
    else if (!barHovered) dismissTooltip();
  });

  document.addEventListener("pointerdown", (e) => {
    if (expanded() && e.target instanceof Node && !root.contains(e.target)) close(false);
  });

  // Geometry is measured from CSS (including the larger touch tier), so re-measure on resize.
  window.addEventListener("resize", () => { previousView = view; render(); });
  // The first measurement can run before the menu's stylesheet applies (an unstyled bar measures ~2000px tall and the
  // shell would cover the page). Re-measure whenever the bar or a panel actually changes size.
  let resync = 0;
  const syncSize = () => { cancelAnimationFrame(resync); resync = requestAnimationFrame(() => { previousView = view; render(); }); };
  if ("ResizeObserver" in window) {
    let first = true;
    const ro = new ResizeObserver(() => { if (first) { first = false; return; } syncSize(); });
    [bar, ...panels].forEach((el) => ro.observe(el));
  }
  window.addEventListener("load", syncSize);
  // A page restored from the back/forward cache comes back collapsed.
  window.addEventListener("pageshow", (e) => { if (e.persisted && expanded()) { view = "collapsed"; previousView = "collapsed"; render(); } });

  root.classList.add("is-ready");
  render();
}

document.querySelectorAll(".morphing-menu").forEach(init);
