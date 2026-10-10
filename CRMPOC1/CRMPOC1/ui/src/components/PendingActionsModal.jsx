import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import "./pending-actions.css";

// Clean line icons (24x24, drawn with currentColor)
const ICONS = {
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 8-3 8h18s-3-1-3-8"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
  complaints: '<path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M12 7v4M12 14h.01"/>',
  calls: '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/>',
  services: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z"/>',
  installations: '<rect x="3" y="4" width="18" height="8" rx="2"/><path d="M7 16c0 1.5-1 2-1 4M12 16c0 1.5-1 2-1 4M17 16c0 1.5-1 2-1 4"/>',
  claims: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
  orders: '<path d="M21 8l-9-5-9 5v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
  bids: '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>',
  sales: '<path d="M4 19V9M10 19V5M16 19v-8M22 19H2"/>',
  lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  partner_registrations: '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><path d="M17 8v6M14 11h6"/>',
  flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  check: '<path d="M5 12l4 4 10-10"/>',
  checks: '<path d="M3 12l4 4 6-8"/><path d="M11 16l2 2 8-10"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
};

const MODULE_LABELS = {
  complaints: "Complaint",
  installations: "Installation",
  services: "Service",
  orders: "Order",
  bids: "Bid",
  sales: "Sales",
  claims: "Claim",
  calls: "Call",
  partner_registrations: "Partner",
};
const TAB_LABELS = {
  complaints: "Complaints",
  installations: "Installation",
  services: "Service",
  orders: "Orders",
  bids: "Bids",
  sales: "Sales",
  claims: "Claims",
  calls: "Calls",
  partner_registrations: "Partners",
};

const HIGH_PRIORITY = /^HIGH PRIORITY\s*[-:]\s*/i;

function Icon({ name, className = "" }) {
  return <svg className={`pa-ico ${className}`} viewBox="0 0 24 24" aria-hidden="true" dangerouslySetInnerHTML={{ __html: ICONS[name] || ICONS.bell }} />;
}

function formatWhen(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const diffMs = Date.now() - date.getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleString();
}

// the server sends times in UTC without a zone mark
function serverTime(value) {
  const text = String(value || "");
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(text) ? text : `${text}Z`);
}

const isoDay = (date) => date.toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });

// A bid reminder has a time limit (due_at). The pill says how much is left, and goes from blue to orange to red.
function timePill(item) {
  if (!item.due_at || !/^bid_/.test(item.action_type || "")) return null;
  const due = serverTime(item.due_at);
  if (Number.isNaN(due.getTime())) return null;
  if (item.action_type === "bid_accept") {
    const ms = due.getTime() - Date.now();
    if (ms <= 0) return { tone: "red", text: "Time is up" };
    const hours = ms / 3600000;
    const text = hours >= 1 ? `${Math.ceil(hours)} h left` : `${Math.max(1, Math.ceil(ms / 60000))} min left`;
    return { tone: hours > 24 ? "blue" : hours > 2 ? "orange" : "red", text };
  }
  const days = Math.round((new Date(isoDay(due)) - new Date(isoDay(new Date()))) / 86400000);
  if (days <= 0) return { tone: "red", text: "LAST DAY" };
  if (days === 1) return { tone: "orange", text: "Last date tomorrow" };
  return { tone: "amber", text: `${days} days left` };
}

function dayGroup(value) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "earlier";
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  if (d >= start) return "today";
  start.setDate(start.getDate() - 1);
  return d >= start ? "yesterday" : "earlier";
}

