import { api } from "./client.js";

const get = (url, params) => api.get(url, { params }).then((r) => r.data);
const post = (url, body) => api.post(url, body).then((r) => r.data);
const put = (url, body) => api.put(url, body).then((r) => r.data);

export const accountsApi = {
  meta: () => get("/api/accounts/meta"),
  lookupItems: (params) => get("/api/accounts/lookup/items", params),

  suppliers: (params) => get("/api/accounts/suppliers", params),
  createSupplier: (body) => post("/api/accounts/suppliers", body),
  updateSupplier: (id, body) => put(`/api/accounts/suppliers/${id}`, body),

  boms: (params) => get("/api/accounts/boms", params),
  getBom: (id) => get(`/api/accounts/boms/${id}`),
  createBom: (body) => post("/api/accounts/boms", body),
  updateBom: (id, body) => put(`/api/accounts/boms/${id}`, body),
  copyBom: (id) => post(`/api/accounts/boms/${id}/copy`),
  activateBom: (id) => post(`/api/accounts/boms/${id}/activate`),
  deleteBom: (id) => api.delete(`/api/accounts/boms/${id}`),

  assemblies: (params) => get("/api/accounts/assemblies", params),
  getAssembly: (id) => get(`/api/accounts/assemblies/${id}`),
  createAssembly: (body) => post("/api/accounts/assemblies", body),
  completeAssembly: (id, body) => post(`/api/accounts/assemblies/${id}/complete`, body),
  cancelAssembly: (id) => post(`/api/accounts/assemblies/${id}/cancel`),
  passport: (serial) => get(`/api/accounts/passport/${encodeURIComponent(serial)}`),

  pos: (params) => get("/api/accounts/pos", params),
  openPos: () => get("/api/accounts/pos/open"),
  getPo: (id) => get(`/api/accounts/pos/${id}`),
  createPo: (body) => post("/api/accounts/pos", body),
  updatePo: (id, body) => put(`/api/accounts/pos/${id}`, body),
  submitPo: (id) => post(`/api/accounts/pos/${id}/submit`),
  approvePo: (id) => post(`/api/accounts/pos/${id}/approve`),
  rejectPo: (id, reason) => post(`/api/accounts/pos/${id}/reject`, { reason }),
  cancelPo: (id, reason) => post(`/api/accounts/pos/${id}/cancel`, { reason }),
};

export function accError(e, fallback) {
  const d = e?.response?.data?.detail;
  if (Array.isArray(d)) return d.map((x) => x.msg).join("; ");
  return d || fallback;
}

export const fieldClass = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm";
export const labelClass = "mb-1 block text-sm font-medium text-slate-700";

export function money(v) {
  if (v === null || v === undefined || v === "") return "-";
  const n = Number(v);
  if (Number.isNaN(n)) return "-";
  return n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export const PO_BADGE = {
  Draft: "bg-slate-100 text-slate-700",
  "Pending Approval": "bg-amber-100 text-amber-800",
  Approved: "bg-sky-100 text-sky-800",
  "Part received": "bg-violet-100 text-violet-800",
  Received: "bg-emerald-100 text-emerald-800",
  Cancelled: "bg-rose-100 text-rose-800",
};

export const BOM_BADGE = {
  Draft: "bg-slate-100 text-slate-700",
  Active: "bg-emerald-100 text-emerald-800",
  Retired: "bg-slate-200 text-slate-500",
};

export const ASM_BADGE = {
  Planned: "bg-amber-100 text-amber-800",
  Completed: "bg-emerald-100 text-emerald-800",
  Cancelled: "bg-rose-100 text-rose-800",
};
