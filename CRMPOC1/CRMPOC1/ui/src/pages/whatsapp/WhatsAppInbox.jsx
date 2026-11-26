import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { whatsappApi } from "../../api/whatsapp.js";
import { fmtIST } from "../../utils/time.js";

const FILTERS = [
  ["", "All"],
  ["unread", "Unread"],
  ["needs_staff", "Needs staff"],
  ["mine", "Mine"],
  ["closed", "Closed"],
];

function who(c) {
  return c.contact_name || c.wa_phone;
}

function short(value) {
  return fmtIST(value, "String", "en-IN", { dateStyle: "short", timeStyle: "short" });
}

function Tick({ status }) {
  const label = { sending: "Sending", sent: "Sent", delivered: "Delivered", read: "Read", failed: "Failed" }[status];
  if (!label) return null;
  return <span className={`ml-1 text-[10px] ${status === "failed" ? "text-rose-200" : "text-blue-200"}`}>{label}</span>;
}

export default function WhatsAppInbox() {
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [list, setList] = useState({ items: [], total: 0 });
  const [activeId, setActiveId] = useState(null);
  const [thread, setThread] = useState(null);
  const [text, setText] = useState("");
  const [note, setNote] = useState("");
  const [err, setErr] = useState("");
  const [sending, setSending] = useState(false);
  const [status, setStatus] = useState(null);
  const bottomRef = useRef(null);

  const loadList = useCallback(() => {
    const params = { search: search || undefined };
    if (filter === "unread") params.unread = true;
    else if (filter === "mine") params.mine = true;
    else if (filter) params.status = filter;
    return whatsappApi.list(params).then(setList).catch(() => null);
  }, [filter, search]);

  const loadThread = useCallback(
    (id) => {
      if (!id) return Promise.resolve();
      return whatsappApi
        .get(id)
        .then((d) => {
          setThread(d);
          if (d.conversation.unread_count > 0) whatsappApi.read(id).then(loadList).catch(() => null);
        })
        .catch(() => null);
    },
    [loadList],
  );

  useEffect(() => {
    whatsappApi.status().then(setStatus).catch(() => null);
  }, []);

  useEffect(() => {
    loadList();
    const t = setInterval(loadList, 10000);
    return () => clearInterval(t);
  }, [loadList]);

  useEffect(() => {
    setErr("");
    loadThread(activeId);
    if (!activeId) return undefined;
    const t = setInterval(() => loadThread(activeId), 8000);
    return () => clearInterval(t);
  }, [activeId, loadThread]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [thread?.messages?.length]);

  async function send(e) {
    e.preventDefault();
    if (!text.trim() || !activeId) return;
    setSending(true);
    setErr("");
    try {
      await whatsappApi.reply(activeId, text.trim());
      setText("");
      await loadThread(activeId);
      loadList();
    } catch (error) {
      setErr(error.response?.data?.detail || "Could not send");
      loadThread(activeId);
    } finally {
      setSending(false);
    }
  }

  async function act(fn) {
    try {
      await fn();
      await loadThread(activeId);
      loadList();
    } catch (error) {
      setErr(error.response?.data?.detail || "Could not do that");
    }
  }

  const conv = thread?.conversation;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">WhatsApp Inbox</h1>
          <p className="text-sm text-slate-500">Customer messages to the INDcool WhatsApp number. Replies from here go out from the same number.</p>
        </div>
        {status && (
          <div className="flex flex-wrap gap-2 text-xs">
            <span className={`rounded-full px-2.5 py-1 ${status.sending_enabled ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
              Sending {status.sending_enabled ? "on" : "off"}
            </span>
            <span className={`rounded-full px-2.5 py-1 ${status.app_secret_set ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}`}>
              Webhook {status.app_secret_set ? "ready" : "needs app secret"}
            </span>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-slate-600">
              {status.conversations} chats &middot; {status.unread} unread
            </span>
          </div>
        )}
      </div>

      <div className="grid h-[calc(100vh-190px)] min-h-[420px] grid-cols-1 overflow-hidden rounded-xl border border-slate-200 bg-white md:grid-cols-[320px_1fr_260px]">
        <div className="flex min-h-0 flex-col border-b border-slate-200 md:border-b-0 md:border-r">
          <div className="space-y-2 border-b border-slate-200 p-3">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search name, number, message"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            <div className="flex flex-wrap gap-1">
              {FILTERS.map(([v, l]) => (
                <button
                  key={v}
                  type="button"
                  onClick={() => setFilter(v)}
                  className={`rounded-full px-2.5 py-1 text-xs ${filter === v ? "bg-[#1e3a8a] text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>
          <ul className="min-h-0 flex-1 overflow-y-auto">
            {list.items.length === 0 && <li className="p-4 text-sm text-slate-400">No conversations yet.</li>}
            {list.items.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => setActiveId(c.id)}
                  className={`block w-full border-b border-slate-100 px-3 py-3 text-left hover:bg-slate-50 ${activeId === c.id ? "bg-blue-50" : ""}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium text-slate-800">{who(c)}</span>
                    <span className="shrink-0 text-[10px] text-slate-400">{c.last_message_at ? short(c.last_message_at) : ""}</span>
                  </div>
                  <div className="mt-0.5 flex items-center justify-between gap-2">
                    <span className="truncate text-xs text-slate-500">{c.last_message_preview || ""}</span>
                    {c.unread_count > 0 && <span className="shrink-0 rounded-full bg-emerald-600 px-1.5 text-[10px] font-semibold text-white">{c.unread_count}</span>}
                  </div>
                  {c.status === "needs_staff" && <span className="mt-1 inline-block rounded bg-rose-100 px-1.5 text-[10px] font-semibold text-rose-700">Needs staff</span>}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex min-h-0 flex-col">
          {!conv ? (
            <div className="flex flex-1 items-center justify-center text-sm text-slate-400">Pick a conversation.</div>
          ) : (
            <>
              <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2.5">
                <div>
                  <div className="font-medium text-slate-800">{who(conv)}</div>
                  <div className="text-xs text-slate-500">
                    +{conv.wa_phone}
                    {conv.assigned_name ? ` · with ${conv.assigned_name}` : ""}
                  </div>
                </div>
                <div className="flex gap-1.5 text-xs">
                  <button type="button" onClick={() => act(() => whatsappApi.assign(conv.id, !conv.assigned_to))} className="rounded border border-slate-300 px-2 py-1 hover:bg-slate-50">
                    {conv.assigned_to ? "Unassign" : "Take it"}
                  </button>
                  <button type="button" onClick={() => act(() => whatsappApi.setStatus(conv.id, conv.status === "closed" ? "open" : "closed"))} className="rounded border border-slate-300 px-2 py-1 hover:bg-slate-50">
                    {conv.status === "closed" ? "Reopen" : "Close"}
                  </button>
                </div>
              </div>
              <div className="min-h-0 flex-1 space-y-2 overflow-y-auto bg-slate-50 px-4 py-3">
                {thread.messages.map((m) => (
                  <div key={m.id} className={`flex ${m.direction === "out" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[80%] rounded-lg px-3 py-2 text-sm shadow-sm ${m.direction === "out" ? "bg-[#1e3a8a] text-white" : "bg-white text-slate-800"}`}>
                      {m.type !== "text" && (
                        <div className="mb-0.5 text-xs italic opacity-80">
                          [{m.type}
                          {m.media_name ? `: ${m.media_name}` : ""}]
                        </div>
                      )}
                      <div className="whitespace-pre-wrap break-words">{m.body}</div>
                      <div className={`mt-1 text-[10px] ${m.direction === "out" ? "text-blue-200" : "text-slate-400"}`}>
                        {m.sent_by ? `${m.sent_by} · ` : ""}
                        {short(m.created_at)}
                        {m.direction === "out" && <Tick status={m.status} />}
                      </div>
                      {m.error && <div className="mt-1 text-[11px] text-rose-200">{m.error}</div>}
                    </div>
                  </div>
                ))}
                <div ref={bottomRef} />
              </div>
              <form onSubmit={send} className="border-t border-slate-200 p-3">
                {!conv.window_open && (
                  <p className="mb-2 rounded bg-amber-50 px-3 py-2 text-xs text-amber-800">
                    More than 24 hours since the customer last wrote. WhatsApp only allows an approved template now, so free text is blocked.
                  </p>
                )}
                {conv.opted_out && <p className="mb-2 rounded bg-rose-50 px-3 py-2 text-xs text-rose-700">This customer asked us to stop messaging them.</p>}
                {err && <p className="mb-2 text-xs text-rose-600">{err}</p>}
                <div className="flex gap-2">
                  <textarea
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    rows={2}
                    placeholder="Type a reply"
                    disabled={!conv.window_open || conv.opted_out}
                    className="min-w-0 flex-1 resize-none rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100"
                  />
                  <button
                    type="submit"
                    disabled={sending || !text.trim() || !conv.window_open || conv.opted_out}
                    className="self-end rounded-md bg-[#1e3a8a] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                  >
                    {sending ? "Sending..." : "Send"}
                  </button>
                </div>
              </form>
            </>
          )}
        </div>

        <div className="hidden min-h-0 min-w-0 overflow-y-auto overflow-x-hidden border-l border-slate-200 p-3 md:block">
          {conv && (
            <div className="space-y-4 text-sm">
              <section>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Linked complaints</h3>
                {thread.complaints.length === 0 ? (
                  <p className="text-xs text-slate-400">None found for this number.</p>
                ) : (
                  thread.complaints.map((c) => (
                    <Link key={c.id} to={`/complaints/${c.id}`} className="mb-1 block rounded border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50">
                      <span className="font-mono text-[#1e3a8a]">{c.comp_no}</span> <span className="text-slate-500">{c.status}</span>
                    </Link>
                  ))
                )}
              </section>
              <section>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Service requests</h3>
                {thread.services.length === 0 ? (
                  <p className="text-xs text-slate-400">None found.</p>
                ) : (
                  thread.services.map((s) => (
                    <Link key={s.id} to={`/services/${s.id}`} className="mb-1 block rounded border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50">
                      <span className="font-mono text-[#1e3a8a]">{s.request_no}</span> <span className="text-slate-500">{s.status}</span>
                    </Link>
                  ))
                )}
              </section>
              <section>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Internal notes</h3>
                {thread.notes.map((n) => (
                  <div key={n.id} className="mb-1 rounded bg-amber-50 px-2 py-1 text-xs text-slate-700">
                    {n.body}
                    <div className="text-[10px] text-slate-400">{n.by}</div>
                  </div>
                ))}
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (note.trim()) act(async () => { await whatsappApi.addNote(conv.id, note.trim()); setNote(""); });
                  }}
                  className="mt-1 space-y-1"
                >
                  <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} placeholder="Note for staff only" className="box-border w-full min-w-0 resize-none rounded border border-slate-300 px-2 py-1 text-xs" />
                  <button type="submit" className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50">Add note</button>
                </form>
              </section>
              <section>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Automatic replies</h3>
                <p className="mb-1 text-xs text-slate-500">Not active yet. This switch will pause them for this chat once they are.</p>
                <label className="flex items-center gap-2 text-xs">
                  <input type="checkbox" checked={conv.ai_paused} onChange={(e) => act(() => whatsappApi.aiPause(conv.id, e.target.checked))} /> Pause for this chat
                </label>
              </section>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
