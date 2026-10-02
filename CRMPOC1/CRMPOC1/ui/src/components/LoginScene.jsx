import { useEffect, useRef } from "react";

import "./login-scene.css";

// Animated INDcool login background: three flows play one after another
// (complaint + spares, order a split AC, order a fridge). Decorative only.

const CY = 60; // seconds for the whole show (3 flows x 20 s)
const pct = (s) => `${((s / CY) * 100).toFixed(3)}%`;

const PTOP = "M686 72 C580 28 250 28 150 72";
const PST = "M92 126 L76 370";
const PTA = "M114 425 L352 425";
const PAV = "M448 425 L646 425";
const PBX = "M648 450 C540 510 230 510 112 450";
const PSA = "M92 126 C110 300 200 420 352 425";
const PDL = "M706 368 L724 128";

function buildCss() {
  let css = "";
  const trv = (name, s, e, path) => {
    css += `.ls-${name}{offset-path:path('${path}');animation:ls-${name} ${CY}s linear infinite}`;
    css += `@keyframes ls-${name}{0%,${pct(s)}{offset-distance:0%;opacity:0}${pct(s + 0.2)}{opacity:1}${pct(e)}{offset-distance:100%;opacity:1}${pct(e + 0.2)},100%{offset-distance:100%;opacity:0}}`;
  };
  const win = (name, list) => {
    let o = "0%{opacity:0}";
    list.forEach(([s, e]) => {
      o += `${pct(s - 0.15)}{opacity:0}${pct(s + 0.15)}{opacity:1}${pct(e - 0.15)}{opacity:1}${pct(e + 0.15)}{opacity:0}`;
    });
    css += `@keyframes ls-${name}{${o}100%{opacity:0}}.ls-k-${name}{animation:ls-${name} ${CY}s infinite}`;
  };
  // flow 1: complaint + spares (0-20 s)
  trv("t1", 1.6, 3.6, PTOP);
  trv("t2", 5.0, 6.4, PST);
  trv("t3", 7.6, 9.2, PTA);
  trv("t4", 10.6, 12.0, PAV);
  trv("bx", 14.8, 17.2, PBX);
  win("c1", [[0.4, 2.0]]);
  win("s1", [[3.6, 5.4]]);
  win("tb1", [[6.4, 8.2]]);
  win("ab", [[9.2, 11.0]]);
  win("v1", [[12.0, 13.6]]);
  win("v2", [[13.6, 15.4]]);
  win("tb2", [[17.4, 19.2]]);
  win("c2", [[18.0, 19.8]]);
  // flows 2 and 3: customer orders an item (20-40 s, 40-60 s)
  [1, 2].forEach((i) => {
    const f = i * 20;
    trv(`o${i}1`, f + 1.6, f + 4.0, PTOP);
    trv(`o${i}2`, f + 5.4, f + 8.2, PSA);
    trv(`o${i}3`, f + 10.0, f + 12.4, PAV);
    trv(`d${i}`, f + 15.2, f + 18.0, PDL);
    win(`cb${i}1`, [[f + 0.4, f + 2.4]]);
    win(`sb${i}`, [[f + 4.0, f + 6.0]]);
    win(`ab${i}`, [[f + 8.2, f + 10.4]]);
    win(`vb${i}1`, [[f + 12.4, f + 14.2]]);
    win(`vb${i}2`, [[f + 14.2, f + 15.8]]);
    win(`cb${i}2`, [[f + 18.0, f + 19.8]]);
  });
  win("ty", [[12, 13.6], [32.4, 34.2], [52.4, 54.2]]);
  win("scr", [[12, 14], [32.4, 34.4], [52.4, 54.4]]);
  win("ck", [[13.6, 15.4], [34.2, 35.8], [54.2, 55.8]]);
  win("ap", [[9.2, 11.2], [28.4, 30.6], [48.4, 50.6]]);
  win("ti0", [[0.3, 19.7]]);
  win("ti1", [[20.3, 39.7]]);
  win("ti2", [[40.3, 59.7]]);
  css += `@keyframes ls-exp{0%,${pct(17.4)}{opacity:0;transform:translate(0,0) scale(.3) rotate(0)}${pct(17.8)}{opacity:1}${pct(19.0)}{opacity:1;transform:translate(var(--ex),var(--ey)) rotate(var(--er)) scale(1)}${pct(19.6)},100%{opacity:0;transform:translate(var(--ex),var(--ey)) rotate(var(--er)) scale(1)}}.ls-ex{animation:ls-exp ${CY}s ease-out infinite}`;
  css += `@keyframes ls-rg{0%,${pct(17.2)}{opacity:0;transform:scale(.2)}${pct(17.6)}{opacity:.9}${pct(19.6)},100%{opacity:0;transform:scale(5)}}.ls-ring{animation:ls-rg ${CY}s ease-out infinite}`;
  return css;
}

