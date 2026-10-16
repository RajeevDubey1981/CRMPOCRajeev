import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { announceQueriesChanged, queriesApi } from "../../api/queries.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import DateRangeFilter from "../../components/DateRangeFilter.jsx";
import QueriesDashboard from "../../components/queries/QueriesDashboard.jsx";
import RaiseQueryModal from "../../components/queries/RaiseQueryModal.jsx";
import { AddPeopleModal, ForwardModal, roleLabel } from "../../components/queries/QueryPeopleModals.jsx";
import { Mark, isTypedDay, isTypedNumber } from "../../components/queries/queryHighlight.jsx";
import { STATUS_STYLE, timeAgo } from "../../components/queries/useQuerySummary.js";
import { isQueryStaffRole } from "../../utils/roles.js";

const FILTERS = [
  { key: "Active", label: "Active" },
  { key: "Open", label: "Waiting for reply" },
  { key: "Answered", label: "Answered" },
  { key: "Closed", label: "Closed" },
  { key: "", label: "All" },
];

const PRIORITY_STYLE = { urgent: "bg-rose-600 text-white", high: "bg-orange-500 text-white" };
const PRIORITY_LABEL = { urgent: "Urgent", high: "High priority" };
const EVENT_DOT = { forward: "bg-violet-500", member: "bg-sky-500", cc: "bg-sky-500", removed: "bg-slate-500", priority: "bg-orange-500", alarm: "bg-rose-600", closed: "bg-emerald-600", reopened: "bg-amber-500", reply: "bg-indcool-blue", start: "bg-indcool-blue" };

