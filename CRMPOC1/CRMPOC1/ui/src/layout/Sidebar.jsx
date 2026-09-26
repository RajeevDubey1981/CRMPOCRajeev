import { useState } from "react";
import { useAuth } from "../auth/AuthContext.jsx";
import { NavLink } from "react-router-dom";
import { isIndcoolServiceRole, isOperationsAdminRole, isPartnerAdminRole, isSystemAdminRole } from "../utils/roles.js";

const NAV = [
  { to: "/dashboard", label: "Dashboard", module: "dashboard" },
  { to: "/vendor-dashboard", label: "Vendor Dashboard", vendorOnly: true },
  {
    label: "Admin",
    adminOnly: true,
    children: [
      { to: "/admin/users", label: "Users", module: "users" },
      { to: "/admin/roles", label: "Roles", module: "roles" },
      { to: "/admin/permissions", label: "Permissions", module: "roles" },
      { to: "/admin/payments", label: "Payment History", systemAdminOnly: true },
      { to: "/admin/partner-registrations", label: "Partner Registrations", partnerAdminOnly: true },
    ],
  },
  { to: "/complaints", label: "Complaints", module: "complaints" },
  { to: "/services", label: "Service Requests", module: "services" },
  { to: "/services/my-units", label: "My Assigned Units", engineerOnly: true },
  { to: "/items", label: "Item Masters", module: "items" },
  { to: "/couriers", label: "Courier Masters", module: "couriers" },
  { to: "/orders", label: "Order List", module: "orders" },
  { to: "/serials/history", label: "Serial History", operationsOnly: true },
  { to: "/installations", label: "Installation Requests", module: "installations" },
  { to: "/claims", label: "Claims", module: "claims" },
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

function LeafLink({ to, label, disabled, onNavigate }) {
  if (disabled) {
    return (
      <span className="block rounded-md px-3 py-2 text-sm text-slate-500 cursor-not-allowed select-none">
        {label}
      </span>
    );
  }
  return (
    <NavLink
      to={to}
      onClick={onNavigate}
      className={({ isActive }) =>
        `block rounded-md px-3 py-2 text-sm transition ${
          isActive
            ? "bg-brand-600 text-white"
            : "text-slate-200 hover:bg-slate-700 hover:text-white"
        }`
      }
    >
      {label}
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
        className="flex w-full items-center justify-between rounded-md px-3 py-2 text-sm font-medium text-slate-100 hover:bg-slate-700"
      >
        <span>{label}</span>
        <span className="text-xs">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <div className="ml-3 mt-1 space-y-0.5 border-l border-slate-700 pl-3">
          {children.map((c) => (
            <LeafLink key={c.to} to={c.to} label={c.label} onNavigate={onNavigate} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function Sidebar({ collapsed, mobileOpen = false, onNavigate }) {
  const { user } = useAuth();
  const role = user?.role?.toLowerCase?.() || "";

  // Role-based visibility: vendors and engineers each see a small, focused menu.
  const isVendor = role === "vendor";
  const isEngineer = role === "engineer";
  const isCallcenter = role === "callcenter";
  const isIndcoolService = isIndcoolServiceRole(role);
  const isCourierAdmin = isOperationsAdminRole(role);

  const isPartnerAdmin = isPartnerAdminRole(user?.role);
  const isSystemAdmin = isSystemAdminRole(user?.role);

  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];
  const hasPermissionPayload = permissions.length > 0;
  function canView(module) {
    if (!module) return false;
    return permissions.some((permission) => permission.module === module && permission.can_view);
  }

  function canShow(item) {
    if (item.vendorOnly) return isVendor;
    if (item.engineerOnly) return isEngineer;
    if (item.operationsOnly) return isCourierAdmin;
    if (item.systemAdminOnly) return isSystemAdmin;
    if (item.partnerAdminOnly) return isPartnerAdmin;
    if (item.adminOnly) return isSystemAdmin || isPartnerAdmin;
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
      className={`fixed inset-y-0 left-0 z-40 h-full w-72 max-w-[85vw] overflow-x-hidden overflow-y-auto bg-slate-800 shadow-xl transition-transform duration-200 md:relative md:z-auto md:max-w-none md:shrink-0 md:shadow-none md:transition-all ${
        mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      } ${
        collapsed ? "md:w-0 md:min-w-0 md:-ml-1" : "md:w-64 md:min-w-64"
      }`}
    >
      <div className="px-4 py-5">
        <div className="text-lg font-bold tracking-wide text-white">Indcool CRM</div>
        <div className="text-xs text-slate-400">Service & Operations</div>
      </div>
      <nav className="space-y-1 px-3 pb-6">
        {filteredNav.map((item) =>
          item.children ? (
            <Group key={item.label} label={item.label} children={item.children} onNavigate={onNavigate} />
          ) : (
            <LeafLink key={item.label} to={item.to} label={item.label} disabled={item.disabled} onNavigate={onNavigate} />
          ),
        )}
      </nav>
    </aside>
  );
}