const SPRITE = `<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<symbol id="ls-indoor" viewBox="0 0 120 44"><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"><rect x="2" y="3" width="116" height="30" rx="9"/><path d="M12 12H84M12 17H84M12 22H84" stroke-width="1"/><rect x="92" y="18" width="18" height="8" rx="2" class="ls-a"/><path d="M8 38Q60 44 112 38"/></g></symbol>
<symbol id="ls-outdoor" viewBox="0 0 80 80"><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"><rect x="3" y="4" width="74" height="68" rx="6"/><circle cx="40" cy="38" r="26"/><circle cx="40" cy="38" r="19" stroke-width="1"/><circle cx="40" cy="38" r="12" stroke-width="1"/><circle cx="40" cy="38" r="3"/><g class="ls-spin ls-a"><path d="M40 38C34 30 36 22 40 20C44 22 46 30 40 38ZM40 38C48 36 54 40 56 44C54 48 46 46 40 38ZM40 38C36 46 28 48 24 46C24 42 30 34 40 38Z"/></g></g></symbol>
<symbol id="ls-compressor" viewBox="0 0 60 80"><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M12 22Q12 8 30 8Q48 8 48 22V62Q48 74 30 74Q12 74 12 62Z"/><ellipse cx="30" cy="22" rx="18" ry="6" stroke-width="1"/><path d="M12 42Q30 50 48 42" stroke-width="1"/><path d="M24 8V0H12M36 8V0H50" class="ls-a"/></g></symbol>
<symbol id="ls-coil" viewBox="0 0 100 60"><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path class="ls-a" d="M6 8H90A5 5 0 0 1 90 18H10A5 5 0 0 0 10 28H90A5 5 0 0 1 90 38H10A5 5 0 0 0 10 48H94"/><path stroke-width="1" d="M18 4V52M28 4V52M38 4V52M48 4V52M58 4V52M68 4V52M78 4V52"/></g></symbol>
<symbol id="ls-prop" viewBox="0 0 60 60"><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><g class="ls-spin"><path d="M30 30C20 18 24 4 30 2C36 4 40 18 30 30ZM30 30C44 26 56 34 56 40C52 46 40 44 30 30ZM30 30C28 46 14 54 8 50C8 44 16 32 30 30Z"/></g><circle cx="30" cy="30" r="3" class="ls-a"/></g></symbol>
<symbol id="ls-xflow" viewBox="0 0 110 36"><g fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><rect x="2" y="4" width="106" height="28" rx="14"/><path class="ls-a" stroke-width="1" d="M16 4V32M24 4V32M32 4V32M40 4V32M48 4V32M56 4V32M64 4V32M72 4V32M80 4V32M88 4V32M96 4V32"/></g></symbol>
<symbol id="ls-pcb" viewBox="0 0 70 50"><g fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"><rect x="2" y="2" width="66" height="46" rx="3"/><rect x="10" y="10" width="18" height="12" class="ls-a"/><rect x="36" y="10" width="12" height="12"/><rect x="10" y="30" width="30" height="9"/><circle cx="56" cy="14" r="5"/></g></symbol>
<symbol id="ls-filter" viewBox="0 0 90 44"><g fill="none" stroke="currentColor" stroke-width="1.4"><rect x="2" y="2" width="86" height="40" rx="3"/><path class="ls-a" stroke-width="1" d="M2 12L88 32M2 22L88 42M2 2L88 22M30 2L88 14M2 42L88 2"/></g></symbol>
<symbol id="ls-flake" viewBox="-14 -14 28 28"><g fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M0 -12V12M-10.4 -6L10.4 6M-10.4 6L10.4 -6"/><path class="ls-a" d="M-3 -9L0 -6L3 -9M-3 9L0 6L3 9"/></g></symbol>
<symbol id="ls-fridge" viewBox="0 0 50 80"><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="2" width="38" height="74" rx="5"/><path d="M6 28H44"/><path d="M13 10V20M13 36V54" class="ls-a" stroke-width="2.2"/><path d="M10 76V79M40 76V79"/></g></symbol>
</defs></svg>`;

