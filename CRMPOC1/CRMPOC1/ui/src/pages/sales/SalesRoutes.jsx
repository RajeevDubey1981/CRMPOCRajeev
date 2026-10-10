import { Navigate, Route, Routes } from "react-router-dom";

import ExportDesk from "./ExportDesk.jsx";
import LeadDetail from "./LeadDetail.jsx";
import LeadList from "./LeadList.jsx";
import MyDay from "./MyDay.jsx";
import QuotationDetail from "./QuotationDetail.jsx";
import QuotationList from "./QuotationList.jsx";
import SalesDashboard from "./SalesDashboard.jsx";
import SalesLog from "./SalesLog.jsx";
import SourcesPage from "./SourcesPage.jsx";
import TypesPage from "./TypesPage.jsx";
import TeamPage from "./TeamPage.jsx";
import TicksPage from "./TicksPage.jsx";
import { Notice, SalesProvider, useSales } from "./salesUi.jsx";

function Gate({ tick, any, admin, children }) {
  const { ready, status, has, error } = useSales();
  if (!ready) return <p className="p-4 text-sm text-slate-500">Loading...</p>;
  if (!status) return <div className="p-4"><Notice tone="bad">{error || "Sales is not available."}</Notice></div>;
  if (admin && !status.is_admin) return <Navigate to="/sales" replace />;
  if (tick && !has(tick)) return <Navigate to="/sales" replace />;
  if (any && !any.some((k) => has(k))) return <Navigate to="/sales" replace />;
  return children;
}

export default function SalesRoutes() {
  return (
    <SalesProvider>
      <Routes>
        <Route index element={<Gate><MyDay /></Gate>} />
        <Route path="leads" element={<Gate><LeadList /></Gate>} />
        <Route path="leads/:id" element={<Gate><LeadDetail /></Gate>} />
        <Route path="quotations" element={<Gate any={["make_quote", "approve_quote"]}><QuotationList /></Gate>} />
        <Route path="quotations/:id" element={<Gate any={["make_quote", "approve_quote", "approve_high", "override"]}><QuotationDetail /></Gate>} />
        <Route path="export" element={<Gate tick="exp_desk"><ExportDesk /></Gate>} />
        <Route path="team" element={<Gate any={["others_profile", "targets", "own_profile", "see_all"]}><TeamPage /></Gate>} />
        <Route path="ticks" element={<Gate admin><TicksPage /></Gate>} />
        <Route path="dashboard" element={<Gate any={["my_dash", "team_dash", "co_dash"]}><SalesDashboard /></Gate>} />
        <Route path="log" element={<Gate tick="reglog"><SalesLog /></Gate>} />
        <Route path="sources" element={<Gate tick="connect"><SourcesPage /></Gate>} />
        <Route path="types" element={<Gate admin><TypesPage /></Gate>} />
        <Route path="*" element={<Navigate to="/sales" replace />} />
      </Routes>
    </SalesProvider>
  );
}
