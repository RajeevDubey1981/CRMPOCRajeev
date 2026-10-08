import { useState } from "react";
import { useAuth } from "../auth/AuthContext.jsx";
import { NavLink } from "react-router-dom";
import { isIndcoolServiceRole, isOperationsAdminRole, isSystemAdminRole } from "../utils/roles.js";
import useQuerySummary from "../components/queries/useQuerySummary.js";

/** w-64 (16rem) reduced by 40% → 9.6rem */
const SIDEBAR_WIDTH_CLASS = "w-[9.6rem] min-w-[9.6rem]";

const NAV = [
  { to: "/dashboard", label: "Dashboard", module: "dashboard" },
  { to: "/vendor-dashboard", label: "Vendor Dashboard", vendorOnly: true },
  { to: "/queries", label: "Queries", everyone: true, badge: "queries" },
  {
    label: "Admin",
    children: [
      { to: "/admin/users", label: "Users", module: "users" },
      { to: "/admin/roles", label: "Roles", module: "roles" },
      { to: "/admin/permissions", label: "Permissions", module: "roles" },
      { to: "/admin/payments", label: "Payment History", module: "payments" },
    ],
  },
  { to: "/complaints", label: "Complaints", module: "complaints" },
  { to: "/services", label: "Service Requests", module: "services" },
  { to: "/partner-registrations", label: "Partner Registrations", module: "partner_registrations" },
  { to: "/services/my-units", label: "My Assigned Units", engineerOnly: true },
  { to: "/items", label: "Item Masters", module: "items" },
  { to: "/couriers", label: "Courier Masters", module: "couriers" },
  { to: "/orders", label: "Order List", module: "orders" },
  { to: "/serials/history", label: "Serial History", operationsOnly: true },
  { to: "/installations", label: "Installation Requests", module: "installations" },
  { to: "/claims", label: "Claims", module: "claims" },
  {
    label: "Bids",
    children: [
      { to: "/bids", label: "Bids", module: "bids", bidSide: "manager" },
      { to: "/bids/allocation", label: "Allocation", module: "bids", bidSide: "manager" },
      { to: "/bids/requests", label: "Vendor requests", module: "bids", bidSide: "manager" },
      { to: "/bids/stats", label: "Stats", module: "bids" },
      { to: "/bids/calendar", label: "Calendar", module: "bids" },
      { to: "/bids", label: "My bids", module: "bids", bidSide: "vendor" },
      { to: "/bids/request", label: "Request a bid", module: "bids", bidSide: "vendor" },
    ],
  },
  {
    label: "Market Admin",
    systemAdminOnly: true,
    children: [
      { to: "/market-admin/dashboard", label: "Dashboard" },
      { to: "/market-admin/users", label: "Users" },
      { to: "/market-admin/items", label: "Items" },
      { to: "/market-admin/orders", label: "Orders" },
      { to: "/market-admin/categories", label: "Categories" },
      { to: "/market-admin/vendors", label: "Vendor Registrations" },
      { to: "/market-admin/media", label: "Media Manager" },
    ],
  },
];

function LeafLink({ to, label, disabled, onNavigate, badge }) {
  if (disabled) {
    return (
      <span className="block rounded-md px-2 py-1.5 text-xs text-slate-500 cursor-not-allowed select-none leading-snug">
        {label}
      </span>
    );
  }
  return (
    <NavLink
      to={to}
      onClick={onNavigate}
      className={({ isActive }) =>
        `block rounded-md px-2 py-1.5 text-xs leading-snug transition ${
          isActive
            ? "bg-indcool-blue font-semibold text-white"
            : "text-slate-200 hover:bg-indcool-blue/60 hover:text-white"
        }`
      }
    >
      {label}
      {badge > 0 && <span className="ml-1.5 rounded-full bg-rose-600 px-1.5 py-0.5 text-[10px] font-bold text-white">{badge}</span>}
    </NavLink>
  );
}

function Group({ label, children, defaultOpen = false, onNavigate }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-xs font-medium leading-snug text-slate-100 hover:bg-indcool-blue/60"
      >
        <span>{label}</span>
        <span className="text-xs">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <div className="ml-2 space-y-1 border-l border-indcool-blue pl-2">
          {children.map((child) => (
            <LeafLink key={child.label} to={child.to} label={child.label} onNavigate={onNavigate} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function Sidebar({ collapsed, mobileOpen = false, onNavigate }) {
  const { user } = useAuth();
  const role = user?.role?.toLowerCase?.() || "";
  const { summary: queriesSummary } = useQuerySummary();

  const isVendor = role === "vendor";
  const isEngineer = role === "engineer";
  const isCallcenter = role === "callcenter";
  const isIndcoolService = isIndcoolServiceRole(role);
  const isCourierAdmin = isOperationsAdminRole(role);

  const isSystemAdmin = isSystemAdminRole(user?.role);

  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];
  const hasPermissionPayload = permissions.length > 0;
  function canView(module) {
    if (!module) return false;
    if (isSystemAdmin) return true;
    return permissions.some((permission) => permission.module === module && permission.can_view);
  }

  // Bid managers get create + edit on the bids module, vendors only view + create (see /api/auth/me)
  const bidsManager = permissions.some((p) => p.module === "bids" && p.can_view && p.can_edit);

  function canShow(item) {
    if (item.bidSide === "manager" && !bidsManager) return false;
    if (item.bidSide === "vendor" && bidsManager) return false;
    if (item.everyone) return true;
    if (item.vendorOnly) return isVendor;
    if (item.engineerOnly) return isEngineer;
    if (item.operationsOnly) return isCourierAdmin;
    if (item.systemAdminOnly) return isSystemAdmin;
    if (item.adminOnly) return isSystemAdmin;
    if (item.children) return true; // a group shows when at least one of its pages does (filtered below)
    if (!item.module) return isSystemAdmin;
    if (!hasPermissionPayload) return false;
    return canView(item.module);
  }

  const filteredNav = NAV
    .filter(canShow)
    .map((it) => {
      if (it.children) {
        const children = it.children.filter(canShow);
        if (children.length === 0) return null;
        return { ...it, children };
      }
      return it;
    })
    .filter(Boolean);

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 h-full max-w-[85vw] overflow-x-hidden overflow-y-auto bg-indcool-navy shadow-xl transition-transform duration-200 md:relative md:z-auto md:max-w-none md:shrink-0 md:shadow-none md:transition-[width,min-width] ${SIDEBAR_WIDTH_CLASS} ${
        mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      } ${
        collapsed ? "md:w-0 md:min-w-0 md:max-w-0 md:overflow-hidden md:border-0" : ""
      }`}
    >
      <div className="px-2.5 py-4">
        <div className="text-base font-black tracking-wide text-white leading-tight">INDcool CRM</div>
        <div className="text-[10px] leading-snug text-slate-200">Service and operations</div>
      </div>
      <nav className="space-y-0.5 px-2 pb-6">
        {filteredNav.map((item) =>
          item.children ? (
            <Group key={item.label} label={item.label} children={item.children} onNavigate={onNavigate} />
          ) : (
            <LeafLink key={item.label} to={item.to} label={item.label} disabled={item.disabled} onNavigate={onNavigate} badge={item.badge === "queries" ? queriesSummary?.unread : 0} />
          ),
        )}
      </nav>
    </aside>
  );
}
