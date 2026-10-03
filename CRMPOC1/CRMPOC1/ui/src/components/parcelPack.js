// Courier parcel effects for the Order List:
//  - launchIntro(): a few parcels pop up and float away when the page opens
//  - packOrder(label, done): items drop into a box, the flaps close, tape seals it, then done() runs (opens the order)
const BOX_SVG =
  '<svg viewBox="0 0 64 64" width="100%" height="100%" aria-hidden="true"><rect x="6" y="14" width="52" height="44" rx="3" fill="#d9a066" stroke="#8a5a2b" stroke-width="2"/>' +
  '<rect x="6" y="14" width="52" height="12" fill="#c58c52" stroke="#8a5a2b" stroke-width="2"/><rect x="26" y="14" width="12" height="44" fill="#f2e2c4" opacity=".85"/>' +
  '<rect x="38" y="36" width="15" height="14" rx="2" fill="#fff" stroke="#1e3a78" stroke-width="1.5"/><path d="M41 41h9M41 45h6" stroke="#1e3a78" stroke-width="1.5" stroke-linecap="round"/></svg>';

const ICON = (d) =>
  `<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
const ITEMS = [
  ICON('<circle cx="12" cy="12" r="2"/><path d="M12 10c0-4 1-7 4-7 2 0 2 3 0 5l-4 2zM14 12c4 0 7 1 7 4 0 2-3 2-5 0l-2-4zM12 14c0 4-1 7-4 7-2 0-2-3 0-5l4-2zM10 12c-4 0-7-1-7-4 0-2 3-2 5 0l2 4z"/>'),
  ICON('<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3"/>'),
  ICON('<rect x="3" y="8" width="14" height="8" rx="2"/><path d="M17 10h3v4h-3M7 8V5h6v3M7 12h6"/>'),
];

const CSS = `
.pp-fly{position:fixed;width:52px;height:52px;margin:-26px 0 0 -26px;pointer-events:none;z-index:70;will-change:transform,opacity}
.pp-ov{position:fixed;inset:0;z-index:80;background:rgba(18,41,92,.55);display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .15s}
.pp-ov.show{opacity:1}
.pp-stage{position:relative;width:240px;height:260px;perspective:700px}
.pp-box{position:absolute;left:55px;top:110px;width:130px;height:130px;transform-style:preserve-3d}
.pp-in{position:absolute;inset:0;background:#7a4a22;border:3px solid #8a5a2b;border-radius:4px}
.pp-fl{position:absolute;top:0;width:65px;height:130px;background:#d9a066;border:3px solid #8a5a2b;box-sizing:border-box;transition:transform .4s cubic-bezier(.3,.9,.3,1)}
.pp-fl.l{left:0;transform-origin:0 50%;transform:rotateY(172deg)}
.pp-fl.r{right:0;transform-origin:100% 50%;transform:rotateY(-172deg);background:#cf9658}
.pp-box.closed .pp-fl{transform:rotateY(0)}
.pp-tape{position:absolute;left:50%;top:-4px;width:20px;height:0;margin-left:-10px;background:#f2e2c4;border-left:1px solid #d8c498;border-right:1px solid #d8c498;transition:height .25s ease-out;z-index:3}
.pp-box.taped .pp-tape{height:138px}
.pp-lab{position:absolute;left:12px;bottom:12px;max-width:106px;overflow:hidden;text-overflow:ellipsis;background:#fff;border:1.5px solid #1e3a78;color:#1e3a78;font:600 10px system-ui,sans-serif;padding:3px 6px;border-radius:3px;transform:scale(0);transition:transform .2s cubic-bezier(.3,1.8,.5,1);z-index:4;white-space:nowrap}
.pp-box.taped .pp-lab{transform:scale(1) rotate(-4deg)}
.pp-item{position:absolute;top:-30px;width:50px;height:50px;border-radius:10px;background:#fff;border:1.5px solid #1e3a78;color:#1e3a78;display:flex;align-items:center;justify-content:center;opacity:0;z-index:2}
.pp-msg{position:absolute;left:0;right:0;bottom:6px;text-align:center;color:#fff;font:600 13px system-ui,sans-serif;opacity:0;transition:opacity .2s}
.pp-msg.on{opacity:1}
`;

let styled = false;
let busy = false;
const reduced = () => !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

function ensureStyle() {
  if (styled) return;
  const st = document.createElement("style");
  st.textContent = CSS;
  document.head.appendChild(st);
  styled = true;
}

function fly(x, y) {
  const el = document.createElement("div");
  el.className = "pp-fly";
  el.style.left = `${x}px`;
  el.style.top = `${y}px`;
  el.innerHTML = BOX_SVG;
  document.body.appendChild(el);
  const rot = Math.random() * 24 - 12;
  const side = (Math.random() < 0.5 ? -1 : 1) * (50 + Math.random() * 110);
  const rise = Math.min(y + 40, 220 + Math.random() * 160);
  el.animate(
    [
      { transform: `scale(0) rotate(${rot * 2}deg)`, opacity: 0, offset: 0 },
      { transform: `translate(0,-6px) scale(1.2) rotate(${rot}deg)`, opacity: 1, offset: 0.12 },
      { transform: `translate(${side * 0.4}px,${-rise * 0.45}px) rotate(${rot + 8}deg)`, opacity: 1, offset: 0.5 },
      { transform: `translate(${side}px,${-rise}px) scale(0.6) rotate(${rot - 6}deg)`, opacity: 0, offset: 1 },
    ],
    { duration: 2000 + Math.random() * 400, easing: "ease-out", fill: "forwards" },
  ).onfinish = () => el.remove();
}

// returns a cancel function
export function launchIntro() {
  if (reduced()) return () => {};
  ensureStyle();
  const w = window.innerWidth;
  const h = window.innerHeight;
  const timers = [0, 1, 2, 3].map((i) =>
    setTimeout(() => fly(w * (0.2 + 0.2 * i) + (Math.random() * 60 - 30), h * (0.65 + Math.random() * 0.2)), 250 + i * 220),
  );
  return () => timers.forEach(clearTimeout);
}

export async function packOrder(label, done) {
  if (busy) return;
  if (reduced()) {
    done?.();
    return;
  }
  busy = true;
  ensureStyle();
  const ov = document.createElement("div");
  ov.className = "pp-ov";
  ov.setAttribute("aria-hidden", "true");
  ov.innerHTML =
    '<div class="pp-stage"><div class="pp-box"><div class="pp-in"></div><div class="pp-fl l"></div><div class="pp-fl r"></div><div class="pp-tape"></div><div class="pp-lab"></div></div>' +
    ITEMS.map((svg, i) => `<div class="pp-item" style="left:${65 + (i - 1) * 22}px">${svg}</div>`).join("") +
    '</div><div class="pp-msg">Packed. Opening your order</div>';
  ov.querySelector(".pp-lab").textContent = label || "Order";
  document.body.appendChild(ov);
  const box = ov.querySelector(".pp-box");
  const msg = ov.querySelector(".pp-msg");
  try {
    await wait(20);
    ov.classList.add("show");
    await wait(120);
    const items = [...ov.querySelectorAll(".pp-item")];
    for (const it of items) {
      it.animate(
        [
          { transform: "translateY(-20px) scale(1.1)", opacity: 0, offset: 0 },
          { transform: "translateY(40px) scale(1)", opacity: 1, offset: 0.3 },
          { transform: "translateY(150px) scale(.55)", opacity: 1, offset: 0.85 },
          { transform: "translateY(165px) scale(.35)", opacity: 0, offset: 1 },
        ],
        { duration: 340, easing: "ease-in", fill: "forwards" },
      );
      await wait(190);
    }
    await wait(150);
    box.classList.add("closed");
    await wait(430);
    box.classList.add("taped");
    await wait(280);
    box.animate(
      [
        { transform: "scale(1,1)" },
        { transform: "scale(1.12,.86) translateY(8px)", offset: 0.25 },
        { transform: "translateY(-22px) scale(.96,1.05)", offset: 0.55 },
        { transform: "scale(1,1)" },
      ],
      { duration: 300, easing: "ease-out" },
    );
    msg.classList.add("on");
    await wait(320);
    // lift off and open the order underneath the fading overlay
    box.animate(
      [{ transform: "translateY(0) scale(1)", opacity: 1 }, { transform: "translateY(-110px) scale(.5)", opacity: 0 }],
      { duration: 320, easing: "ease-in", fill: "forwards" },
    );
    done?.();
    await wait(280);
    ov.classList.remove("show");
    await wait(180);
  } finally {
    ov.remove();
    busy = false;
  }
}
