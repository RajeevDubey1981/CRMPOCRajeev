import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import { partnerAgreementPublicApi } from "../../api/partnerAgreementPublic.js";

const STEPS = ["Review", "Send OTP", "Enter OTP", "Signed"];

function fmtDateTime(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("en-IN", { dateStyle: "long", timeStyle: "medium" });
  } catch {
    return value;
  }
}

function StepBar({ step }) {
  return (
    <div className="mx-auto mb-5 flex max-w-md items-start">
      {STEPS.map((label, index) => {
        const n = index + 1;
        const done = step > n;
        const active = step === n;
        return (
          <div key={label} className="flex flex-1 items-center">
            <div className="flex flex-col items-center gap-1">
              <div
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  done ? "bg-emerald-600 text-white" : active ? "bg-sky-600 text-white" : "bg-slate-200 text-slate-400"
                }`}
              >
                {done ? "✓" : n}
              </div>
              <span className={`whitespace-nowrap text-[10px] ${active ? "font-bold text-sky-700" : "text-slate-400"}`}>
                {label}
              </span>
            </div>
            {n < STEPS.length && (
              <div className={`mb-4 h-0.5 flex-1 ${step > n ? "bg-emerald-600" : "bg-slate-200"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function OtpBoxes({ value, onChange, disabled }) {
  const refs = useRef([]);
  const chars = value.padEnd(6).split("").slice(0, 6);

  function update(index, char) {
    const next = chars.slice();
    next[index] = char;
    onChange(next.join("").trimEnd());
    if (char && index < 5) refs.current[index + 1]?.focus();
  }

  return (
    <div className="my-2 flex justify-center gap-2.5">
      {chars.map((char, index) => (
        <input
          key={index}
          ref={(el) => { refs.current[index] = el; }}
          type="text"
          inputMode="numeric"
          maxLength={1}
          disabled={disabled}
          value={char.trim()}
          onChange={(e) => update(index, e.target.value.replace(/\D/g, "").slice(-1))}
          onKeyDown={(e) => {
            if (e.key === "Backspace") {
              update(index, "");
              if (!char.trim() && index > 0) refs.current[index - 1]?.focus();
            }
          }}
          onPaste={(e) => {
            e.preventDefault();
            const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
            onChange(pasted);
            refs.current[Math.min(pasted.length, 5)]?.focus();
          }}
          className={`h-14 w-11 rounded-lg border-2 text-center text-xl font-bold text-slate-800 outline-none disabled:bg-slate-50 ${
            char.trim() ? "border-sky-600" : "border-slate-300"
          }`}
        />
      ))}
    </div>
  );
}

export default function PartnerAgreementSign() {
  const { token } = useParams();

  const [context, setContext] = useState(null);
  const [loadErr, setLoadErr] = useState("");
  const [step, setStep] = useState(1);
  const [scrolledToEnd, setScrolledToEnd] = useState(false);
  const [otp, setOtp] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [timer, setTimer] = useState(0);
  const [signed, setSigned] = useState(null);

  const scrollRef = useRef(null);

  useEffect(() => {
    partnerAgreementPublicApi
      .get(token)
      .then((result) => {
        setContext(result);
        if (result.is_signed) {
          setSigned({
            agreement_no: result.agreement_no,
            agreement_version: result.agreement_version,
            email: result.email,
            signed_at: result.signed_at,
          });
          setStep(4);
        }
      })
      .catch((error) => setLoadErr(error.response?.data?.detail || "Agreement link is invalid or expired"));
  }, [token]);

  useEffect(() => {
    if (timer <= 0) return undefined;
    const id = setTimeout(() => setTimer((t) => t - 1), 1000);
    return () => clearTimeout(id);
  }, [timer]);

  function onScroll() {
    const el = scrollRef.current;
    if (el && el.scrollTop + el.clientHeight >= el.scrollHeight - 8) setScrolledToEnd(true);
  }

  async function sendOtp() {
    setBusy(true);
    setErr("");
    try {
      const result = await partnerAgreementPublicApi.sendOtp(token);
      setStep(3);
      setOtp("");
      setTimer(result.resend_wait_seconds || 30);
    } catch (error) {
      setErr(error.response?.data?.detail || "Failed to send OTP. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function verifyOtp() {
    if (otp.length < 6) {
      setErr("Enter all 6 digits.");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      const result = await partnerAgreementPublicApi.verifyOtp(token, otp);
      setSigned(result);
      setStep(4);
    } catch (error) {
      setErr(error.response?.data?.detail || "OTP verification failed.");
    } finally {
      setBusy(false);
    }
  }

  if (loadErr) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
        <div className="max-w-md rounded-xl bg-white p-6 text-center shadow">
          <h1 className="text-lg font-semibold text-slate-900">Link unavailable</h1>
          <p className="mt-2 text-sm text-rose-700">{loadErr}</p>
        </div>
      </div>
    );
  }

  if (!context) {
    return <div className="flex min-h-screen items-center justify-center text-slate-600">Loading agreement...</div>;
  }

  return (
    <div className="min-h-screen bg-slate-100 py-6 sm:py-10">
      <div className="mx-auto max-w-3xl px-4">
        <div className="mb-5 text-center">
          <div className="text-xs font-semibold uppercase tracking-widest text-sky-700">Indcool Partner Onboarding</div>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">Digital Agreement Signing</h1>
          <p className="mt-1 text-sm text-slate-600">Verified via email OTP</p>
        </div>

        <StepBar step={step} />

        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
          {/* Step 1 — Review */}
          {step === 1 && (
            <>
              <div className="rounded-t-2xl bg-gradient-to-r from-slate-800 to-sky-700 px-6 py-4 text-white">
                <div className="text-base font-semibold">{context.agreement_title}</div>
                <div className="mt-0.5 text-xs opacity-80">
                  Ref: {context.agreement_no} · Version {context.agreement_version} · {context.agreement_effective}
                </div>
              </div>
              <div className="p-6">
                <div className="relative rounded-lg border border-slate-200">
                  <div
                    ref={scrollRef}
                    onScroll={onScroll}
                    className="h-80 overflow-y-auto whitespace-pre-wrap px-5 py-4 text-xs leading-relaxed text-slate-700"
                  >
                    {context.agreement_text}
                  </div>
                </div>
                <div
                  className={`mt-3 rounded-lg border px-3 py-2 text-xs font-semibold ${
                    scrolledToEnd
                      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                      : "border-amber-200 bg-amber-50 text-amber-700"
                  }`}
                >
                  {scrolledToEnd
                    ? "You have read the full agreement."
                    : "Please scroll to the bottom of the agreement before proceeding."}
                </div>
                <button
                  type="button"
                  disabled={!scrolledToEnd}
                  onClick={() => setStep(2)}
                  className="mt-4 w-full rounded-md bg-sky-700 px-4 py-3 text-sm font-medium text-white disabled:opacity-50"
                >
                  I have read the agreement — proceed to sign
                </button>
              </div>
            </>
          )}

          {/* Step 2 — Confirm email / send OTP */}
          {step === 2 && (
            <div className="p-6">
              <div className="text-center">
                <div className="text-lg font-bold text-slate-900">Verify your email</div>
                <p className="mt-1 text-sm text-slate-600">
                  We will send a 6-digit OTP to the email address on your partner registration.
                </p>
              </div>
              <div className="mt-5">
                <label className="mb-1 block text-sm font-medium text-slate-700">Registered email</label>
                <input
                  value={context.email}
                  disabled
                  className="w-full rounded-xl border border-slate-300 bg-slate-100 px-3 py-3 text-sm text-slate-600"
                />
                <p className="mt-1 text-xs text-slate-500">
                  For security, the agreement can only be signed from this registered address. Contact INDcool if it
                  needs to change.
                </p>
              </div>
              {err && (
                <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                  {err}
                </div>
              )}
              <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-xs leading-relaxed text-emerald-800">
                <strong className="mb-1 block">What happens next:</strong>
                1. You will receive a 6-digit OTP at this email address<br />
                2. Enter the OTP to digitally sign this agreement<br />
                3. Your partner account and vendor code are then issued
              </div>
              <div className="mt-4 flex gap-2">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="flex-1 rounded-md border border-slate-300 px-4 py-2.5 text-sm"
                >
                  Back
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={sendOtp}
                  className="flex-[2] rounded-md bg-sky-700 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
                >
                  {busy ? "Sending..." : "Send OTP to my email"}
                </button>
              </div>
            </div>
          )}

          {/* Step 3 — Enter OTP */}
          {step === 3 && (
            <div className="p-6">
              <div className="text-center">
                <div className="text-lg font-bold text-slate-900">Enter OTP</div>
                <p className="mt-1 text-sm text-slate-600">
                  A 6-digit OTP was sent to
                  <br />
                  <span className="font-semibold text-slate-900">{context.email}</span>
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Check your spam/junk folder if it does not arrive within 30 seconds.
                </p>
              </div>

              <div className="mt-4">
                <OtpBoxes value={otp} onChange={(v) => { setOtp(v); setErr(""); }} disabled={busy} />
              </div>

              {err && (
                <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-center text-xs text-rose-700">
                  {err}
                </div>
              )}

              <div className="mt-3 text-center text-xs text-slate-600">
                {timer > 0 ? (
                  `Resend OTP in ${timer}s`
                ) : (
                  <button type="button" onClick={sendOtp} disabled={busy} className="font-semibold text-sky-700 underline">
                    Resend OTP
                  </button>
                )}
              </div>

              <div className="mt-4 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2.5 text-xs leading-relaxed text-sky-900">
                By submitting the OTP you agree to the {context.agreement_title}. Your acceptance is timestamped and
                legally binding under the Information Technology Act, 2000.
              </div>

              <div className="mt-4 flex gap-2">
                <button
                  type="button"
                  onClick={() => { setStep(2); setOtp(""); setErr(""); }}
                  className="flex-1 rounded-md border border-slate-300 px-4 py-2.5 text-sm"
                >
                  Back
                </button>
                <button
                  type="button"
                  disabled={busy || otp.length < 6}
                  onClick={verifyOtp}
                  className="flex-[2] rounded-md bg-emerald-700 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
                >
                  {busy ? "Verifying..." : "Verify & sign agreement"}
                </button>
              </div>
            </div>
          )}

          {/* Step 4 — Signed */}
          {step === 4 && signed && (
            <div className="p-8 text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-600 text-2xl text-white">
                ✓
              </div>
              <div className="mt-4 text-xl font-bold text-emerald-700">Agreement signed successfully</div>
              <p className="mt-1 text-sm text-slate-600">
                Your agreement is digitally signed and legally binding.
              </p>

              <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-left">
                <div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-emerald-700">
                  Digital signing certificate
                </div>
                {[
                  ["Agreement No", signed.agreement_no],
                  ["Version", signed.agreement_version],
                  ["Signed Email", signed.email],
                  ["Signed At", fmtDateTime(signed.signed_at)],
                  ["IP Address", signed.ip_address || "—"],
                  ["Verified Via", "Email OTP"],
                  ["Legal Validity", "IT Act 2000, India"],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between border-b border-emerald-100 py-1.5 text-xs last:border-0">
                    <span className="text-slate-600">{label}</span>
                    <span className="font-semibold text-slate-800">{value}</span>
                  </div>
                ))}
              </div>

              <div className="mt-4 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2.5 text-xs text-sky-900">
                A confirmation email has been sent to {signed.email}, followed by your welcome email with your INDcool
                vendor code.
              </div>

              <button
                type="button"
                onClick={() => window.print?.()}
                className="mt-4 rounded-md border border-slate-300 px-4 py-2 text-xs"
              >
                Print / download certificate
              </button>
            </div>
          )}
        </div>

        <p className="mt-4 text-center text-[10px] text-slate-400">
          Legally valid under IT Act 2000 · Email OTP verification
        </p>
      </div>
    </div>
  );
}
