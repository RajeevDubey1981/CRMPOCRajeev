import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext.jsx";
import SerialSearch from "../components/SerialSearch.jsx";
import { isOperationsAdminRole } from "../utils/roles.js";

export default function Topbar({ onToggle, pendingCount = 0, onOpenPending, pendingLoading = false }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const canUseSerialHistory = isOperationsAdminRole(user?.role);
  const badgeLabel = pendingCount > 9 ? "9+" : String(pendingCount);

  return (
    <header className="flex flex-wrap items-center gap-2 border-b bg-white px-3 py-2 shadow-sm sm:px-4 sm:py-3">
      <button
        type="button"
        aria-label="Toggle sidebar"
        onClick={onToggle}
        className="rounded p-2 text-slate-600 hover:bg-slate-100"
      >
        <span className="block h-0.5 w-5 bg-current" />
        <span className="mt-1 block h-0.5 w-5 bg-current" />
        <span className="mt-1 block h-0.5 w-5 bg-current" />
      </button>
      <div className="order-3 min-w-full flex-1 sm:order-none sm:min-w-0 sm:px-4">
        {canUseSerialHistory ? <SerialSearch /> : null}
      </div>
      <div className="ml-auto flex min-w-0 items-center gap-2 sm:gap-3">
        <button
          type="button"
          aria-label="Pending actions"
          onClick={onOpenPending}
          disabled={pendingLoading}
          className="relative rounded-md border border-slate-300 p-2 text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M15 17h5l-1.4-1.4A2 2 0 0 1 18 14.2V11a6 6 0 1 0-12 0v3.2c0 .5-.2 1-.6 1.4L4 17h5" />
            <path d="M9.5 17a2.5 2.5 0 0 0 5 0" />
          </svg>
          {pendingCount > 0 && (
            <span className="absolute -right-1 -top-1 min-w-[1.1rem] rounded-full bg-rose-600 px-1 text-center text-[10px] font-semibold leading-4 text-white">
              {badgeLabel}
            </span>
          )}
        </button>
        <div className="hidden min-w-0 text-right sm:block">
          <div className="truncate text-sm font-medium text-slate-800">{user?.name}</div>
          <div className="truncate text-xs text-slate-500">{user?.role}</div>
        </div>
        <button
          onClick={() => {
            logout();
            navigate("/login");
          }}
          className="rounded-md border border-slate-300 px-2.5 py-1.5 text-sm text-slate-700 hover:bg-slate-100 sm:px-3"
        >
          Logout
        </button>
      </div>
    </header>
  );
}
