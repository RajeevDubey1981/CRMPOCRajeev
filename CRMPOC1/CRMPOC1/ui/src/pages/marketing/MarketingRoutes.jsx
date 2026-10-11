import { Navigate, Route, Routes } from "react-router-dom";

import MarketingHome from "./MarketingHome.jsx";
import MarketingTicks from "./MarketingTicks.jsx";
import { MarketingProvider, Notice, useMarketing } from "./marketingUi.jsx";

function Gate({ admin, children }) {
  const { ready, status, error } = useMarketing();
  if (!ready) return <p className="p-4 text-sm text-slate-500">Loading...</p>;
  if (!status) return <div className="p-4"><Notice tone="bad">{error || "Marketing is not available."}</Notice></div>;
  if (admin && !status.is_admin) return <Navigate to="/marketing" replace />;
  return children;
}

export default function MarketingRoutes() {
  return (
    <MarketingProvider>
      <Routes>
        <Route index element={<Gate><MarketingHome /></Gate>} />
        <Route path="ticks" element={<Gate admin><MarketingTicks /></Gate>} />
        <Route path="*" element={<Navigate to="/marketing" replace />} />
      </Routes>
    </MarketingProvider>
  );
}
