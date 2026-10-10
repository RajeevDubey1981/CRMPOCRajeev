import { api } from "./client.js";

const get = (url, params) => api.get(url, { params }).then((r) => r.data);
const post = (url, body) => api.post(url, body || {}).then((r) => r.data);
const put = (url, body) => api.put(url, body || {}).then((r) => r.data);
const patch = (url, body) => api.patch(url, body || {}).then((r) => r.data);

export const salesApi = {
  enabled: () => get("/api/sales/enabled"),
  status: () => get("/api/sales/status"),
  summary: () => get("/api/sales/summary"),
  summaryQuick: () => api.get("/api/sales/summary", { timeout: 3000 }).then((r) => r.data),
  leads: (params) => get("/api/sales/leads", params),
  lead: (id) => get(`/api/sales/leads/${id}`),
  addLead: (body) => post("/api/sales/leads", body),
  patchLead: (id, body) => patch(`/api/sales/leads/${id}`, body),
  give: (id, owner_user_id) => post(`/api/sales/leads/${id}/give`, { owner_user_id }),
  autoGive: () => post("/api/sales/leads-auto-give"),
  call: (id, body) => post(`/api/sales/leads/${id}/call`, body),
  rate: (id, body) => post(`/api/sales/leads/${id}/rate`, body),
  priority: (id, body) => post(`/api/sales/leads/${id}/priority`, body),
  dispose: (id, body) => post(`/api/sales/leads/${id}/dispose`, body),
  approveDisposal: (id) => post(`/api/sales/leads/${id}/disposal/approve`),
  reopen: (id) => post(`/api/sales/leads/${id}/disposal/reopen`),
  remind: (id) => post(`/api/sales/leads/${id}/partner/remind`),
  cancelRequest: (id, reason) => post(`/api/sales/leads/${id}/partner/cancel-request`, { reason }),
  sync: (body) => post("/api/sales/sync", body),
  inboxLog: () => get("/api/sales/inbox-log"),
  items: (q) => get("/api/sales/items", { q }),
  quotations: (params) => get("/api/sales/quotations", params),
  quotation: (id) => get(`/api/sales/quotations/${id}`),
  makeQuotation: (leadId, body) => post(`/api/sales/leads/${leadId}/quotations`, body),
  updateQuotation: (id, body) => put(`/api/sales/quotations/${id}`, body),
  quotationAction: (id, action, reason) => post(`/api/sales/quotations/${id}/${action}`, { reason: reason || "" }),
  team: () => get("/api/sales/team"),
  updateProfile: (userId, body) => put(`/api/sales/team/${userId}/profile`, body),
  ticks: () => get("/api/sales/ticks"),
  setRoleTicks: (role, ticks) => put(`/api/sales/ticks/role/${role}`, { ticks }),
  setUserTicks: (userId, ticks) => put(`/api/sales/ticks/user/${userId}`, { ticks }),
  ticksHistory: () => get("/api/sales/ticks/history"),
  updateSettings: (body) => put("/api/sales/settings", body),
};
