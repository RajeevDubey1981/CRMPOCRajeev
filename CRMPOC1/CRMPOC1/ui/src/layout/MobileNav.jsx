import { NavLink } from "react-router-dom";

import { useAuth } from "../auth/AuthContext.jsx";

// Phones only: a bottom menu for engineers and vendors, so the main places are one thumb tap away.
// "More" opens the full side menu, so nothing is taken away.

const ICONS = {
  home: "M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10",
  list: "M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01",
  box: "M21 8l-9-5-9 5v8l9 5 9-5V8zM3 8l9 5 9-5M12 13v8",
  tool: "M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18v3h3l6.3-6.3a4 4 0 0 0 5.4-5.4l-2.4 2.4-2.1-.6-.6-2.1 2.1-2.7z",
  doc: "M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6",
  chat: "M4 5h16v11H9l-5 4V5zM8 10h8M8 13h5",
  menu: "M4 6h16M4 12h16M4 18h16",
};

function Icon({ name }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={ICONS[name]} />
    </svg>
  );
}

function canView(user, module) {
  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];
  return permissions.some((p) => p.module === module && p.can_view);
}

export function mobileNavItems(user) {
  const role = (user?.role || "").trim().toLowerCase();
  if (role === "engineer") {
    return [
      { to: "/dashboard", label: "Home", icon: "home" },
      { to: "/services", label: "Jobs", icon: "list", end: true },
      { to: "/services/my-units", label: "My units", icon: "box" },
      ...(canView(user, "installations") ? [{ to: "/installations", label: "Install", icon: "tool" }] : []),
      { to: "/queries", label: "Queries", icon: "chat" },
    ];
  }
  if (role === "sales" || role === "sales_manager") {
    return [
      { to: "/dashboard", label: "Home", icon: "home" },
      { to: "/sales", label: "My day", icon: "list", end: true },
      { to: "/sales/leads", label: "Leads", icon: "doc" },
      { to: "/queries", label: "Queries", icon: "chat" },
    ];
  }
  if (role === "vendor") {
    return [
      { to: "/vendor-dashboard", label: "Home", icon: "home" },
      ...(canView(user, "orders") ? [{ to: "/orders", label: "Orders", icon: "box" }] : []),
      ...(canView(user, "services") ? [{ to: "/services", label: "Service", icon: "tool" }] : []),
      ...(canView(user, "bids") ? [{ to: "/bids", label: "Bids", icon: "doc" }] : []),
      { to: "/queries", label: "Queries", icon: "chat" },
    ];
  }
  return [];
}

export default function MobileNav({ onMore }) {
  const { user } = useAuth();
  const items = mobileNavItems(user);
  if (items.length === 0) return null;
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-30 flex border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] shadow-[0_-2px_8px_rgba(15,23,42,0.08)] md:hidden"
    >
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end ?? (item.to === "/dashboard" || item.to === "/vendor-dashboard")}
          className={({ isActive }) =>
            `flex min-h-[56px] flex-1 flex-col items-center justify-center gap-0.5 px-1 text-[11px] ${
              isActive ? "font-bold text-indcool-navy" : "text-slate-500"
            }`
          }
        >
          <Icon name={item.icon} />
          {item.label}
        </NavLink>
      ))}
      <button
        type="button"
        onClick={onMore}
        className="flex min-h-[56px] flex-1 flex-col items-center justify-center gap-0.5 px-1 text-[11px] text-slate-500"
      >
        <Icon name="menu" />
        More
      </button>
    </nav>
  );
}
