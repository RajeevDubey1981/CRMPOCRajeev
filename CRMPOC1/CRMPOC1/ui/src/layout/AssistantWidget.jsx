import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { assistantApi } from "../api/assistant.js";

const SUGGESTIONS = ["how to find leads", "process a return", "add courier", "where is order"];

export default function AssistantWidget() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState([
    { who: "bot", text: "Hi! I'm the INDcool Assistant — ask me where to find something or how to do a task." },
  ]);

  async function ask(text) {
    const q = text.trim();
    if (!q || busy) return;
    setMessages((m) => [...m, { who: "user", text: q }]);
    setInput("");
    setBusy(true);
    try {
      const res = await assistantApi.ask(q);
      setMessages((m) => [...m, { who: "bot", ...res }]);
    } catch {
      setMessages((m) => [...m, { who: "bot", text: "Something went wrong — try again." }]);
    } finally {
      setBusy(false);
    }
  }

  function goTo(link) {
    if (!link) return;
    setOpen(false);
    navigate(link);
  }

  return (
    <div className="fixed bottom-5 right-5 z-40 flex flex-col items-end gap-3">
      {open && (
        <div className="flex h-[480px] max-h-[70vh] w-[340px] max-w-[calc(100vw-2.75rem)] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
          <div className="flex items-center gap-2 bg-[#122050] px-4 py-3 text-white">
            <span className="text-sm font-bold">INDcool Assistant</span>
            <button type="button" onClick={() => setOpen(false)} className="ml-auto text-white/80 hover:text-white">✕</button>
          </div>
          <div className="flex-1 space-y-2.5 overflow-y-auto p-3.5">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`max-w-[85%] rounded-xl px-3 py-2 text-sm leading-relaxed ${
                  m.who === "user" ? "ml-auto rounded-br-sm bg-brand-600 text-white" : "rounded-bl-sm bg-slate-100 text-slate-800"
                }`}
              >
                {m.text}
                {m.steps && (
                  <ol className="mt-1.5 space-y-1 text-[13px]">
                    {m.steps.map((s, si) => (
                      <li key={si} className="flex gap-1.5">
                        <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-brand-100 text-[10px] font-bold text-brand-700">{si + 1}</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ol>
                )}
                {m.card_title && (
                  <div className="mt-2 rounded-lg border border-slate-200 bg-white px-2.5 py-2">
                    <div className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{m.card_title}</div>
                    <div className="text-sm font-semibold text-slate-800">{m.card_body}</div>
                  </div>
                )}
                {m.link && (
                  <button
                    type="button"
                    onClick={() => goTo(m.link)}
                    className="mt-1.5 block rounded-md bg-brand-50 px-2.5 py-1 text-xs font-bold text-brand-700 hover:bg-brand-100"
                  >
                    {m.link_label || "Open"} →
                  </button>
                )}
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-1.5 px-3.5 pb-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => ask(s)}
                className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] text-slate-600 hover:bg-slate-100"
              >
                {s}
              </button>
            ))}
          </div>
          <form
            onSubmit={(e) => { e.preventDefault(); ask(input); }}
            className="flex gap-2 border-t border-slate-200 px-3 py-2.5"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about the CRM..."
              className="flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
            />
            <button type="submit" disabled={busy} className="rounded-lg bg-brand-600 px-3.5 text-sm font-bold text-white disabled:opacity-50">
              {busy ? "…" : "Ask"}
            </button>
          </form>
        </div>
      )}

      {!open && (
        <div className="relative flex h-[170px] w-[170px] items-center justify-center">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="absolute h-[100px] w-[100px] rounded-full border-[3px] border-white"
              style={{ animation: "indcool-assistant-ring 2s cubic-bezier(.15,.6,.3,1) infinite", animationDelay: `${i * 0.5}s`, opacity: 0 }}
            />
          ))}
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="relative z-10 flex h-[100px] w-[100px] flex-col items-center justify-center gap-0.5 rounded-full border-[3px] border-white/20 text-white shadow-[0_10px_30px_rgba(18,32,80,0.5)] transition-transform hover:scale-105"
            style={{ background: "radial-gradient(circle at 32% 28%, #22326e, #122050 60%, #0a1430 100%)" }}
          >
            <span className="text-2xl leading-none">💬</span>
            <span className="text-[13px] font-extrabold tracking-wide">Assistant</span>
            <span className="absolute right-2 top-1 h-3.5 w-3.5 rounded-full border-2 border-white bg-emerald-400" />
          </button>
        </div>
      )}
      <style>{`
        @keyframes indcool-assistant-ring {
          0% { transform: scale(.75); opacity: .9; }
          80% { transform: scale(1.8); opacity: 0; }
          100% { transform: scale(1.8); opacity: 0; }
        }
      `}</style>
    </div>
  );
}
