import { hasPermission } from "../../utils/permissions.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";

import Modal from "../../components/Modal.jsx";
import { couriersApi } from "../../api/couriers.js";

function fmt(s) { return s ? new Date(s).toLocaleString() : "—"; }

function Field({ label, value, full = false }) {
  return (
    <div className={full ? "md:col-span-2" : ""}>
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-0.5 text-sm text-slate-800">
        {value ?? <span className="text-slate-400">—</span>}
      </div>
    </div>
  );
}

export default function CourierDetail() {
  const { user: permUser } = useAuth();
  const canDeletePerm = hasPermission(permUser, "couriers", "can_delete");
  const location = useLocation();
  const navigate = useNavigate();
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const [courier, setCourier] = useState(null);
  const [err, setErr] = useState("");
  const [successMsg, setSuccessMsg] = useState(location.state?.success || "");
  const [editing, setEditing] = useState(searchParams.get("edit") === "1");
  const [editForm, setEditForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveErr, setSaveErr] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  async function load() {
    try {
      const data = await couriersApi.get(id);
      setCourier(data);
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to load courier");
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  function openEdit() {
    setEditForm({
      courier_name: courier.courier_name,
      contact_name: courier.contact_name || "",
      contact_mobile: courier.contact_mobile || "",
      email: courier.email || "",
      address: courier.address || "",
    });
    setSaveErr("");
    setEditing(true);
  }

  // Auto-open edit modal if ?edit=1 was in the URL and courier loaded
  useEffect(() => {
    if (courier && searchParams.get("edit") === "1" && !editing) {
      openEdit();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courier]);

  function setField(field, value) { setEditForm((f) => ({ ...f, [field]: value })); }

  async function saveEdit(e) {
    e.preventDefault();
    setSaveErr("");
    if (!editForm.courier_name.trim()) {
      setSaveErr("Courier name is required");
      return;
    }
    setSaving(true);
    try {
      const body = {
        courier_name: editForm.courier_name.trim(),
        contact_name: editForm.contact_name.trim() || null,
        contact_mobile: editForm.contact_mobile.trim() || null,
        email: editForm.email.trim() || null,
        address: editForm.address.trim() || null,
      };
      const updated = await couriersApi.update(id, body);
      setCourier(updated);
      setEditing(false);
      setSuccessMsg("Courier updated successfully.");
    } catch (e) {
      const detail = e.response?.data?.detail;
      setSaveErr(Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function doDelete() {
    try {
      await couriersApi.remove(id);
      navigate("/couriers", {
        state: { success: `Courier "${courier.courier_name}" deleted successfully.` },
      });
    } catch (e) {
      setErr(e.response?.data?.detail || "Failed to delete courier");
      setConfirmDelete(false);
    }
  }

  const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";
  const labelClass = "mb-1 block text-sm font-medium text-slate-700";

  if (err && !courier) return <div className="rounded-md bg-rose-50 px-4 py-3 text-sm text-rose-700">{err}</div>;
  if (!courier) return <div className="py-10 text-center text-slate-500">Loading…</div>;

  return (
    <div className="space-y-5">
      {successMsg && <div className="rounded-md bg-green-50 px-4 py-3 text-sm text-green-700">{successMsg}</div>}
      {err && <div className="rounded-md bg-rose-50 px-4 py-3 text-sm text-rose-700">{err}</div>}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/couriers" className="text-sm text-brand-600 hover:underline">← Back to Courier Masters</Link>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">{courier.courier_name}</h1>
        </div>
        <div className="flex gap-2">
          <button
            onClick={openEdit}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            ✏️ Edit
          </button>
{canDeletePerm && (
          <button
            onClick={() => setConfirmDelete(true)}
            className="rounded-md border border-rose-300 px-4 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50"
          >
            🗑 Delete
          </button>
)}
        </div>
      </div>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-medium text-slate-700">Courier details</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Courier Name" value={courier.courier_name} />
          <Field label="Contact Name" value={courier.contact_name} />
          <Field label="Contact Mobile" value={courier.contact_mobile} />
          <Field label="Email" value={courier.email} />
          <Field label="Address" value={courier.address} full />
          <Field label="Created At" value={fmt(courier.created_at)} />
          <Field label="Last Updated" value={fmt(courier.updated_at)} />
        </div>
      </section>

      {/* Edit Modal */}
      <Modal open={editing} onClose={() => setEditing(false)} title="Edit Courier">
        <form onSubmit={saveEdit} className="space-y-4">
          {saveErr && (
            <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{saveErr}</div>
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className={labelClass}>Courier Name *</label>
              <input
                required
                value={editForm?.courier_name || ""}
                onChange={(e) => setField("courier_name", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Contact Name</label>
              <input
                value={editForm?.contact_name || ""}
                onChange={(e) => setField("contact_name", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Contact Mobile</label>
              <input
                value={editForm?.contact_mobile || ""}
                onChange={(e) => setField("contact_mobile", e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label className={labelClass}>Email</label>
              <input
                type="email"
                value={editForm?.email || ""}
                onChange={(e) => setField("email", e.target.value)}
                className={fieldClass}
              />
            </div>
          </div>
          <div>
            <label className={labelClass}>Address</label>
            <textarea
              rows={3}
              value={editForm?.address || ""}
              onChange={(e) => setField("address", e.target.value)}
              className={fieldClass}
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >Cancel</button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal open={confirmDelete} onClose={() => setConfirmDelete(false)} title="Delete courier?">
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            This will soft-delete courier <strong>{courier.courier_name}</strong>.
            This action can be reversed by an admin.
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setConfirmDelete(false)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >Cancel</button>
            <button
              onClick={doDelete}
              className="rounded-md bg-rose-600 px-3 py-2 text-sm text-white hover:bg-rose-700"
            >Delete</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