const D = {
  indoor: [120, 44], outdoor: [80, 80], compressor: [60, 80], coil: [100, 60], prop: [60, 60],
  xflow: [110, 36], pcb: [70, 50], filter: [90, 44], flake: [28, 28], fridge: [50, 80],
};
const mk = (s) =>
  `<svg viewBox="0 0 ${D[s][0]} ${D[s][1]}"><use href="#ls-${s}" width="${D[s][0]}" height="${D[s][1]}"/></svg>`;
const ico = (s, w) => `<span class="ls-ic" style="width:${w}px">${mk(s)}</span>`;
const G = 'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"';

const CUST = `<svg viewBox="0 0 80 112"><g ${G}><circle cx="38" cy="32" r="13"/><path d="M14 110V74Q14 56 38 56Q62 56 62 74V110"/><rect x="52" y="20" width="9" height="18" rx="2.5" transform="rotate(14 56 29)" class="ls-a"/><path d="M58 60L60 44"/><path d="M30 36Q38 43 46 36" stroke-width="1.3"/><path d="M68 14L72 10M70 24H76M68 34L72 38" class="ls-a" stroke-width="1.2"/></g></svg>`;
const SUP = `<svg viewBox="0 0 120 112"><g ${G}><circle cx="36" cy="34" r="12"/><path d="M21 33A15 15 0 0 1 51 33" class="ls-a"/><rect x="17" y="31" width="6" height="12" rx="2" class="ls-a"/><rect x="49" y="31" width="6" height="12" rx="2" class="ls-a"/><path d="M22 42Q20 54 36 52" class="ls-a" stroke-width="1.3"/><path d="M12 110V74Q12 56 36 56Q60 56 60 74V110"/><rect x="66" y="40" width="46" height="34" rx="3"/><path d="M89 74V86M78 86H100"/><path d="M72 50H106M72 56H96M72 62H102" class="ls-a" stroke-width="1.2"/><path d="M0 110H120" stroke-width="1.5"/></g></svg>`;
const ADM = `<svg viewBox="0 0 100 112"><g ${G}><circle cx="38" cy="30" r="12"/><path d="M14 110V72Q14 54 38 54Q62 54 62 72V110"/><path d="M38 54L33 70L38 94L43 70Z" class="ls-a" stroke-width="1.3"/><rect x="62" y="64" width="32" height="42" rx="3"/><rect x="72" y="60" width="12" height="8" rx="2" class="ls-a"/><path d="M68 78H88M68 86H84M68 94H80" stroke-width="1.2"/><g class="ls-ap ls-k-ap"><path d="M66 100L74 108L92 86" class="ls-a" stroke-width="3.4"/></g></g></svg>`;
const TECH = `<svg viewBox="0 0 80 112"><g ${G}><path d="M20 24A20 17 0 0 1 60 24Z" class="ls-a"/><path d="M15 24H65" class="ls-a"/><circle cx="40" cy="34" r="12"/><path d="M18 110V72Q18 54 40 54Q62 54 62 72V110"/><path d="M58 66L62 86"/><rect x="50" y="86" width="26" height="18" rx="2" class="ls-a"/><path d="M57 86V81H69V86"/><path d="M34 38Q40 43 46 38" stroke-width="1.2"/></g></svg>`;
const KEYS = `<rect x="56" y="95" width="7" height="6"/><rect x="66" y="95" width="7" height="6"/><rect x="76" y="95" width="7" height="6"/><rect x="86" y="95" width="7" height="6"/><rect x="96" y="95" width="7" height="6"/>`;
const VEND = `<svg viewBox="0 0 120 112"><g ${G}><circle cx="30" cy="30" r="12"/><path d="M8 110V72Q8 54 30 54Q52 54 52 72V110"/><rect x="58" y="38" width="52" height="36" rx="3"/><path d="M84 74V86M72 86H96"/><g class="ls-scr ls-k-scr"><path d="M66 48H102M66 54H92M66 60H98M66 66H88" class="ls-a" stroke-width="1.2"/></g><g class="ls-chk ls-k-ck"><path d="M72 58L82 68L102 46" class="ls-a" stroke-width="3.2"/></g><rect x="52" y="92" width="60" height="12" rx="2"/></g><g class="ls-keys">${KEYS}</g><g class="ls-typing ls-k-ty">${KEYS}</g><path d="M0 111H120" stroke="currentColor" stroke-width="1.5"/></svg>`;
const TICKET = `<svg viewBox="0 0 34 42" width="30" height="38"><g ${G}><rect x="2" y="2" width="30" height="38" rx="3" fill="var(--pap)"/><path d="M8 12H26M8 18H26M8 24H20" class="ls-a" stroke-width="1.3"/><path d="M8 33H18" stroke-width="2.2"/></g></svg>`;
const BOX = `<svg viewBox="0 0 48 42" width="48" height="42"><g ${G}><path d="M3 12L24 3L45 12V32L24 40L3 32Z" fill="var(--pap)"/><path d="M3 12L24 21L45 12M24 21V40"/><path d="M14 8L35 17" class="ls-a"/></g></svg>`;

