import { useCallback, useEffect, useState } from "react";
import { Outlet } from "react-router-dom";

import { fetchPendingActions, markPendingActionsRead } from "../api/pendingActions.js";
import { useAuth } from "../auth/AuthContext.jsx";
import PendingActionsModal from "../components/PendingActionsModal.jsx";
import CallcenterGuard from "./CallcenterGuard.jsx";
import Sidebar from "./Sidebar.jsx";
import Topbar from "./Topbar.jsx";

const SIDEBAR_COLLAPSED_KEY = "indcool_sidebar_collapsed";

function readSidebarCollapsed() {
  try {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

let _collapsed = readSidebarCollapsed();

export default function Layout() {
  const { user } = useAuth();
  const [collapsed, setCollapsed] = useState(_collapsed);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [pendingItems, setPendingItems] = useState([]);
  const [pendingTotal, setPendingTotal] = useState(0);
  const [modalOpen, setModalOpen] = useState(false);
  const [loadingPending, setLoadingPending] = useState(false);

  function toggle() {
    if (window.matchMedia?.("(max-width: 767px)").matches) {
      setMobileSidebarOpen((open) => !open);
      return;
    }
    _collapsed = !_collapsed;
    setCollapsed(_collapsed);
    try {
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, _collapsed ? "1" : "0");
    } catch {
      // ignore storage errors
    }
  }

  const loadPendingActions = useCallback(async (autoOpen = false) => {
    if (!user) return;
    setLoadingPending(true);
    try {
      const data = await fetchPendingActions(15);
      setPendingItems(data.items || []);
      setPendingTotal(data.total || 0);
      if (autoOpen && (data.total || 0) > 0) {
        setModalOpen(true);
      }
    } catch {
      setPendingItems([]);
      setPendingTotal(0);
    } finally {
      setLoadingPending(false);
    }
  }, [user]);

  useEffect(() => {
    loadPendingActions(true);
  }, [loadPendingActions]);

  async function handleMarkRead(ids) {
    if (!ids?.length) return;
    try {
      await markPendingActionsRead(ids);
      await loadPendingActions(false);
    } catch {
      // keep UI responsive even if mark-read fails
    }
  }

  return (
    <div className="flex h-screen min-w-0 overflow-hidden" style={{ height: "100dvh" }}>
      {mobileSidebarOpen && (
        <button
          type="button"
          aria-label="Close sidebar"
          onClick={() => setMobileSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-slate-900/50 md:hidden"
        />
      )}
      <Sidebar
        collapsed={collapsed}
        mobileOpen={mobileSidebarOpen}
        onNavigate={() => setMobileSidebarOpen(false)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          onToggle={toggle}
          sidebarCollapsed={collapsed}
          pendingCount={pendingTotal}
          onOpenPending={() => {
            loadPendingActions(false);
            setModalOpen(true);
          }}
          pendingLoading={loadingPending}
        />
        <main className="min-w-0 flex-1 overflow-x-hidden overflow-y-auto p-3 sm:p-4 lg:p-6">
          <CallcenterGuard>
            <Outlet />
          </CallcenterGuard>
        </main>
      </div>
      <PendingActionsModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        items={pendingItems}
        total={pendingTotal}
        onMarkRead={handleMarkRead}
      />
    </div>
  );
}
