// Example from a three.js portfolio: the page must fit every viewport height without scrolling or hiding controls.
// Adapt the selectors (.zone-nav, .bottom-dock, #primary-actions, .site-header, .intro-copy) and control names.
import { test, expect, type Page } from '@playwright/test';

// The zone dock is fixed to the viewport, so the lab must fit whatever height it is given. These sizes all failed
// before the viewport-height tiers in theme.css: the tour controls sat underneath the dock and the page scrolled.
const sizes:[string,number,number,boolean][]=[
 ['small phone, browser bars showing',375,548,true],
 ['phone in landscape',844,390,true],
 ['smallest landscape phone',568,320,true],
 ['1366x768 laptop',1366,650,false],
 ['short laptop window',1280,600,false],
];

async function enterLab(page:Page){
 // Layout does not depend on the heavy models; skipping them keeps five lab loads affordable on a software GPU.
 await page.route(/\.(glb|hdr)$/,route=>route.abort());
 await page.goto('/');
 await expect(page.locator('.loading-badge')).toHaveCount(0,{timeout:60000});
}

for(const [name,width,height,mobile] of sizes){
 test(`the lab fits without scrolling: ${name} (${width}x${height})`,async({browser})=>{
  const context=await browser.newContext({viewport:{width,height},deviceScaleFactor:mobile?2:1,isMobile:mobile,hasTouch:mobile,reducedMotion:'reduce'});
  const page=await context.newPage();await enterLab(page);
  const box=await page.evaluate(()=>{
   const rect=(selector:string)=>document.querySelector(selector)!.getBoundingClientRect();
   const nav=rect('.zone-nav'),dock=rect('.bottom-dock'),actions=rect('#primary-actions'),header=rect('.site-header'),copy=rect('.intro-copy');
   return {scroll:document.documentElement.scrollHeight-innerHeight,overflowX:document.documentElement.scrollWidth-innerWidth,dockUnderNav:dock.bottom-nav.top,actionsOverDock:actions.bottom-dock.top,copyUnderHeader:header.bottom-copy.top};
  });
  expect(box.scroll,'page must not scroll vertically').toBeLessThanOrEqual(0);
  expect(box.overflowX,'page must not scroll sideways').toBeLessThanOrEqual(0);
  expect(box.dockUnderNav,'tour controls must sit above the zone dock').toBeLessThanOrEqual(0);
  expect(box.actionsOverDock,'primary actions must sit above the tour controls').toBeLessThanOrEqual(0);
  expect(box.copyUnderHeader,'caption must start below the header').toBeLessThanOrEqual(0);
  // Replace with your own controls' accessible names.
  for(const control of ['Primary action','Secondary action','Enter full screen','Last navigation item'])await expect(page.getByRole('button',{name:control}).first()).toBeInViewport({ratio:1});
  await context.close();
 });
}
