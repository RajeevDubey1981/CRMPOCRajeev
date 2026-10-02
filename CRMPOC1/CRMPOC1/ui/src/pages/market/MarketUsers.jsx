import { useEffect, useMemo, useState } from "react";
import { marketApi } from "../../api/market.js";
import Modal from "../../components/Modal.jsx";
import Pagination from "../../components/Pagination.jsx";

const ROLES = ["Retailer", "Distributor", "Sales", "Admin"];
const STATUS_TABS = ["All", "Pending", "Active"];

const fieldClass =
  "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";

function fmtDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleDateString("en-IN"); } catch { return s; }
}

function StatusBadge({ value }) {
  const cls =
    value === "Active"
      ? "bg-green-100 text-green-700"
      : "bg-amber-100 text-amber-700";
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {value}
    </span>
  );
}

function FeeBadge({ value }) {
  const cls =
    value === "Paid"
      ? "bg-green-100 text-green-700"
      : "bg-amber-100 text-amber-700";
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {value}
    </span>
  );
}

function RoleBadge({ value }) {
  const colors = {
    Retailer: "bg-blue-100 text-blue-700",
    Distributor: "bg-purple-100 text-purple-700",
    Sales: "bg-teal-100 text-teal-700",
    Admin: "bg-slate-200 text-slate-700",
  };
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${colors[value] || "bg-slate-100 text-slate-500"}`}>
      {value}
    </span>
  );
}

const EMPTY_FORM = {
  name: "",
  email: "",
  phone: "",
  address: "",
  city: "",
  state: "",
  role: "Retailer",
  status: "Pending",
  fee_status: "Pending",
  onboarding_fee: "",
};

function UserForm({ form, setForm, onSubmit, onCancel, submitLabel, readOnly = false }) {
  function field(name, label, type = "text", extra = {}) {
    return (
      <div>
        <label className={labelClass}>{label}</label>
        <input
          type={type}
          value={form[name]}
          onChange={(e) => setForm((f) => ({ ...f, [name]: e.target.value }))}
          className={fieldClass}
          readOnly={readOnly}
          {...extra}
        />
      </div>
    );
  }

  function sel(name, label, options) {
    return (
      <div>
        <label className={labelClass}>{label}</label>
        <select
          value={form[name]}
          onChange={(e) => setForm((f) => ({ ...f, [name]: e.target.value }))}
          className={fieldClass}
          disabled={readOnly}
        >
          {options.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {field("name", "Full Name *")}
        {field("email", "Email *", "email")}
        {field("phone", "Phone")}
        {field("city", "City")}
        {field("state", "State")}
        {field("onboarding_fee", "Onboarding Fee (₹)", "number")}
      </div>
      <div>
        <label className={labelClass}>Address</label>
        <textarea
          rows={2}
          value={form.address}
          onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
          className={fieldClass}
          readOnly={readOnly}
        />
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {sel("role", "Role", ROLES)}
        {sel("status", "Status", ["Pending", "Active"])}
        {sel("fee_status", "Fee Status", ["Pending", "Paid"])}
      </div>
      {!readOnly && (
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onSubmit}
            className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            {submitLabel}
          </button>
        </div>
      )}
    </div>
  );
}

export default function MarketUsers() {
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [statusTab, setStatusTab] = useState("All");
  const [filters, setFilters] = useState({ search: "", role: "" });
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState(EMPTY_FORM);
  const [createErr, setCreateErr] = useState("");

  const [editUser, setEditUser] = useState(null);
  const [editForm, setEditForm] = useState(EMPTY_FORM);
  const [editErr, setEditErr] = useState("");

  const [viewUser, setViewUser] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const params = useMemo(() => ({
    page,
    per_page: perPage,
    status: statusTab === "All" ? undefined : statusTab,
    role: filters.role || undefined,
    search: filters.search || undefined,
  }), [page, perPage, statusTab, filters]);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setData(await marketApi.listUsers(params));
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load users");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  function applyFilter(patch) {
    setFilters((f) => ({ ...f, ...patch }));
    setPage(1);
  }

  async function doCreate() {
    setCreateErr("");
    try {
      const body = { ...createForm };
      if (!body.onboarding_fee) delete body.onboarding_fee;
      else body.onboarding_fee = parseFloat(body.onboarding_fee);
      await marketApi.createUser(body);
      setCreateOpen(false);
      setCreateForm(EMPTY_FORM);
      load();
    } catch (e) {
      setCreateErr(e.response?.data?.detail || "Failed to create user");
    }
  }

  function openEdit(u) {
    setEditUser(u);
    setEditForm({
      name: u.name || "",
      email: u.email || "",
      phone: u.phone || "",
      address: u.address || "",
      city: u.city || "",
      state: u.state || "",
      role: u.role || "Retailer",
      status: u.status || "Pending",
      fee_status: u.fee_status || "Pending",
      onboarding_fee: u.onboarding_fee != null ? String(u.onboarding_fee) : "",
    });
    setEditErr("");
  }

  async function doEdit() {
    setEditErr("");
    try {
      const body = { ...editForm };
      delete body.email;
      if (!body.onboarding_fee) delete body.onboarding_fee;
      else body.onboarding_fee = parseFloat(body.onboarding_fee);
      await marketApi.updateUser(editUser.id, body);
      setEditUser(null);
      load();
    } catch (e) {
      setEditErr(e.response?.data?.detail || "Failed to update user");
    }
  }

  async function doDelete() {
    if (!confirmDelete) return;
    try {
      await marketApi.deleteUser(confirmDelete.id);
      setConfirmDelete(null);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to delete user");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Market Users</h1>
        <button
          onClick={() => { setCreateForm(EMPTY_FORM); setCreateErr(""); setCreateOpen(true); }}
          className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          + Create User
        </button>
      </div>

      {/* Status tabs */}
      <div className="flex gap-1 border-b">
        {STATUS_TABS.map((t) => (
          <button
            key={t}
            onClick={() => { setStatusTab(t); setPage(1); }}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              statusTab === t
                ? "border-brand-600 text-brand-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <input
            type="text"
            placeholder="Search name or email…"
            value={filters.search}
            onChange={(e) => applyFilter({ search: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <select
            value={filters.role}
            onChange={(e) => applyFilter({ role: e.target.value })}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">All Roles</option>
            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      <div className="crm-scroll rounded-lg bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2">#ID</th>
              <th className="px-3 py-2">Name / Email</th>
              <th className="px-3 py-2">Contact</th>
              <th className="px-3 py-2">Role</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Fee Status</th>
              <th className="px-3 py-2">Joined</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
            )}
            {!loading && data.items.length === 0 && (
              <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-500">No users found.</td></tr>
            )}
            {!loading && data.items.map((u) => (
              <tr key={u.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 text-slate-500">{u.id}</td>
                <td className="px-3 py-2">
                  <div className="font-medium text-slate-800">{u.name}</div>
                  <div className="text-xs text-slate-500">{u.email}</div>
                </td>
                <td className="px-3 py-2">
                  <div>{u.phone || "—"}</div>
                  {u.city && <div className="text-xs text-slate-500">{u.city}</div>}
                </td>
                <td className="px-3 py-2"><RoleBadge value={u.role} /></td>
                <td className="px-3 py-2"><StatusBadge value={u.status} /></td>
                <td className="px-3 py-2"><FeeBadge value={u.fee_status} /></td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtDate(u.joined_at)}</td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-1">
                    <button
                      title="View"
                      onClick={() => setViewUser(u)}
                      className="rounded p-1 text-slate-600 hover:bg-slate-100"
                    >👁</button>
                    <button
                      title="Edit"
                      onClick={() => openEdit(u)}
                      className="rounded p-1 text-slate-600 hover:bg-slate-100"
                    >✏️</button>
                    <button
                      title="Delete"
                      onClick={() => setConfirmDelete(u)}
                      className="rounded p-1 text-rose-600 hover:bg-rose-50"
                    >🗑</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination
        page={page}
        perPage={perPage}
        total={data.total}
        onPageChange={setPage}
        onPerPageChange={(n) => { setPerPage(n); setPage(1); }}
      />

      {/* Create Modal */}
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Create Market User" maxWidth="max-w-2xl">
        {createErr && <div className="mb-3 rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">{createErr}</div>}
        <UserForm
          form={createForm}
          setForm={setCreateForm}
          onSubmit={doCreate}
          onCancel={() => setCreateOpen(false)}
          submitLabel="Create User"
        />
      </Modal>

      {/* Edit Modal */}
      <Modal open={!!editUser} onClose={() => setEditUser(null)} title="Edit Market User" maxWidth="max-w-2xl">
        {editErr && <div className="mb-3 rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">{editErr}</div>}
        <UserForm
          form={editForm}
          setForm={setEditForm}
          onSubmit={doEdit}
          onCancel={() => setEditUser(null)}
          submitLabel="Save Changes"
        />
      </Modal>

      {/* View Modal */}
      <Modal open={!!viewUser} onClose={() => setViewUser(null)} title="User Details" maxWidth="max-w-2xl">
        {viewUser && (
          <div className="space-y-3 text-sm">
            <div className="grid grid-cols-2 gap-3">
              {[
                ["Name", viewUser.name],
                ["Email", viewUser.email],
                ["Phone", viewUser.phone || "—"],
                ["City", viewUser.city || "—"],
                ["State", viewUser.state || "—"],
                ["Role", viewUser.role],
                ["Status", viewUser.status],
                ["Fee Status", viewUser.fee_status],
                ["Onboarding Fee", viewUser.onboarding_fee != null ? `₹${viewUser.onboarding_fee}` : "—"],
                ["Joined", fmtDate(viewUser.joined_at)],
              ].map(([label, val]) => (
                <div key={label}>
                  <div className="text-xs text-slate-500">{label}</div>
                  <div className="font-medium text-slate-800">{val}</div>
                </div>
              ))}
            </div>
            {viewUser.address && (
              <div>
                <div className="text-xs text-slate-500">Address</div>
                <div className="font-medium text-slate-800">{viewUser.address}</div>
              </div>
            )}
            <div className="flex justify-end pt-2">
              <button
                onClick={() => setViewUser(null)}
                className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Delete Confirm */}
      <Modal open={!!confirmDelete} onClose={() => setConfirmDelete(null)} title="Delete User?">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Delete user <strong>{confirmDelete?.name}</strong> ({confirmDelete?.email})?
            This cannot be undone.
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setConfirmDelete(null)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              onClick={doDelete}
              className="rounded-md bg-rose-600 px-3 py-2 text-sm text-white hover:bg-rose-700"
            >
              Delete
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