const FLOATS = [
  ["indoor", 170, 150, 110, 14, -3, 30, 22, 6], ["outdoor", 620, 150, 78, 15, -6, -26, 26, -10],
  ["compressor", 34, 206, 44, 12, -2, 22, -24, 12], ["coil", 556, 262, 92, 14, -8, -26, -18, 8],
  ["prop", 210, 262, 44, 10, -4, 20, 26, -24], ["xflow", 546, 176, 96, 13, -9, 24, -14, 5],
  ["pcb", 688, 262, 56, 11, -1, -20, 20, 12], ["filter", 300, 70, 80, 15, -10, 22, 18, 5],
  ["flake", 160, 330, 24, 10, -6, -14, -18, -32], ["flake", 604, 336, 22, 9, -2, 14, -16, 28],
];
const EXPLODE = [
  ["pcb", 64, -20, -120, -40, 160], ["filter", 84, 50, -50, -100, -140], ["xflow", 96, -10, 80, -120, 100],
  ["prop", 50, 40, 150, -40, 200], ["coil", 84, 30, 130, 40, -120], ["compressor", 40, 0, 20, -150, 90],
];
const ITEMS = [
  null,
  { n: "split AC", s: "indoor", w: 34, dw: 70, o: "IDC_5107", p: "the AC", done: "AC" },
  { n: "fridge", s: "fridge", w: 16, dw: 30, o: "IDC_5108", p: "the fridge", done: "Fridge" },
];

const el = (cls, html, st = "") => `<div class="${cls}" style="${st}">${html}</div>`;

