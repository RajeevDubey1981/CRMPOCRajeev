import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "../../api/client.js";

export default function LeadInterestForm() {
  const { token } = useParams();
  const [state, setState] = useState({ loading: true, error: "", data: null });
  const [interest, setInterest] = useState("yes");
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    api.get(`/api/public/lead-interest/${token}`)
      .then((r) => setState({ loading: false, error: "", data: r.data }))
      .catch((e) => setState({ loading: false, error: e.response?.data?.detail || "This link is not valid.", data: null }));
  }, [token]);

  async function submit(e) {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError("");
    try {
      await api.post(`/api/public/lead-interest/${token}`, { interest, answers });
      setDone(true);
    } catch (err) {
      setSubmitError(err.response?.data?.detail || "Could not send this. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (state.loading) {
    return <Shell><p className="muted">Loading...</p></Shell>;
  }
  if (state.error) {
    return <Shell><p className="muted">{state.error}</p></Shell>;
  }

  const { lead, product, fields = [], already_submitted: alreadySubmitted, submitted_interest: submittedInterest } = state.data;
  const setAnswer = (key) => (e) => setAnswers((a) => ({ ...a, [key]: e.target.value }));
  const showConfirm = done || alreadySubmitted;

  return (
    <Shell>
      <div className="brand"><span className="mark">IC</span><span>INDCOOL &middot; DEALER OUTREACH</span></div>
      <div className="card">
        <div className="hero">
          <span className="tag">New product</span>
          <h1>Introducing {product.name || "this product"}</h1>
          <p>We&rsquo;re extending the range you already carry. Tell us if it&rsquo;s worth adding to your next order.</p>
        </div>

        <div className="known">
          <span className="avatar">{(lead.name || "?").slice(0, 2).toUpperCase()}</span>
          <div><b>{lead.name}</b> &middot; {lead.phone} &mdash; already on file, no need to retype.</div>
        </div>

        {!showConfirm ? (
          <form onSubmit={submit}>
            <fieldset>
              <legend>Are you interested in {product.name || "this product"}?</legend>
              <div className="choice-row">
                <label className={`choice ${interest === "yes" ? "selected" : ""}`}>
                  <input type="radio" name="interest" value="yes" checked={interest === "yes"} onChange={() => setInterest("yes")} />
                  Yes, interested
                </label>
                <label className={`choice ${interest === "maybe" ? "selected" : ""}`}>
                  <input type="radio" name="interest" value="maybe" checked={interest === "maybe"} onChange={() => setInterest("maybe")} />
                  Maybe, send details
                </label>
              </div>
            </fieldset>

            {fields.map((f) => (
              <label className="field" key={f.key}>{f.label}
                {f.type === "select" ? (
                  <select value={answers[f.key] || ""} onChange={setAnswer(f.key)}>
                    <option value="">Select...</option>
                    {(f.options || []).map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : f.type === "yesno" ? (
                  <select value={answers[f.key] || ""} onChange={setAnswer(f.key)}>
                    <option value="">Select...</option>
                    <option value="Yes">Yes</option>
                    <option value="No">No</option>
                  </select>
                ) : (
                  <input type="text" value={answers[f.key] || ""} onChange={setAnswer(f.key)} />
                )}
              </label>
            ))}

            {submitError && <p className="error">{submitError}</p>}
            <button type="submit" className="submit-btn" disabled={submitting}>{submitting ? "Sending..." : "Send to INDcool"}</button>
          </form>
        ) : (
          <div className="confirm show">
            <div className="check">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5l4.5 4.5L19 7" /></svg>
            </div>
            <h2>Got it, thank you</h2>
            <p>This has been added straight to your existing record with our Sales team &mdash; someone will call you shortly.</p>
            {alreadySubmitted && !done && submittedInterest && (
              <p className="muted" style={{ marginTop: 10 }}>You already replied to this ({submittedInterest === "yes" ? "Yes, interested" : "Maybe, send details"}).</p>
            )}
          </div>
        )}
      </div>
      <p className="foot-note">This link is personal to {lead.name} and updates your existing INDcool record &mdash; no new account is created.</p>
    </Shell>
  );
}

function Shell({ children }) {
  return (
    <>
      <style>{CSS}</style>
      <div className="wrap">{children}</div>
    </>
  );
}

const CSS = `
:root {
  --bg: #f3f1ec; --panel: #ffffff; --ink: #1c2230; --sub: #6b6f7a; --line: #e2ddd1;
  --accent: #1e3a78; --accent-soft: #e8edf7; --gold: #b8860b; --good: #0f7a4a; --good-soft: #e3f3ea;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #15171c; --panel: #1d2027; --ink: #eceef2; --sub: #9aa2b1; --line: #343842;
    --accent: #7fa8ea; --accent-soft: #1d2a47; --gold: #e3b341; --good: #4fcf99; --good-soft: #15291f;
  }
}
* { box-sizing: border-box; }
body { background: var(--bg); }
.wrap { max-width: 460px; margin: 0 auto; padding: 32px 16px 48px; font-family: "Inter", system-ui, sans-serif; color: var(--ink); }
.muted { color: var(--sub); font-size: 0.9rem; text-align: center; margin-top: 60px; }
.brand { display: flex; align-items: center; gap: 9px; margin-bottom: 18px; }
.brand .mark { width: 30px; height: 30px; border-radius: 8px; background: var(--accent); display: grid; place-items: center; color: #fff; font-weight: 800; font-size: 13px; }
.brand span { font-size: 13px; font-weight: 700; color: var(--sub); letter-spacing: 0.02em; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 16px; overflow: hidden; }
.hero { padding: 22px 22px 18px; border-bottom: 1px solid var(--line); }
.hero .tag { display: inline-block; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.06em; color: var(--gold); margin-bottom: 8px; }
.hero h1 { margin: 0 0 6px; font-size: 1.3rem; font-family: "Sora", "Inter", sans-serif; }
.hero p { margin: 0; font-size: 0.86rem; color: var(--sub); line-height: 1.5; }
.known { margin: 16px 22px 0; padding: 12px 14px; border-radius: 10px; background: var(--accent-soft); font-size: 0.82rem; color: var(--ink); display: flex; align-items: center; gap: 10px; }
.known .avatar { width: 30px; height: 30px; border-radius: 999px; background: var(--accent); color: #fff; font-weight: 700; font-size: 12px; display: grid; place-items: center; flex: none; }
form { padding: 18px 22px 22px; display: flex; flex-direction: column; gap: 16px; }
fieldset { border: 0; padding: 0; margin: 0; }
legend { font-size: 0.8rem; font-weight: 700; margin-bottom: 8px; padding: 0; }
.choice-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.choice { position: relative; border: 1.5px solid var(--line); border-radius: 10px; padding: 11px 12px; cursor: pointer; font-size: 0.85rem; font-weight: 600; text-align: center; }
.choice input { position: absolute; opacity: 0; }
.choice.selected { border-color: var(--accent); background: var(--accent-soft); color: var(--accent); }
.field { display: flex; flex-direction: column; gap: 5px; font-size: 0.8rem; font-weight: 600; color: var(--sub); }
.field input, .field select, .field textarea { font: inherit; font-size: 0.92rem; font-weight: 500; color: var(--ink); border: 1.5px solid var(--line); border-radius: 9px; padding: 9px 11px; background: var(--panel); }
.field textarea { resize: vertical; min-height: 64px; font-family: inherit; }
.qty-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.submit-btn { border: 0; border-radius: 10px; background: var(--accent); color: #fff; font: inherit; font-size: 0.94rem; font-weight: 700; padding: 13px; cursor: pointer; }
.submit-btn:disabled { opacity: 0.6; }
.error { color: #c0392b; font-size: 0.82rem; margin: 0; }
.foot-note { margin-top: 14px; font-size: 0.74rem; color: var(--sub); text-align: center; line-height: 1.5; }
.confirm { padding: 40px 22px 34px; text-align: center; }
.confirm .check { width: 54px; height: 54px; border-radius: 999px; background: var(--good-soft); color: var(--good); display: grid; place-items: center; margin: 0 auto 14px; }
.confirm h2 { margin: 0 0 6px; font-size: 1.15rem; font-family: "Sora", "Inter", sans-serif; }
.confirm p { margin: 0; font-size: 0.86rem; color: var(--sub); line-height: 1.55; }
`;
