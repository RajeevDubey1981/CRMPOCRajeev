import { useEffect, useState } from "react";
import { marketApi } from "../../api/market.js";
import StatCard from "../../components/StatCard.jsx";
import { fmtIST } from "../../utils/time.js";

function fmtDate(s) {
  if (!s) return "—";
  try { return fmtIST(s, "Date", "en-IN"); } catch { return s; }
}

function fmtRupee(v) {
  if (v === null || v === undefined) return "—";
  return `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 0 })}`;
}

export default function MarketDashboard() {
  const [dash, setDash] = useState(null);
  const [recentUsers, setRecentUsers] = useState([]);
  const [recentOrders, setRecentOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      marketApi.dashboard(),
      marketApi.listUsers({ per_page: 5, page: 1 }),
      marketApi.listOrders({ per_page: 5, page: 1 }),
    ])
      .then(([d, u, o]) => {
        setDash(d);
        setRecentUsers(u.items || []);
        setRecentOrders(o.items || []);
      })
      .catch((e) => setErr(e.response?.data?.detail || "Failed to load market dashboard"))
      .finally(() => setLoading(false));
  }, []);

  const statusBadge = (s) => {
    const colors = {
      Active: "bg-green-100 text-green-700",
      Pending: "bg-amber-100 text-amber-700",
      Processing: "bg-blue-100 text-blue-700",
      Delivered: "bg-green-100 text-green-700",
      Cancelled: "bg-rose-100 text-rose-700",
    };
    return (
      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${colors[s] || "bg-slate-100 text-slate-500"}`}>
        {s}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Market Dashboard</h1>
        <button className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">
          Generate Report
        </button>
      </div>

      {err && (
        <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>
      )}

      {loading ? (
        <div className="text-sm text-slate-500">Loading dashboard…</div>
      ) : (
        <>
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <StatCard
              label="Total Users"
              value={dash?.total_users ?? "—"}
              tone="blue"
            />
            <StatCard
              label={`Active: ${dash?.active_users ?? 0} | Pending: ${dash?.pending_users ?? 0}`}
              value="Users"
              tone="grey"
            />
            <StatCard
              label="Total Items"
              value={dash?.total_items ?? "—"}
              tone="green"
            />
            <StatCard
              label={`Active: ${dash?.active_items ?? 0} | Low Stock: ${dash?.low_stock_items ?? 0}`}
              value="Items"
              tone="grey"
            />
            <StatCard
              label="Total Orders"
              value={dash?.total_orders ?? "—"}
              tone="orange"
            />
            <StatCard
              label="Total Sales"
              value={fmtRupee(dash?.total_sales)}
              tone="green"
            />
          </section>

          <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard
              label="Pending Orders"
              value={dash?.pending_orders ?? "—"}
              tone="orange"
            />
            <StatCard
              label="Delivered Orders"
              value={dash?.delivered_orders ?? "—"}
              tone="green"
            />
            <StatCard
              label="Total Categories"
              value={dash?.total_categories ?? "—"}
              tone="blue"
            />
          </section>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Recent Users */}
            <div className="rounded-lg bg-white shadow-sm">
              <div className="border-b px-4 py-3">
                <h2 className="text-sm font-semibold text-slate-700">Recent Users</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-50 text-left text-slate-600">
                    <tr>
                      <th className="px-3 py-2">Name</th>
                      <th className="px-3 py-2">Role</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Joined</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {recentUsers.length === 0 && (
                      <tr>
                        <td colSpan={4} className="px-3 py-4 text-center text-slate-400">
                          No users yet
                        </td>
                      </tr>
                    )}
                    {recentUsers.map((u) => (
                      <tr key={u.id} className="hover:bg-slate-50">
                        <td className="px-3 py-2 font-medium text-slate-800">{u.name}</td>
                        <td className="px-3 py-2 text-slate-600">{u.role}</td>
                        <td className="px-3 py-2">{statusBadge(u.status)}</td>
                        <td className="px-3 py-2 text-xs text-slate-500">{fmtDate(u.joined_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Recent Orders */}
            <div className="rounded-lg bg-white shadow-sm">
              <div className="border-b px-4 py-3">
                <h2 className="text-sm font-semibold text-slate-700">Recent Orders</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-50 text-left text-slate-600">
                    <tr>
                      <th className="px-3 py-2">Order #</th>
                      <th className="px-3 py-2">Retailer</th>
                      <th className="px-3 py-2">Amount</th>
                      <th className="px-3 py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {recentOrders.length === 0 && (
                      <tr>
                        <td colSpan={4} className="px-3 py-4 text-center text-slate-400">
                          No orders yet
                        </td>
                      </tr>
                    )}
                    {recentOrders.map((o) => (
                      <tr key={o.id} className="hover:bg-slate-50">
                        <td className="px-3 py-2 font-mono text-xs">{o.order_no}</td>
                        <td className="px-3 py-2 text-slate-600">{o.retailer_name || "—"}</td>
                        <td className="px-3 py-2">{fmtRupee(o.total_amount)}</td>
                        <td className="px-3 py-2">{statusBadge(o.status)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
