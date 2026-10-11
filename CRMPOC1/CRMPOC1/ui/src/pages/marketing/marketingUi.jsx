import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { NavLink } from "react-router-dom";

import { marketingApi } from "../../api/marketing.js";
import { MotionSwitch } from "../sales/salesUi.jsx";

export { CountUp, Icon, MotionSwitch, Notice, PageTitle, btn, errText, fieldClass, fmtDateTime, greeting, useAsync } from "../sales/salesUi.jsx";

// ---- who the person is in Marketing: the ticks, read once and kept ----
const MarketingContext = createContext({ ready: false, status: null, has: () => false, reload: () => {} });

export function MarketingProvider({ children }) {
  const [state, setState] = useState({ ready: false, status: null, error: "" });
  const load = useCallback(() => {
    marketingApi.status()
      .then((status) => setState({ ready: true, status, error: "" }))
      .catch((e) => setState({ ready: true, status: null, error: e?.response?.data?.detail || "Marketing is not available" }));
  }, []);
  useEffect(() => { load(); }, [load]);
  const value = useMemo(() => ({
    ready: state.ready, status: state.status, error: state.error, reload: load,
    has: (tick) => !!state.status?.ticks?.includes(tick),
    any: (...ticks) => ticks.some((t) => state.status?.ticks?.includes(t)),
  }), [state, load]);
  return <MarketingContext.Provider value={value}>{children}</MarketingContext.Provider>;
}

export function useMarketing() {
  return useContext(MarketingContext);
}

export function MarketingTabs() {
  const { status } = useMarketing();
  const m = status?.menu || {};
  const tabs = [
    ["/marketing", "Overview", true],
    ...(m.settings ? [["/marketing/settings", "Settings"]] : []),
    ...(m.ticks ? [["/marketing/ticks", "Access ticks"]] : []),
  ];
  return (
    <nav className="mb-4 flex flex-wrap gap-1 border-b border-slate-200 pb-2">
      {tabs.map(([to, label, end]) => (
        <NavLink key={to} to={to} end={!!end} className={({ isActive }) => `s-press rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${isActive ? "bg-indcool-blue text-white" : "text-slate-600 hover:bg-slate-100"}`}>
          {label}
        </NavLink>
      ))}
      <MotionSwitch />
    </nav>
  );
}
