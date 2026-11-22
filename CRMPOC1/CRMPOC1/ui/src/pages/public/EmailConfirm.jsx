import { useState } from "react";

import { api } from "../../api/client.js";

// Opened from the SMS link. The caller types their email and the 6-digit code from the message.
export default function EmailConfirm() {
  const [code, setCode] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/api/public/email-confirm", { code: code.trim(), email: email.trim() });
      setDone(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not save this. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-start justify-center bg-slate-50 px-4 py-10">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 text-sm font-semibold tracking-wide text-orange-700">INDCOOL</div>
        {done ? (
          <>
            <h1 className="text-lg font-semibold text-slate-900">Email confirmed</h1>
            <p className="mt-2 text-sm text-slate-600">Thank you. We will send your updates to {email.trim()}. You can close this page.</p>
          </>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <div>
              <h1 className="text-lg font-semibold text-slate-900">Confirm your email</h1>
              <p className="mt-1 text-sm text-slate-600">Type your email address and the 6-digit code from our SMS.</p>
            </div>
            <label className="block text-sm font-medium text-slate-700">
              Email address
              <input
                type="email"
                inputMode="email"
                autoComplete="email"
                autoCapitalize="none"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-base"
              />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              Code from the SMS
              <input
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                required
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/[^0-9]/g, ""))}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-base tracking-widest"
              />
            </label>
            {error && <p className="text-sm text-rose-600">{error}</p>}
            <button
              type="submit"
              disabled={busy || code.length !== 6 || !email}
              className="w-full rounded-md bg-orange-700 px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
            >
              {busy ? "Saving..." : "Confirm email"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
