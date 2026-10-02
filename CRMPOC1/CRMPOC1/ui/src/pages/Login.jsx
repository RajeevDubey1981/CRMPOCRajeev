import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext.jsx";
import LoginScene from "../components/LoginScene.jsx";

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
    <LoginScene>
      <form
        onSubmit={handleSubmit}
        className="w-full space-y-2.5 rounded-xl bg-white p-4 shadow-2xl"
      >
        <div>
          <div className="text-[26px] font-black leading-none tracking-tight text-indcool-navy">
            IND<span className="text-indcool-blue">cool</span>
          </div>
          <p className="mt-0.5 text-[11px] text-slate-500">Made in India. Made for Indians.</p>
        </div>
        <h1 className="text-sm font-bold text-indcool-navy">Welcome to INDcool</h1>
        {error && (
          <div className="rounded-md bg-rose-50 px-3 py-1.5 text-xs text-rose-700">{error}</div>
        )}
        <input
          type="email"
          name="email"
          aria-label="Email"
          placeholder="Email"
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full rounded-md border border-slate-300 px-2.5 py-1.5 text-base focus:border-indcool-navy focus:outline-none focus:ring-1 focus:ring-indcool-navy md:text-[13px]"
        />
        <input
          type="password"
          name="password"
          aria-label="Password"
          placeholder="Password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full rounded-md border border-slate-300 px-2.5 py-1.5 text-base focus:border-indcool-navy focus:outline-none focus:ring-1 focus:ring-indcool-navy md:text-[13px]"
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-indcool-navy px-4 py-2 text-[13px] font-bold text-white hover:bg-indcool-blue disabled:opacity-50"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </LoginScene>
  );
}
