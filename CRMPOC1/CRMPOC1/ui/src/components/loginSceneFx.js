// Click / tap reactions for the animated login background (decorative only).
//   click a person        -> they hop, a ring glows, they say a line, a few snowflakes
//   click a floating part -> it spins once, its name shows in a tag, snowflakes
//   click the background  -> a cool ripple and a burst of snowflakes
//   mouse (not touch)     -> the floating parts drift slightly with the pointer
// Everything is drawn into the .ls-fx layer and removes itself again.

const FLAKE = '<svg viewBox="0 0 28 28"><use href="#ls-flake" width="28" height="28"/></svg>';

export function attachSceneEffects(wrap, stage, fx) {
  const timers = new Set();
  const later = (fn, ms) => {
    const t = setTimeout(() => {
      timers.delete(t);
      fn();
    }, ms);
    timers.add(t);
  };
  const scaleOf = () => (stage.offsetWidth ? stage.getBoundingClientRect().width / stage.offsetWidth : 1);
  const put = (cls, html, css) => {
    const d = document.createElement("div");
    d.className = cls;
    d.style.cssText = css;
    d.innerHTML = html;
    fx.appendChild(d);
    return d;
  };

  function snow(x, y, n) {
    for (let i = 0; i < n; i += 1) {
      const a = ((Math.PI * 2) / n) * i + Math.random() * 0.5;
      const r = 50 + Math.random() * 50;
      const s = put("ls-snow", FLAKE, `left:${x}px;top:${y}px;--x:${(Math.cos(a) * r).toFixed(0)}px;--y:${(Math.sin(a) * r).toFixed(0)}px`);
      later(() => s.remove(), 950);
    }
  }

  function ripple(x, y) {
    const r = put("ls-rip", "", `left:${x}px;top:${y}px`);
    later(() => r.remove(), 950);
  }

  function say(actor) {
    fx.querySelectorAll(".ls-say").forEach((n) => n.remove());
    const x = actor.offsetLeft;
    const y = actor.offsetTop;
    const w = actor.offsetWidth;
    const h = actor.offsetHeight;
    const bubble = put("ls-say", actor.getAttribute("data-say") || "", "left:0;top:0");
    const bw = bubble.offsetWidth;
    const bh = bubble.offsetHeight;
    const below = y < stage.offsetHeight / 2 - 40; // top row: bubble under the person, bottom row: above
    const left = Math.min(Math.max(x + w / 2 - bw / 2, 4), stage.offsetWidth - bw - 4);
    const top = Math.min(Math.max(below ? y + h + 8 : y - bh - 8, 4), stage.offsetHeight - bh - 4);
    bubble.style.left = `${left}px`;
    bubble.style.top = `${top}px`;
    requestAnimationFrame(() => bubble.classList.add("ls-on"));
    later(() => {
      bubble.classList.remove("ls-on");
      later(() => bubble.remove(), 250);
    }, 2600);
  }

  function hitActor(actor) {
    actor.classList.remove("ls-hit");
    void actor.offsetWidth; // restart the animation on a quick second click
    actor.classList.add("ls-hit");
    const glow = put(
      "ls-glow",
      "",
      `left:${actor.offsetLeft - 12}px;top:${actor.offsetTop - 8}px;width:${actor.offsetWidth + 24}px;height:${actor.offsetHeight + 16}px`,
    );
    later(() => glow.remove(), 850);
    say(actor);
    snow(actor.offsetLeft + actor.offsetWidth / 2, actor.offsetTop + actor.offsetHeight * 0.4, 5);
  }

  function popPart(part) {
    part.classList.remove("ls-pop");
    void part.offsetWidth;
    part.classList.add("ls-pop");
    const s = scaleOf();
    const sr = stage.getBoundingClientRect();
    const r = part.getBoundingClientRect();
    const tag = put("ls-tagname", part.getAttribute("data-name") || "", `left:${(r.left - sr.left) / s}px;top:${(r.top - sr.top) / s - 28}px`);
    requestAnimationFrame(() => tag.classList.add("ls-on"));
    later(() => {
      tag.remove();
      part.classList.remove("ls-pop");
    }, 1600);
    snow((r.left - sr.left + r.width / 2) / s, (r.top - sr.top + r.height / 2) / s, 6);
  }

  function onClick(e) {
    if (e.target.closest(".ls-card")) return; // never react while someone types the password
    const actor = e.target.closest('[data-ls="act"]');
    if (actor) return hitActor(actor);
    const part = e.target.closest('[data-ls="part"]');
    if (part) return popPart(part);
    const sr = stage.getBoundingClientRect();
    const s = scaleOf();
    const x = (e.clientX - sr.left) / s;
    const y = (e.clientY - sr.top) / s;
    ripple(x, y);
    snow(x, y, 7);
    return undefined;
  }

  const fine = window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  function onMove(e) {
    const r = wrap.getBoundingClientRect();
    const mx = (e.clientX - r.left) / r.width - 0.5;
    const my = (e.clientY - r.top) / r.height - 0.5;
    stage.querySelectorAll('[data-ls="part"]').forEach((p) => {
      const d = Number(p.getAttribute("data-depth")) || 0.03;
      p.firstElementChild.style.transform = `translate(${(mx * d * -900).toFixed(1)}px,${(my * d * -600).toFixed(1)}px)`;
    });
  }
  function onLeave() {
    stage.querySelectorAll('[data-ls="part"]').forEach((p) => {
      p.firstElementChild.style.transform = "";
    });
  }

  wrap.addEventListener("click", onClick);
  if (fine) {
    wrap.addEventListener("mousemove", onMove);
    wrap.addEventListener("mouseleave", onLeave);
  }
  return () => {
    wrap.removeEventListener("click", onClick);
    wrap.removeEventListener("mousemove", onMove);
    wrap.removeEventListener("mouseleave", onLeave);
    timers.forEach((t) => clearTimeout(t));
    timers.clear();
    fx.innerHTML = "";
  };
}