function useCountUp(target) {
  const [value, setValue] = useState(target);
  const last = useRef(target);
  useEffect(() => {
    const from = last.current;
    const t0 = performance.now();
    let raf;
    const step = (now) => {
      const k = Math.min(1, (now - t0) / 500);
      const eased = 1 - (1 - k) ** 3;
      const v = Math.round(from + (target - from) * eased);
      last.current = v;
      setValue(v);
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target]);
  return value;
}

const GROUP_TITLES = { pri: "High priority - handle first", today: "Today", yesterday: "Yesterday", earlier: "Earlier" };

export default function PendingActionsModal({
  open,
  onClose,
  items = [],
  total = 0,
  onMarkRead,
  onLoadMore,
  canLoadMore = false,
  loadingMore = false,
}) {
  const navigate = useNavigate();
  const [filter, setFilter] = useState("all");
  const [onlyUnread, setOnlyUnread] = useState(true);
  const [leaving, setLeaving] = useState(() => new Set());
  const [picked, setPicked] = useState(() => new Set());
  const [handled, setHandled] = useState(0);
  const shownTotal = useCountUp(total);
  // The parent passes a new onClose function on every render; keep it in a ref so the popup does not
  // reset its filters and counters each time the list refreshes.
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    if (!open) return undefined;
    setFilter("all");
    setOnlyUnread(true);
    setHandled(0);
    setPicked(new Set());
    setLeaving(new Set());
    const onKey = (e) => {
      if (e.key === "Escape") closeRef.current?.();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open]);

  const rows = useMemo(
    () => items.map((item) => ({ ...item, priority: HIGH_PRIORITY.test(item.message || ""), text: (item.message || "").replace(HIGH_PRIORITY, "") })),
    [items],
  );
  const base = useMemo(() => (onlyUnread ? rows.filter((r) => !r.is_read) : rows), [rows, onlyUnread]);
  const counts = useMemo(() => {
    const c = { all: base.length, pri: base.filter((r) => r.priority).length };
    base.forEach((r) => {
      c[r.module] = (c[r.module] || 0) + 1;
    });
    return c;
  }, [base]);
  const unreadLoaded = rows.filter((r) => !r.is_read).length;
  const modules = [...new Set(base.map((r) => r.module))];

  const visible = rows.filter((r) => {
    if (filter === "pri" && !r.priority) return false;
    if (filter !== "all" && filter !== "pri" && r.module !== filter) return false;
    if (onlyUnread && r.is_read) return false;
    return true;
  });
  const groups = ["pri", "today", "yesterday", "earlier"]
    .map((g) => ({ key: g, list: visible.filter((r) => (g === "pri" ? r.priority : !r.priority && dayGroup(r.occurred_at) === g)) }))
    .filter((g) => g.list.length);

  if (!open) return null;

  function toggle(item) {
    if (item.is_read) return;
    setPicked((s) => {
      const next = new Set(s);
      if (next.has(item.id)) next.delete(item.id);
      else next.add(item.id);
      return next;
    });
  }

  function openAction(item) {
    const locked = !!item.due_at;
    if (!locked) {
      setLeaving((s) => new Set(s).add(item.id));
      setHandled((h) => h + 1);
    }
    setTimeout(() => {
      if (!locked) onMarkRead?.([item.id]);  // a bid reminder stays until the vendor answers
      onClose?.();
      navigate(item.href);
    }, locked ? 0 : 260);
  }

  function proceed() {
    const ids = [...picked].filter((id) => rows.some((r) => r.id === id && !r.is_read));
    if (!ids.length) return;
    setHandled((h) => h + ids.length);
    setPicked(new Set());
    onMarkRead?.(ids);
  }

  let n = 0;
  return (
    <div className="pa-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}>
      <div className="pa-modal" role="dialog" aria-modal="true" aria-labelledby="pa-title">
        <div className="pa-head">
          <div className="pa-head-row">
            <div className="pa-logo"><Icon name="bell" /></div>
            <div className="pa-head-text">
              <h3 id="pa-title">Actions pending for you</h3>
              <small>{total === 0 ? "Nothing waiting for you" : "Open an item to jump straight to the work"}</small>
            </div>
            <div className="pa-count">
              <b>{shownTotal.toLocaleString("en-IN")}</b>
              <span>UNREAD</span>
            </div>
            <button type="button" className="pa-close" onClick={onClose} aria-label="Close"><Icon name="close" /></button>
          </div>
        </div>

        <div className="pa-sum">
          <span><b>{total.toLocaleString("en-IN")}</b> unread</span>
          {counts.pri > 0 && <span className="pa-sum-pri"><b>{counts.pri}</b> high priority</span>}
          <span><b>{unreadLoaded}</b> unread in this list</span>
          <span className="pa-bar">
            {handled} handled now
            <i><u style={{ width: `${Math.min(100, handled * 10)}%` }} /></i>
          </span>
        </div>

        <div className="pa-tabs" role="tablist">
          <button type="button" role="tab" className={`pa-tab${filter === "all" ? " on" : ""}`} onClick={() => setFilter("all")}>All<em>{counts.all}</em></button>
          {counts.pri > 0 && (
            <button type="button" role="tab" className={`pa-tab pa-tab-pri${filter === "pri" ? " on" : ""}`} onClick={() => setFilter("pri")}>High priority<em>{counts.pri}</em></button>
          )}
          {modules.map((m) => (
            <button key={m} type="button" role="tab" className={`pa-tab${filter === m ? " on" : ""}`} onClick={() => setFilter(m)}>{TAB_LABELS[m] || m}<em>{counts[m]}</em></button>
          ))}
          <label className="pa-switch"><input type="checkbox" checked={onlyUnread} onChange={(e) => setOnlyUnread(e.target.checked)} />Unread only</label>
        </div>

        <div className="pa-list">
          {rows.length === 0 && (
            <div className="pa-empty">
              <div className="pa-empty-ring"><Icon name="check" /></div>
              <h4>You are all caught up</h4>
              <p>No pending actions right now.</p>
            </div>
          )}
          {rows.length > 0 && total === 0 && unreadLoaded === 0 && (
            <div className="pa-done"><Icon name="check" /> All caught up. Everything below is already marked as read.</div>
          )}
          {rows.length > 0 && visible.length === 0 && (
            <div className="pa-empty"><h4>Nothing in this view</h4><p>Try another tab or turn off the unread filter.</p></div>
          )}
          {groups.map((g) => (
            <div key={g.key}>
              <div className={`pa-gh${g.key === "pri" ? " pri" : ""}`}>{g.key === "pri" && <Icon name="flag" />}{GROUP_TITLES[g.key]}</div>
              {g.list.map((item) => {
                const i = n++;
                const pill = timePill(item);
                const locked = !!item.due_at;
                const cls = ["pa-card", item.priority && "pri", item.is_read && "read", leaving.has(item.id) && "gone", picked.has(item.id) && "picked"].filter(Boolean).join(" ");
                return (
                  <div key={item.id} className={cls} style={{ "--i": Math.min(i, 14) }}>
                    <div className="pa-tile">
                      <Icon name={item.module} />
                      <span className="pa-ud" />
                    </div>
                    <div className="pa-body">
                      <div className="pa-meta">
                        <span className="pa-k">{MODULE_LABELS[item.module] || item.module}</span>
                        {item.priority && <span className="pa-hp">High priority</span>}
                        <span className="pa-tm"><Icon name="clock" />{formatWhen(item.occurred_at)}</span>
                      </div>
                      <div className="pa-tt">{item.title}{pill && <span className={`pa-time ${pill.tone}`}>{pill.text}</span>}</div>
                      <div className="pa-ms">{item.text}</div>
                      {item.entity_status && <span className="pa-st">Status: {item.entity_status}</span>}
                    </div>
                    <div className="pa-ac">
                      {locked ? (
                        <span className="pa-lock" title="This stays here until you answer"><Icon name="lock" />Stays until you answer</span>
                      ) : (
                      <label className={`pa-pick${item.is_read ? " is-read" : ""}`} title={item.is_read ? "Already read" : "Tick to mark as read"}>
                        <input type="checkbox" checked={item.is_read || picked.has(item.id)} disabled={item.is_read} onChange={() => toggle(item)} />
                        <span className="pa-box"><Icon name="check" /></span>
                        <span className="pa-pick-t">{item.is_read ? "Read" : "Mark read"}</span>
                      </label>
                      )}
                      <button type="button" className="pa-go" onClick={() => openAction(item)}>{item.action_label}<Icon name="arrow" /></button>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        <div className="pa-foot">
          <span className="pa-hint">{rows.length} shown, {total.toLocaleString("en-IN")} unread in total</span>
          {canLoadMore && (
            <button type="button" className="pa-btn" onClick={onLoadMore} disabled={loadingMore}>{loadingMore ? "Loading..." : "Load more"}</button>
          )}
          <button type="button" className="pa-btn pa-mark" onClick={proceed} disabled={picked.size === 0}>
            <Icon name="check" />{picked.size ? `Proceed (${picked.size} ticked)` : "Tick items to proceed"}
          </button>
        </div>
      </div>
    </div>
  );
}
