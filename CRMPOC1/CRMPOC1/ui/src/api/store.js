import { api } from "./client.js";

export const storeApi = {
  meta: () => api.get("/api/store/meta").then((r) => r.data),
  lookupItems: (q) => api.get("/api/store/lookup/items", { params: { q: q || undefined } }).then((r) => r.data),
  checkSerial: (serial, grnId) => api.post("/api/store/serials/check", { serial, grn_id: grnId || null }).then((r) => r.data),
  listGrns: (params) => api.get("/api/store/grns", { params }).then((r) => r.data),
  getGrn: (id) => api.get(`/api/store/grns/${id}`).then((r) => r.data),
  createGrn: (body) => api.post("/api/store/grns", body).then((r) => r.data),
  updateGrn: (id, body) => api.put(`/api/store/grns/${id}`, body).then((r) => r.data),
  deleteGrn: (id) => api.delete(`/api/store/grns/${id}`),
  submitGrn: (id) => api.post(`/api/store/grns/${id}/submit`).then((r) => r.data),
  approveGrn: (id) => api.post(`/api/store/grns/${id}/approve`).then((r) => r.data),
  rejectGrn: (id, reason) => api.post(`/api/store/grns/${id}/reject`, { reason }).then((r) => r.data),
  stock: (params) => api.get("/api/store/stock", { params }).then((r) => r.data),
  stockUnits: (params) => api.get("/api/store/stock/units", { params }).then((r) => r.data),
  ledger: (params) => api.get("/api/store/ledger", { params }).then((r) => r.data),
};

export function storeError(e, fallback) {
  const d = e?.response?.data?.detail;
  if (Array.isArray(d)) return d.map((x) => x.msg).join("; ");
  return d || fallback;
}
