import { useEffect } from "react";

// Courier parcels that pop up, float up and drift away: a few when the page opens, and one on every click.
const BOX =
  '<svg viewBox="0 0 64 64" width="100%" height="100%" aria-hidden="true"><rect x="6" y="14" width="52" height="44" rx="3" fill="#d9a066" stroke="#8a5a2b" stroke-width="2"/>' +
  '<rect x="6" y="14" width="52" height="12" fill="#c58c52" stroke="#8a5a2b" stroke-width="2"/><rect x="26" y="14" width="12" height="44" fill="#f2e2c4" opacity=".85"/>' +
  '<rect x="38" y="36" width="15" height="14" rx="2" fill="#fff" stroke="#1e3a78" stroke-width="1.5"/><path d="M41 41h9M41 45h6" stroke="#1e3a78" stroke-width="1.5" stroke-linecap="round"/></svg>';
const MAX_LIVE = 14;

function launch(layer, x, y, size = 56) {
  if (layer.childElementCount >= MAX_LIVE) return;
  const el = document.createElement("div");
  el.innerHTML = BOX;
  el.style.cssText = `position:absolute;left:${x}px;top:${y}px;width:${size}px;height:${size}px;margin:${-size / 2}px 0 0 ${-size / 2}px;pointer-events:none;will-change:transform,opacity`;
  layer.appendChild(el);
  const rot = Math.random() * 24 - 12;
  const side = (Math.random() < 0.5 ? -1 : 1) * (50 + Math.random() * 110);
  const rise = Math.min(y + size, 260 + Math.random() * 180);
  const anim = el.animate(
    [
      { transform: `translate(0,0) scale(0) rotate(${rot * 2}deg)`, opacity: 0, offset: 0 },
      { transform: `translate(0,-6px) scale(1.2) rotate(${rot}deg)`, opacity: 1, offset: 0.12 },
      { transform: `translate(0,-14px) scale(1) rotate(${rot}deg)`, opacity: 1, offset: 0.2 },
      { transform: `translate(${side * 0.3}px,${-rise * 0.4}px) scale(1) rotate(${rot + 8}deg)`, opacity: 1, offset: 0.5 },
      { transform: `translate(${side * 0.7}px,${-rise * 0.75}px) scale(0.85) rotate(${rot - 8}deg)`, opacity: 0.85, offset: 0.8 },
      { transform: `translate(${side}px,${-rise}px) scale(0.6) rotate(${rot + 6}deg)`, opacity: 0, offset: 1 },
    ],
    { duration: 1900 + Math.random() * 500, easing: "ease-out", fill: "forwards" },
  );
  anim.onfinish = () => el.remove();
}

export default function ParcelClicks() {
  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return undefined;
    const layer = document.createElement("div");
    layer.style.cssText = "position:fixed;inset:0;z-index:40;pointer-events:none;overflow:hidden";
    layer.setAttribute("aria-hidden", "true");
    document.body.appendChild(layer);

    const timers = [];
    const w = window.innerWidth;
    const h = window.innerHeight;
    for (let i = 0; i < 4; i += 1) {
      timers.push(setTimeout(() => launch(layer, w * (0.2 + 0.2 * i) + (Math.random() * 60 - 30), h * (0.65 + Math.random() * 0.2), 52), 250 + i * 220));
    }

    let last = 0;
    const onClick = (e) => {
      const tag = e.target?.tagName;
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA" || tag === "OPTION") return;
      const now = Date.now();
      if (now - last < 90) return;
      last = now;
      launch(layer, e.clientX, e.clientY);
    };
    document.addEventListener("click", onClick);
    return () => {
      timers.forEach(clearTimeout);
      document.removeEventListener("click", onClick);
      layer.remove();
    };
  }, []);
  return null;
}
