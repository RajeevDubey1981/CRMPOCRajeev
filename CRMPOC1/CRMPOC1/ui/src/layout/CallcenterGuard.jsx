import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthContext.jsx";

function isCallcenterAllowedPath(pathname) {
  if (pathname === "/dashboard") return true;
  if (pathname === "/complaints/new") return true;
  if (/^\/complaints\/\d+$/.test(pathname)) return true;
  // Queries is open to every role by design (Admin > Roles has no "queries" card at all). Orders and
  // Installations are allowed because Call Center's own role card has can_view/can_create ticked for
  // both -- this guard used to only ever let Call Center reach Dashboard and Complaints, so those two
  // sidebar links and the "+New" buttons on them did nothing even though the permission screen said
  // otherwise (security/role-access review, 2026-10-27).
  if (pathname === "/queries" || /^\/queries\/\d+$/.test(pathname)) return true;
  if (pathname === "/orders" || pathname === "/orders/new" || /^\/orders\/\d+$/.test(pathname)) return true;
  if (pathname === "/installations" || pathname === "/installations/new" || /^\/installations\/\d+$/.test(pathname)) return true;
  return false;
}

export default function CallcenterGuard({ children }) {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const role = user?.role?.toLowerCase?.() || "";

  if (role === "callcenter" && !isCallcenterAllowedPath(pathname)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}
