import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext.jsx";

function defaultPathForRole(role) {
  if (role === "vendor") return "/vendor-dashboard";
  return "/dashboard";
}

export default function Login() {
  const { user, login, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  if (user) {
    const dest = defaultPathForRole(user.role);
    return <Navigate to={dest} replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      const loggedInUser = await login(email, password);
      navigate(defaultPathForRole(loggedInUser.role), { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
    }
  }

  return (
    <div className="flex min-h-full flex-col bg-indcool-teal md:flex-row">
      <div className="flex flex-col justify-between bg-indcool-navy px-6 py-6 text-white md:w-1/2 md:px-12 md:py-10">
        <div>
          <div className="text-5xl font-black leading-none tracking-tight md:text-7xl">
            IND<span className="text-sky-300">cool</span>
          </div>
          <p className="mt-2 text-xs text-white/85 md:text-sm">Made in India. Made for Indians.</p>
        </div>
        <div className="my-6 md:my-0">
          <div className="text-3xl font-black tracking-tight md:text-5xl">SSO</div>
          <p className="mt-2 text-base font-bold md:text-xl">Service, Sales and Operations</p>
        </div>
        <p className="hidden text-xs text-white/70 md:block">INDcool</p>
      </div>
      <div className="flex flex-1 items-center justify-center p-4 md:p-8">
        <form
          onSubmit={handleSubmit}
          className="w-full max-w-sm space-y-4 rounded-xl bg-white p-6 shadow-lg md:p-8"
        >
          <div>
            <h1 className="text-2xl font-bold text-indcool-navy">Welcome to INDcool SSO</h1>
            <p className="text-sm text-slate-500">Sign in to continue</p>
          </div>
          {error && (
            <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>
          )}
          <div>
            <label className="mb-1 block text-sm font-bold text-slate-700">Email</label>
            <input
              type="email"
              name="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-base focus:border-indcool-navy focus:outline-none focus:ring-1 focus:ring-indcool-navy sm:text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-bold text-slate-700">Password</label>
            <input
              type="password"
              name="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-base focus:border-indcool-navy focus:outline-none focus:ring-1 focus:ring-indcool-navy sm:text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-indcool-navy px-4 py-2.5 font-bold text-white hover:bg-indcool-blue disabled:opacity-50"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