function buildArt() {
  let floats = "";
  FLOATS.forEach((p) => {
    floats += el(
      "ls-fp ls-drift",
      mk(p[0]),
      `left:${p[1]}px;top:${p[2]}px;width:${p[3]}px;--d:${p[4]}s;--dl:${p[5]}s;--dx:${p[6]}px;--dy:${p[7]}px;--r:${p[8]}deg`,
    );
  });

  const paths = [PTOP, PST, PTA, PAV, PBX, PSA, PDL];
  let s = `<svg class="ls-route" viewBox="0 0 800 500"><g fill="none" stroke="var(--acc)" stroke-width="1.3" stroke-dasharray="4 6" opacity=".45">${paths
    .map((p) => `<path d="${p}"/>`)
    .join("")}</g></svg>`;
  s += el("ls-it", SUP, "left:40px;top:20px;width:105px");
  s += el("ls-it", CUST, "left:690px;top:20px;width:70px");
  s += el("ls-it", TECH, "left:40px;top:374px;width:70px");
  s += el("ls-it", ADM, "left:356px;top:374px;width:88px");
  s += el("ls-it", VEND, "left:650px;top:374px;width:105px");
  s += el("ls-lbl", "INDcool SUPPORT", "left:20px;top:4px;width:150px");
  s += el("ls-lbl", "CUSTOMER", "left:675px;top:4px;width:100px");
  s += el("ls-lbl", "TECHNICIAN", "left:15px;top:480px;width:120px");
  s += el("ls-lbl", "ADMIN", "left:350px;top:480px;width:100px");
  s += el("ls-lbl", "VENDOR", "left:650px;top:480px;width:105px");
  s += el("ls-ttl ls-k-ti0", "FLOW 1 OF 3 &middot; AC NOT COOLING, SPARE PART ORDERED");
  s += el("ls-ttl ls-k-ti1", "FLOW 2 OF 3 &middot; CUSTOMER ORDERS A SPLIT AC");
  s += el("ls-ttl ls-k-ti2", "FLOW 3 OF 3 &middot; CUSTOMER ORDERS A FRIDGE");
  // flow 1 bubbles
  s += el("ls-bub ls-k-c1", "My AC is not cooling!", "right:122px;top:30px");
  s += el("ls-bub ls-k-s1", "Complaint registered IDC_4821 &#10003;", "left:158px;top:30px");
  s += el("ls-bub ls-k-tb1", "Need a PCB board", "left:118px;top:344px");
  s += el("ls-bub ls-k-ab", "Part approved &#10003;", "left:452px;top:376px");
  s += el("ls-bub ls-k-v1", "Punching order&hellip;", "left:660px;top:344px");
  s += el("ls-bub ls-k-v2", "Order placed &#10003;", "left:660px;top:344px");
  s += el("ls-bub ls-k-tb2", "Spares arrived!", "left:118px;top:344px");
  s += el("ls-bub ls-k-c2", "Cooling again. Thank you!", "right:122px;top:30px");
  // flows 2 and 3 bubbles
  [1, 2].forEach((i) => {
    const t = ITEMS[i];
    s += el(`ls-bub ls-k-cb${i}1`, `I want to buy a ${t.n}${ico(t.s, t.w)}`, "right:122px;top:30px");
    s += el(`ls-bub ls-k-sb${i}`, `Order ${t.o} placed &#10003;`, "left:158px;top:30px");
    s += el(`ls-bub ls-k-ab${i}`, "Stock OK. Invoice sent &#10003;", "left:452px;top:376px");
    s += el(`ls-bub ls-k-vb${i}1`, `Packing ${t.p}&hellip;`, "left:660px;top:344px");
    s += el(`ls-bub ls-k-vb${i}2`, "Dispatched &#10003;", "left:660px;top:344px");
    s += el(`ls-bub ls-k-cb${i}2`, `${t.done} delivered. Thank you!`, "right:122px;top:30px");
  });
  // things that travel
  ["t1", "t2", "t3", "t4"].forEach((k) => (s += el(`ls-tr ls-tk ls-${k}`, TICKET)));
  s += el("ls-tr ls-bx ls-bx", BOX);
  [1, 2].forEach((i) => {
    [`o${i}1`, `o${i}2`, `o${i}3`].forEach((k) => (s += el(`ls-tr ls-tk ls-${k}`, TICKET)));
    const t = ITEMS[i];
    s += el(`ls-tr ls-dl ls-d${i}`, `<div style="width:${t.dw}px;color:#fff">${mk(t.s)}</div>`);
  });
  s += el("ls-ring", "");
  EXPLODE.forEach((e) => {
    const d = D[e[0]];
    const w = e[1] * 0.62;
    const hh = (w * d[1]) / d[0];
    s += el(
      "ls-ex",
      mk(e[0]),
      `width:${w}px;left:${112 - w / 2}px;top:${450 - hh / 2}px;--ex:${e[2]}px;--ey:${e[3]}px;--er:${e[4]}deg`,
    );
  });

  return `${SPRITE}<div class="ls-floats">${floats}</div><div class="ls-story">${s}</div>`;
}

const ART_HTML = buildArt();
const CSS_TEXT = buildCss();

export default function LoginScene({ children }) {
  const wrapRef = useRef(null);
  const stageRef = useRef(null);

  useEffect(() => {
    const wrap = wrapRef.current;
    const stage = stageRef.current;
    if (!wrap || !stage) return undefined;
    const mq = window.matchMedia("(min-width: 768px)");
    const fit = () => {
      if (!mq.matches) {
        stage.style.transform = "";
        return;
      }
      const s = Math.max(0.7, Math.min(wrap.clientWidth / 800, wrap.clientHeight / 500, 1.6));
      stage.style.transform = `translate(-50%,-50%) scale(${s})`;
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(wrap);
    mq.addEventListener("change", fit);
    return () => {
      ro.disconnect();
      mq.removeEventListener("change", fit);
    };
  }, []);

  return (
    <div ref={wrapRef} className="ls-wrap">
      <style>{CSS_TEXT}</style>
      <div ref={stageRef} className="ls-stage">
        <div className="ls-art" aria-hidden="true" dangerouslySetInnerHTML={{ __html: ART_HTML }} />
        <div className="ls-card">{children}</div>
      </div>
    </div>
  );
}
