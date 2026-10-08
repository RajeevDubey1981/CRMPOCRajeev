import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { announceQueriesChanged, queriesApi } from "../../api/queries.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import RaiseQueryModal from "../../components/queries/RaiseQueryModal.jsx";
import { STATUS_STYLE, timeAgo } from "../../components/queries/useQuerySummary.js";
import { isQueryStaffRole } from "../../utils/roles.js";

const FILTERS = [
  { key: "Active", label: "Active" },
  { key: "Open", label: "Waiting for reply" },
  { key: "Answered", label: "Answered" },
  { key: "Closed", label: "Closed" },
  { key: "", label: "All" },
];

function StatusChip({ status }) {
  return <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_STYLE[status] || "bg-slate-100 text-slate-600"}`}>{status}</span>;
}

function QueryList({ rows, activeId, staff, loading }) {
  if (loading && rows.length === 0) return <p className="p-4 text-sm text-slate-500">Loading...</p>;
  if (rows.length === 0) return <p className="p-4 text-sm text-slate-500">No queries here.</p>;
  return (
    <ul className="divide-y divide-slate-100">
      {rows.map((q) => (
        <li key={q.id}>
          <Link
            to={`/queries/${q.id}`}
            className={`block px-3 py-2.5 hover:bg-sky-50 ${String(q.id) === String(activeId) ? "bg-sky-50" : ""}`}
          >
            <div className="flex items-start justify-between gap-2">
              <span className={`text-sm ${q.unread_count > 0 ? "font-bold text-slate-900" : "font-medium text-slate-800"}`}>{q.subject}</span>
              {q.unread_count > 0 && <span className="mt-0.5 shrink-0 rounded-full bg-rose-600 px-1.5 py-0.5 text-[10px] font-bold text-white">{q.unread_count} new</span>}
            </div>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-500">
              <StatusChip status={q.status} />
              {staff && <span className="font-medium text-slate-700">{q.owner_name}</span>}
              <span>{q.category}</span>
              {q.related_to && <span>· {q.related_to}</span>}
              <span className="ml-auto">{timeAgo(q.last_message_at)}</span>
            </div>
            <p className="mt-1 line-clamp-2 text-xs text-slate-600">
              {q.last_sender_name ? `${q.last_sender_name}: ` : ""}{q.last_message_preview}
            </p>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function Thread({ id, staff, onChanged }) {
  const [thread, setThread] = useState(null);
  const [err, setErr] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  const load = useCallback(() => {
    queriesApi.get(id)
      .then((data) => { setThread(data); setErr(""); announceQueriesChanged(); })
      .catch((e) => setErr(e.response?.status === 404 ? "This query was not found." : "Could not open this query."));
  }, [id]);

  useEffect(() => {
    setThread(null);
    setText("");
    load();
    const timer = setInterval(load, 30000);
    return () => clearInterval(timer);
  }, [load]);

  useEffect(() => { endRef.current?.scrollIntoView({ block: "end" }); }, [thread?.messages?.length]);

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

  async function send(e) {
    e?.preventDefault();
    if (!text.trim()) return;
    if (await act(() => queriesApi.reply(id, text))) setText("");
  }

  if (err && !thread) return <div className="p-6 text-sm text-rose-700">{err}</div>;
  if (!thread) return <div className="p-6 text-sm text-slate-500">Loading...</div>;

  return (
    <div className="flex min-h-[24rem] flex-col">
      <div className="border-b border-slate-200 px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-base font-semibold text-slate-800">{thread.subject}</h2>
          <StatusChip status={thread.status} />
        </div>
        <div className="mt-1 text-xs text-slate-500">
          {staff && <span className="mr-2 font-medium text-slate-700">{thread.owner_name} ({thread.owner_role})</span>}
          {thread.category}{thread.related_to ? ` · ${thread.related_to}` : ""} · started {timeAgo(thread.created_at)}
        </div>
        <div className="mt-2 flex gap-2">
          {thread.can_close && (
            <button type="button" disabled={busy} onClick={() => act(() => queriesApi.close(id))} className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60">
              Mark as solved
            </button>
          )}
          {thread.can_reopen && (
            <button type="button" disabled={busy} onClick={() => act(() => queriesApi.reopen(id))} className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60">
              Reopen
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 px-4 py-3" style={{ maxHeight: "calc(100vh - 22rem)", minHeight: "10rem" }}>
        {thread.messages.map((m, index) => {
          const newOnes = thread.unread_count || 0;
          const isNew = !m.mine && index >= thread.messages.length - newOnes;
          return (
            <div key={m.id} className={`flex ${m.mine ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm shadow-sm ${m.mine ? "bg-indcool-navy text-white" : m.from_staff ? "border border-emerald-200 bg-emerald-50 text-slate-800" : "border border-slate-200 bg-white text-slate-800"}`}>
                <div className={`mb-0.5 text-[11px] font-semibold ${m.mine ? "text-slate-200" : "text-slate-500"}`}>
                  {m.mine ? "You" : m.sender_name}{!m.mine && m.from_staff ? " · Admin team" : ""} · {timeAgo(m.created_at)}
                  {isNew && <span className="ml-1 rounded bg-rose-600 px-1 text-[10px] text-white">new</span>}
                </div>
                <div className="whitespace-pre-wrap break-words">{m.body}</div>
              </div>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>

      {thread.can_reply ? (
        <form onSubmit={send} className="border-t border-slate-200 p-3">
          {err && <div className="mb-2 rounded-md bg-rose-50 px-3 py-1.5 text-sm text-rose-700">{err}</div>}
          <textarea
            rows={3}
            value={text}
            maxLength={4000}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send(e); }}
            placeholder={thread.status === "Closed" ? "Write here to reopen this query" : "Write your reply"}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <div className="mt-2 flex items-center justify-between">
            <span className="text-xs text-slate-400">Ctrl + Enter to send</span>
            <button type="submit" disabled={busy || !text.trim()} className="rounded-md bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">
              {busy ? "Sending..." : "Send reply"}
            </button>
          </div>
        </form>
      ) : (
        <div className="border-t border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
          This query is closed. Press Reopen to continue, or raise a new query.
        </div>
      )}
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
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [raising, setRaising] = useState(false);

  const load = useCallback(() => {
    queriesApi.list({ status: filter || undefined, search: search.trim() || undefined })
      .then((data) => { setRows(data); setErr(""); })
      .catch(() => setErr("Could not load the queries."))
      .finally(() => setLoading(false));
  }, [filter, search]);

  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(load, search ? 250 : 0);
    return () => clearTimeout(timer);
  }, [load, search]);

  useEffect(() => {
    const timer = setInterval(load, 30000);
    window.addEventListener("queries-changed", load);
    return () => { clearInterval(timer); window.removeEventListener("queries-changed", load); };
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Queries</h1>
          <p className="text-sm text-slate-500">
            {staff ? "Questions from the team. Answer here; they are told on their dashboard." : "Ask the Admin team anything. Answers come back here."}
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

      <div className="grid grid-cols-1 gap-4 md:grid-cols-[22rem_1fr]">
        <div className={`rounded-lg bg-white shadow-sm ${id ? "hidden md:block" : ""}`}>
          <div className="space-y-2 border-b border-slate-100 p-3">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={staff ? "Search subject, number or person" : "Search subject or number"}
              className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
            />
            <div className="flex flex-wrap gap-1.5">
              {FILTERS.map((f) => (
                <button
                  key={f.label}
                  type="button"
                  onClick={() => setFilter(f.key)}
                  className={`rounded-full px-2.5 py-1 text-xs font-medium ${filter === f.key ? "bg-indcool-navy text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
          {err && <div className="m-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
          <div className="max-h-[70vh] overflow-y-auto">
            <QueryList rows={rows} activeId={id} staff={staff} loading={loading} />
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
