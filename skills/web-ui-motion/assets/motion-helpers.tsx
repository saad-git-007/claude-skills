// Motion helpers. Everything here is progressive: without the API, or with reduced motion, the
// interface simply shows its final state. The matching styles and the timing tokens live in motion.css.
//
// Techniques were adapted, not imported, because this project has no Tailwind or animation library:
// the circular View Transition reveal and the text scramble follow beUI (MIT, (c) 2026 Saurabh Chauhan,
// github.com/starc007/ui-components); the reveal-on-scroll observer follows the pattern on open-design.ai;
// the word-by-word headline follows MengTo/Skills "staggered-word-reveal" (MIT).
import { Fragment, useEffect, useRef, useState, type CSSProperties } from 'react';
import { flushSync } from 'react-dom';

const prefersReducedMotion=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Reveals `[data-reveal]` descendants once, as they scroll into view. Elements arriving together are staggered. */
export function useReveal<T extends HTMLElement>(active:boolean){
 const root=useRef<T>(null);
 useEffect(()=>{
  const host=root.current;if(!host||!active)return;
  const targets=Array.from(host.querySelectorAll<HTMLElement>('[data-reveal]'));
  const show=(el:HTMLElement)=>{el.dataset.revealed='true';};
  if(prefersReducedMotion()||!('IntersectionObserver' in window)){targets.forEach(show);return;}
  const observer=new IntersectionObserver(entries=>{
   let step=0;
   for(const entry of entries){
    if(!entry.isIntersecting)continue;
    const el=entry.target as HTMLElement;el.style.setProperty('--reveal-delay',`${Math.min(step++,7)*60}ms`);show(el);observer.unobserve(el);
   }
  },{threshold:.12,rootMargin:'0px 0px -6% 0px'});
  targets.forEach(el=>observer.observe(el));
  return()=>observer.disconnect();
 },[active]);
 return root;
}

/** A headline line whose words rise in one after another. Give the heading an aria-label; these spans are presentational. */
export function Words({text,from=0}:{text:string;from?:number}){
 const words=text.split(' ');
 // No wrapper element: an existing `h1>span{display:block}` rule would put every wrapped word on its own line.
 return <>{words.map((word,i)=><Fragment key={i}><span className="word" aria-hidden="true" style={{'--i':from+i} as CSSProperties}>{word}</span>{i<words.length-1?' ':''}</Fragment>)}</>;
}

const GLYPHS='ABCDEFGHJKLMNPQRSTUVWXYZ0123456789#%&/<>';
/** Decodes a short mono label from noise, left to right. Screen readers get the plain text once. */
export function Scramble({text}:{text:string}){
 const [shown,setShown]=useState(text);
 useEffect(()=>{
  if(prefersReducedMotion()){setShown(text);return;}
  const started=performance.now(),duration=Math.min(760,Math.max(420,text.length*32));let frame=0,last=0;
  const tick=(now:number)=>{
   if(now-last>=40){last=now;const settled=Math.floor(Math.min((now-started)/duration,1)*text.length);
    setShown(Array.from(text,(ch,i)=>i<settled||ch===' '?ch:GLYPHS[Math.floor(Math.random()*GLYPHS.length)]).join(''));}
   if(now-started<duration)frame=requestAnimationFrame(tick);else setShown(text);
  };
  frame=requestAnimationFrame(tick);return()=>cancelAnimationFrame(frame);
 },[text]);
 return <><span className="sr-only">{text}</span><span aria-hidden="true">{shown}</span></>;
}

type TransitionDocument=Document&{startViewTransition?:(update:()=>void)=>{finished:Promise<void>}};
/**
 * Applies a React state change inside a View Transition that opens the new view as a circle growing out of
 * `origin`, the control that was pressed. Without the API, or with reduced motion, the change is applied directly:
 * the API does not honour prefers-reduced-motion by itself.
 * Only use this when the OLD view has no WebGL canvas. Snapshotting the live lab took 1.5-3 s in testing,
 * against 21 ms for a plain swap, which is why leaving the lab does not go through here.
 */
export function transitionView(update:()=>void,origin?:Element|null){
 const doc=document as TransitionDocument;
 if(!doc.startViewTransition||prefersReducedMotion()){update();return;}
 const root=document.documentElement;
 if(origin){const box=origin.getBoundingClientRect();root.style.setProperty('--vt-origin',`${box.left+box.width/2}px ${box.top+box.height/2}px`);}
 root.dataset.vt='enter';
 doc.startViewTransition(()=>flushSync(update)).finished.finally(()=>{delete root.dataset.vt;});
}
