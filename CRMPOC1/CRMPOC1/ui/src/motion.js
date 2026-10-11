// Click movement for the whole CRM: a ring spreads where you press. Movement is on unless the person turned it off
// with the Movement switch (kept in localStorage as "sales_motion").
export function installClickEffects() {
  try {
    if (localStorage.getItem("sales_motion") === "off") document.documentElement.setAttribute("data-s-motion", "off");
  } catch { /* storage may be blocked: movement stays on */ }
  document.addEventListener("pointerdown", (e) => {
    if (document.documentElement.getAttribute("data-s-motion") === "off") return;
    const hit = e.target instanceof Element ? e.target.closest('button, a, [role="button"], summary, select, input[type="checkbox"], input[type="radio"], label') : null;
    if (!hit || hit.disabled || hit.getAttribute("aria-disabled") === "true") return;
    const ring = document.createElement("span");
    ring.className = "crm-click";
    ring.style.left = `${e.clientX}px`;
    ring.style.top = `${e.clientY}px`;
    document.body.appendChild(ring);
    setTimeout(() => ring.remove(), 650);
  }, { capture: true, passive: true });
}