// "2026-10-12" -> "12 Oct 2026" (a plain day, so no time zone shift)
function dayText(iso) {
  const [y, m, d] = String(iso || "").split("-").map(Number);
  if (!y || !m || !d) return "";
  return new Date(y, m - 1, d).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function QueryNo({ no, hit = false }) {
  if (!no) return null;
  return (
    <span className={`shrink-0 rounded-md px-2 py-0.5 text-xs font-bold tracking-wide ${hit ? "bg-yellow-300 text-slate-900 ring-2 ring-yellow-400" : "bg-indcool-navy text-white"}`} title="Query number">
      {no}
    </span>
  );
}

function RaisedDate({ day, hit = false }) {
  if (!day) return null;
  return (
    <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium ${hit ? "border-yellow-400 bg-yellow-200 text-slate-900" : "border-sky-200 bg-sky-50 text-indcool-navy"}`} title="The day it was raised">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 10h18" /></svg>
      Raised {dayText(day)}
    </span>
  );
}

function StatusChip({ status }) {
  return <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_STYLE[status] || "bg-slate-100 text-slate-600"}`}>{status}</span>;
}

function PriorityChip({ priority }) {
  if (!PRIORITY_LABEL[priority]) return null;
  return <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${PRIORITY_STYLE[priority]}`}>{PRIORITY_LABEL[priority]}</span>;
}

function BellIcon({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M10.3 21a1.9 1.9 0 0 0 3.4 0" />
    </svg>
  );
}

function leftText(q) {
  if (q.hours_left == null) return "";
  const h = Math.floor(q.hours_left);
  const m = Math.round((q.hours_left - h) * 60);
  return h > 0 ? `${h} h ${m} m` : `${m} min`;
}

function QueryList({ rows, activeId, staff, loading, term = "", numberOn = false, dateOn = false }) {
  if (loading && rows.length === 0) return <p className="p-4 text-sm text-slate-500">Loading...</p>;
  if (rows.length === 0) return <p className="p-4 text-sm text-slate-500">No queries here.</p>;
  return (
    <ul className="divide-y divide-slate-100">
      {rows.map((q) => (
        <li key={q.id}>
          <Link
            to={`/queries/${q.id}`}
            className={`block border-l-4 px-3 py-2.5 transition-colors hover:bg-sky-50 ${String(q.id) === String(activeId) ? "bg-sky-50" : ""} ${q.alarm_for_me ? "border-l-rose-600 bg-rose-50/60" : q.priority === "urgent" ? "border-l-rose-500" : q.priority === "high" ? "border-l-orange-400" : "border-l-transparent"}`}
          >
            <div className="flex items-start justify-between gap-2">
              <span className={`text-sm ${q.unread_count > 0 ? "font-bold text-slate-900" : "font-medium text-slate-800"}`}><Mark text={q.subject} term={term} /></span>
              <div className="flex shrink-0 items-center gap-1.5">
                <QueryNo no={q.query_no} hit={numberOn || isTypedNumber(term, q.query_no, q.id)} />
                {q.unread_count > 0 && <span className="rounded-full bg-rose-600 px-1.5 py-0.5 text-[10px] font-bold text-white">{q.unread_count} new</span>}
              </div>
            </div>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
              <StatusChip status={q.status} />
              <PriorityChip priority={q.priority} />
              {q.alarm_for_me ? <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-bold text-rose-700">No reply in 24 h</span>
                : q.overdue ? <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-semibold text-rose-700">Overdue</span>
                : q.status === "Open" && q.hours_left != null && q.hours_left < 6 ? <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">{leftText(q)} left</span> : null}
              {(staff || q.holder_id) && <span className="font-medium text-slate-700">{staff ? <Mark text={q.owner_name} term={term} /> : ""}</span>}
              {q.holder_name && <span title="Who has to answer it">→ <Mark text={q.holder_name} term={term} /></span>}
              {q.member_count > 1 && <span>· {q.member_count} people</span>}
              <span>{q.category}</span>
              {q.related_to && <span>· <Mark text={q.related_to} term={term} /></span>}
              <span className="ml-auto">{timeAgo(q.last_message_at)}</span>
            </div>
            <div className="mt-1.5">
              <RaisedDate day={q.raised_on} hit={dateOn || isTypedDay(term, q.raised_on)} />
            </div>
            <p className="mt-1 line-clamp-2 text-xs text-slate-600">
              {q.last_sender_name ? `${q.last_sender_name}: ` : ""}<Mark text={q.last_message_preview} term={term} />
            </p>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function History({ events }) {
  if (!events.length) return <p className="p-4 text-sm text-slate-500">Nothing yet.</p>;
  return (
    <ol className="space-y-0 px-5 py-4">
      {events.slice().reverse().map((e, i) => (
        <li key={`${e.id}-${i}`} style={{ "--i": Math.min(i, 10) }} className="s-slide relative border-l border-slate-200 pb-4 pl-5 text-sm last:border-transparent last:pb-0">
          <span className={`absolute -left-[6px] top-1 h-3 w-3 rounded-full ring-4 ring-white ${EVENT_DOT[e.kind] || "bg-slate-400"}`} />
          <div className="text-slate-800">{e.text}</div>
          <div className="text-xs text-slate-400">{new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(String(e.at)) ? e.at : `${e.at}Z`).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" })}</div>
        </li>
      ))}
    </ol>
  );
}

function People({ thread, busy, onAdd, onRemove, onAddBack }) {
  const inside = thread.members.filter((m) => m.active);
  const out = thread.members.filter((m) => !m.active);
  return (
    <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
      <span className="font-semibold text-slate-500">In this conversation:</span>
      {inside.map((m) => (
        <span key={m.user_id} className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white py-0.5 pl-2.5 pr-1.5 text-slate-700">
          {m.is_holder && <span title="Has to answer" className="text-amber-600">★</span>}
          <b className="font-semibold">{m.name}</b>
          <span className="text-slate-400">{m.kind === "cc" ? "CC" : m.kind === "owner" ? "asked" : roleLabel(m.role)}</span>
          {thread.can_manage && !m.is_holder && (
            <button type="button" disabled={busy} title={`Take ${m.name} out for a private talk`} onClick={() => onRemove(m)} className="grid h-4 w-4 place-items-center rounded-full bg-slate-100 text-[10px] leading-none text-slate-500 hover:bg-rose-100 hover:text-rose-700">✕</button>
          )}
        </span>
      ))}
      {out.map((m) => (
        <span key={`out-${m.user_id}`} className="inline-flex items-center gap-1 rounded-full border border-dashed border-slate-300 bg-slate-50 py-0.5 pl-2.5 pr-1.5 text-slate-500">
          <span className="line-through">{m.name}</span><span>out</span>
          {thread.can_manage && <button type="button" disabled={busy} onClick={() => onAddBack(m)} className="rounded-full bg-sky-100 px-1.5 text-[10px] font-semibold text-sky-800 hover:bg-sky-200">Add back</button>}
        </span>
      ))}
      {thread.can_manage && <button type="button" disabled={busy} onClick={onAdd} className="rounded-full border border-brand-600 px-2.5 py-0.5 font-semibold text-brand-700 hover:bg-sky-50">+ Add or CC</button>}
    </div>
  );
}

function Thread({ id, staff, onChanged }) {
  const [thread, setThread] = useState(null);
  const [err, setErr] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("chat");
  const [forwarding, setForwarding] = useState(false);
  const [adding, setAdding] = useState(false);
  const endRef = useRef(null);

  const load = useCallback(() => {
    queriesApi.get(id)
      .then((data) => { setThread(data); setErr(""); announceQueriesChanged(); })
      .catch((e) => setErr(e.response?.status === 404 ? "This query was not found, or you are not in this conversation." : "Could not open this query."));
  }, [id]);

  useEffect(() => {
    setThread(null);
    setText("");
    setTab("chat");
    load();
    const timer = setInterval(load, 30000);
    return () => clearInterval(timer);
  }, [load]);

  useEffect(() => { endRef.current?.scrollIntoView({ block: "end" }); }, [thread?.messages?.length, tab]);

  async function act(fn) {
    setBusy(true);
    setErr("");
    try {
      const data = await fn();
      setThread(data);
      announceQueriesChanged();
      onChanged?.();
      return true;
    } catch (e) {
      const detail = e.response?.data?.detail;
      setErr(Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || "That did not work. Try again");
      return false;
    } finally {
      setBusy(false);
    }
  }
  const done = (data) => { setThread(data); setForwarding(false); setAdding(false); announceQueriesChanged(); onChanged?.(); };

  async function send(e) {
    e?.preventDefault();
    if (!text.trim()) return;
    if (await act(() => queriesApi.reply(id, text))) setText("");
  }
  function takeOut(m) {
    if (!window.confirm(`Take ${m.name} out of this conversation?\n\nThey will not see it, or anything said while they are out, until you add them back. The others can talk privately.`)) return;
    act(() => queriesApi.removeMember(id, m.user_id));
  }

  if (err && !thread) return <div className="p-6 text-sm text-rose-700">{err}</div>;
  if (!thread) return <div className="p-6 text-sm text-slate-500">Loading...</div>;

  const waiting = thread.status === "Open" && thread.hours_left != null;
  const pct = waiting ? Math.max(0, Math.min(100, 100 - (thread.hours_left / 24) * 100)) : 0;

  return (
    <div className="flex min-h-[24rem] flex-col">
      <div className="border-b border-slate-200 px-4 py-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-semibold text-slate-800">{thread.subject}</h2>
              <StatusChip status={thread.status} />
              <PriorityChip priority={thread.priority} />
            </div>
            <div className="mt-1 text-xs text-slate-500">
              {staff && <span className="mr-2 font-medium text-slate-700">{thread.owner_name} ({roleLabel(thread.owner_role)})</span>}
              {thread.category}{thread.related_to ? ` · ${thread.related_to}` : ""} · started {timeAgo(thread.created_at)}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {thread.can_set_priority && (
              <select aria-label="Priority" value={thread.priority} disabled={busy} onChange={(e) => act(() => queriesApi.setPriority(id, e.target.value))} className="rounded-md border border-slate-300 px-2 py-1 text-xs">
                <option value="normal">Priority: Normal</option><option value="high">Priority: High</option><option value="urgent">Priority: Urgent</option>
              </select>
            )}
            {thread.can_forward && <button type="button" disabled={busy} onClick={() => setForwarding(true)} className="s-press rounded-md bg-brand-600 px-3 py-1 text-xs font-semibold text-white hover:bg-brand-700 disabled:opacity-60">↪ Forward</button>}
            {thread.can_close && <button type="button" disabled={busy} onClick={() => act(() => queriesApi.close(id))} className="s-press rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60">Mark as solved</button>}
            {thread.can_reopen && <button type="button" disabled={busy} onClick={() => act(() => queriesApi.reopen(id))} className="s-press rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60">Reopen</button>}
          </div>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-600">
          <QueryNo no={thread.query_no} />
          <RaisedDate day={thread.raised_on} />
        </div>
        {thread.holder_name && thread.status !== "Closed" && (
          <div className="mt-2 rounded-md bg-slate-100 px-3 py-1.5 text-xs text-slate-700">With now: <b>{thread.holder_name}</b> ({roleLabel(thread.holder_role)})</div>
        )}
        <People thread={thread} busy={busy} onAdd={() => setAdding(true)} onRemove={takeOut} onAddBack={(m) => act(() => queriesApi.addMember(id, m.user_id, m.kind === "cc" ? "cc" : "member", true))} />
        {thread.private_now && (
          <div className="s-pop mt-2 rounded-md border border-violet-200 bg-violet-50 px-3 py-1.5 text-xs text-violet-800">
            🔒 Someone is out of this conversation. What you write now is private to the people in it, until you add them back.
          </div>
        )}
      </div>

      {thread.alarm_for_me && (
        <div className="q-alarm mx-4 mt-3 flex flex-wrap items-center gap-3 rounded-lg bg-rose-600 px-4 py-3 text-white">
          <span className="q-bell grid h-10 w-10 shrink-0 place-items-center rounded-full bg-white/20"><BellIcon /></span>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-bold">This query has waited over 24 hours for you</div>
            <div className="text-xs text-white/90">Answer it, or forward it to the right person.</div>
          </div>
        </div>
      )}
      {waiting && !thread.alarm_for_me && (
        <div className={`mx-4 mt-3 flex flex-wrap items-center gap-3 rounded-lg px-3 py-2 text-xs ${thread.overdue ? "bg-rose-50 text-rose-700" : thread.hours_left < 6 ? "bg-amber-50 text-amber-800" : "bg-emerald-50 text-emerald-800"}`}>
          <span>{thread.overdue ? "No reply for 24 hours" : "Reply due within"}</span>
          <b className="text-base tabular-nums">{thread.overdue ? "OVERDUE" : leftText(thread)}</b>
          <span className="h-2 min-w-[6rem] flex-1 overflow-hidden rounded-full bg-black/10"><span className="block h-full rounded-full bg-current transition-all" style={{ width: `${thread.overdue ? 100 : pct}%` }} /></span>
          <span>{thread.holder_name ? `Alarm rings for ${thread.holder_name}` : "Alarm rings for the Admin team"}{thread.alarm_count ? ` · rung ${thread.alarm_count}×` : ""}</span>
          {thread.can_ring && thread.overdue && <button type="button" disabled={busy} onClick={() => act(() => queriesApi.ring(id))} className="rounded-md bg-rose-600 px-2.5 py-1 font-semibold text-white hover:bg-rose-700 disabled:opacity-60">Ring again</button>}
        </div>
      )}

      {thread.can_see_history && (
        <div className="mx-4 mt-3 flex gap-1 border-b border-slate-200 text-sm">
          {[["chat", "Conversation"], ["hist", `History (${thread.events.length})`]].map(([k, l]) => (
            <button key={k} type="button" onClick={() => setTab(k)} className={`-mb-px border-b-2 px-3 py-1.5 font-semibold ${tab === k ? "border-indcool-navy text-indcool-navy" : "border-transparent text-slate-500 hover:text-slate-700"}`}>{l}</button>
          ))}
        </div>
      )}

      {tab === "hist" && thread.can_see_history ? <History events={thread.events} /> : (
        <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 px-4 py-3" style={{ maxHeight: "calc(100vh - 26rem)", minHeight: "10rem" }}>
          {thread.messages.map((m, index) => {
            const newOnes = thread.unread_count || 0;
            const isNew = !m.mine && index >= thread.messages.length - newOnes;
            return (
              <div key={m.id} className={`flex ${m.mine ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm shadow-sm ${m.mine ? "bg-indcool-navy text-white" : m.from_staff ? "border border-emerald-200 bg-emerald-50 text-slate-800" : "border border-slate-200 bg-white text-slate-800"} ${m.is_private ? "ring-1 ring-violet-300" : ""}`}>
                  <div className={`mb-0.5 text-[11px] font-semibold ${m.mine ? "text-slate-200" : "text-slate-500"}`}>
                    {m.mine ? "You" : m.sender_name}{!m.mine && m.from_staff ? " · Admin team" : ""} · {timeAgo(m.created_at)}
                    {m.is_private && <span className={`ml-1 rounded px-1 text-[10px] ${m.mine ? "bg-violet-400/40 text-white" : "bg-violet-100 text-violet-700"}`}>🔒 private{m.hidden_from?.length ? `, not shown to ${m.hidden_from.join(", ")}` : ""}</span>}
                    {isNew && <span className="ml-1 rounded bg-rose-600 px-1 text-[10px] text-white">new</span>}
                  </div>
                  <div className="whitespace-pre-wrap break-words">{m.body}</div>
                </div>
              </div>
            );
          })}
          <div ref={endRef} />
        </div>
      )}

      {thread.can_reply ? (
        <form onSubmit={send} className="border-t border-slate-200 p-3">
          {err && <div className="mb-2 rounded-md bg-rose-50 px-3 py-1.5 text-sm text-rose-700">{err}</div>}
          <textarea
            rows={3}
            value={text}
            maxLength={4000}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send(e); }}
            placeholder={thread.status === "Closed" ? "Write here to reopen this query" : thread.private_now ? "Write a private reply to the people in this conversation" : "Write your reply"}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <div className="mt-2 flex items-center justify-between">
            <span className="text-xs text-slate-400">Ctrl + Enter to send{thread.members.filter((m) => m.active).length > 2 ? ` · goes to ${thread.members.filter((m) => m.active).length - 1} people` : ""}</span>
            <button type="submit" disabled={busy || !text.trim()} className="s-press rounded-md bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">
              {busy ? "Sending..." : "Send reply"}
            </button>
          </div>
        </form>
      ) : (
        <div className="border-t border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
          This query is closed. Press Reopen to continue, or raise a new query.
        </div>
      )}

      <ForwardModal open={forwarding} thread={thread} onClose={() => setForwarding(false)} onDone={done} />
      <AddPeopleModal open={adding} thread={thread} onClose={() => setAdding(false)} onDone={done} />
    </div>
  );
}

export default function QueriesPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const staff = isQueryStaffRole(user?.role);
  const [filter, setFilter] = useState("Active");
  const [search, setSearch] = useState("");
  const [queryNo, setQueryNo] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [raising, setRaising] = useState(false);
  const [board, setBoard] = useState(null);
  const [tile, setTile] = useState("");
  const [kind, setKind] = useState("");
  const [holder, setHolder] = useState("");

  const loadBoard = useCallback(() => { queriesApi.dashboard().then(setBoard).catch(() => {}); }, []);
  useEffect(() => {
    loadBoard();
    const timer = setInterval(loadBoard, 60000);
    window.addEventListener("queries-changed", loadBoard);
    return () => { clearInterval(timer); window.removeEventListener("queries-changed", loadBoard); };
  }, [loadBoard]);

  // a tile asks the server for the right group and then narrows it here
  const TILE_STATUS = { new: "Active", active: "Active", waiting: "Open", late: "Open", priority: "Active", done: "" };
  function pickTile(key) {
    setTile(key);
    setKind("");
    setHolder("");
    setFilter(key ? TILE_STATUS[key] : "Active");
  }
  function pickChip(key) { setFilter(key); setTile(""); setKind(""); setHolder(""); }

  const load = useCallback(() => {
    queriesApi.list({ status: filter || undefined, search: search.trim() || undefined, query_no: queryNo.trim() || undefined, date_from: dateFrom || undefined, date_to: dateTo || undefined })
      .then((data) => { setRows(data); setErr(""); })
      .catch(() => setErr("Could not load the queries."))
      .finally(() => setLoading(false));
  }, [filter, search, queryNo, dateFrom, dateTo]);

  const shown = rows.filter((q) => {
    if (tile === "new" && !(q.unread_count > 0)) return false;
    if (tile === "late" && !q.overdue) return false;
    if (tile === "priority" && q.priority === "normal") return false;
    if (tile === "done" && q.status === "Open") return false;
    if (kind && (q.category !== kind || q.status === "Closed")) return false;
    if (holder && (q.status !== "Open" || (q.holder_name || "Admin team") !== holder)) return false;
    return true;
  });
  const filterName = tile ? { new: "New", active: "Active", waiting: "Waiting for reply", late: "No reply in 24 h", priority: "High and urgent", done: "Answered and closed" }[tile] : kind ? `Kind: ${kind}` : holder ? `Waiting for ${holder}` : "";

  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(load, search || queryNo ? 250 : 0);
    return () => clearTimeout(timer);
  }, [load, search, queryNo]);

  useEffect(() => {
    const timer = setInterval(load, 30000);
    window.addEventListener("queries-changed", load);
    return () => { clearInterval(timer); window.removeEventListener("queries-changed", load); };
  }, [load]);

  const ringing = rows.filter((q) => q.alarm_for_me).length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Queries</h1>
          <p className="text-sm text-slate-500">
            {staff ? "Questions from the team. Answer here, forward them, or open them up to more people." : "Ask the Admin team anything. Answers come back here, and queries sent to you appear in this list."}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setRaising(true)}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-brand-700"
        >
          {staff ? "+ Write to a user" : "+ Raise query"}
        </button>
      </div>

      {ringing > 0 && (
        <div className="q-alarm flex items-center gap-3 rounded-lg bg-rose-600 px-4 py-2.5 text-sm font-semibold text-white">
          <span className="q-bell grid h-8 w-8 place-items-center rounded-full bg-white/20"><BellIcon size={16} /></span>
          {ringing === 1 ? "1 query has waited over 24 hours for your answer" : `${ringing} queries have waited over 24 hours for your answer`}
        </div>
      )}

      <QueriesDashboard data={board} tile={tile} onTile={pickTile} kind={kind} onKind={(k) => { setKind(k); setTile(""); setHolder(""); setFilter("Active"); }} holder={holder} onHolder={(h) => { setHolder(h); setTile(""); setKind(""); setFilter("Open"); }} />
      {filterName && (
        <div className="s-pop flex flex-wrap items-center gap-2 text-xs text-slate-600">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-50 py-1 pl-3 pr-1.5 font-semibold text-indcool-navy">
            {filterName}
            <button type="button" aria-label="Show all active queries" onClick={() => pickTile("")} className="grid h-4 w-4 place-items-center rounded-full bg-sky-200 text-[10px] leading-none">✕</button>
          </span>
          <span>{shown.length} shown</span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-[22rem_1fr]">
        <div className={`rounded-lg bg-white shadow-sm ${id ? "hidden md:block" : ""}`}>
          <div className="space-y-2 border-b border-slate-100 p-3">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={staff ? "Search subject, number, person, query no. or date" : "Search subject, number, query no. or date"}
              className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
            />
            <div className="flex flex-wrap items-end gap-2">
              <label className="block text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Query no.
                <input
                  value={queryNo}
                  onChange={(e) => setQueryNo(e.target.value)}
                  inputMode="numeric"
                  maxLength={20}
                  placeholder="5 or QRY-0005"
                  aria-label="Query number"
                  className={`mt-0.5 block w-32 rounded border px-2 py-1.5 text-sm font-normal normal-case tracking-normal ${queryNo.trim() ? "border-indcool-blue bg-sky-50 text-indcool-navy" : "border-slate-300 bg-white text-slate-800"}`}
                />
              </label>
              <div>
                <span className="block text-[11px] font-semibold uppercase tracking-wide text-slate-500">Date raised</span>
                <DateRangeFilter className="mt-0.5" label="Raised" from={dateFrom} to={dateTo} onChange={(a, b) => { setDateFrom(a); setDateTo(b); }} />
              </div>
              {(queryNo.trim() || dateFrom || dateTo) && (
                <button type="button" onClick={() => { setQueryNo(""); setDateFrom(""); setDateTo(""); }} className="pb-2 text-xs text-sky-700 underline hover:text-sky-900">
                  Clear
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {FILTERS.map((f) => (
                <button
                  key={f.label}
                  type="button"
                  onClick={() => pickChip(f.key)}
                  className={`rounded-full px-2.5 py-1 text-xs font-medium ${filter === f.key ? "bg-indcool-navy text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
          {err && <div className="m-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
          <div className="max-h-[70vh] overflow-y-auto">
            <QueryList rows={shown} activeId={id} staff={staff} loading={loading} term={search.trim()} numberOn={!!queryNo.trim()} dateOn={!!(dateFrom || dateTo)} />
          </div>
        </div>

        <div className={`overflow-hidden rounded-lg bg-white shadow-sm ${id ? "" : "hidden md:block"}`}>
          {id ? (
            <>
              <button type="button" onClick={() => navigate("/queries")} className="border-b border-slate-100 px-4 py-2 text-sm font-medium text-brand-700 md:hidden">
                ← All queries
              </button>
              <Thread key={id} id={id} staff={staff} onChanged={load} />
            </>
          ) : (
            <div className="flex h-full min-h-[16rem] items-center justify-center p-6 text-center text-sm text-slate-500">
              Choose a query on the left{staff ? "" : ", or raise a new one"}.
            </div>
          )}
        </div>
      </div>

      <RaiseQueryModal
        open={raising}
        staff={staff}
        onClose={() => setRaising(false)}
        onCreated={(created) => { setRaising(false); load(); navigate(`/queries/${created.id}`); }}
      />
    </div>
  );
}
