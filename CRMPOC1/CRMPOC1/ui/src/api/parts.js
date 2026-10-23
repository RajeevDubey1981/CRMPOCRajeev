import { api } from "./client.js";

export const partsApi = {
  catalogue: (params) => api.get("/api/parts/catalogue", { params }).then((r) => r.data),
  createPart: (body) => api.post("/api/parts/catalogue", body).then((r) => r.data),
  updatePart: (id, body) => api.put(`/api/parts/catalogue/${id}`, body).then((r) => r.data),
  addFitment: (id, crm_item_code, crm_item_name_cache) => {
    const fd = new FormData();
    fd.append("crm_item_code", crm_item_code);
    if (crm_item_name_cache) fd.append("crm_item_name_cache", crm_item_name_cache);
    return api.post(`/api/parts/catalogue/${id}/fitments`, fd).then((r) => r.data);
  },

  requests: (params) => api.get("/api/parts/requests", { params }).then((r) => r.data),
  requestDetail: (id) => api.get(`/api/parts/requests/${id}`).then((r) => r.data),
  raiseRequest: (body) => api.post("/api/parts/requests", body).then((r) => r.data),
  uploadPhoto: (id, file, label) => {
    const fd = new FormData();
    fd.append("photo", file);
    if (label) fd.append("label", label);
    return api.post(`/api/parts/requests/${id}/photos`, fd).then((r) => r.data);
  },
  approve: (id) => api.post(`/api/parts/requests/${id}/approve`, {}).then((r) => r.data),
  reject: (id, reason) => api.post(`/api/parts/requests/${id}/reject`, { reason }).then((r) => r.data),
  returnToTeam: (id, reason) => api.post(`/api/parts/requests/${id}/return-team`, { reason }).then((r) => r.data),
  returnToManager: (id, reason) => api.post(`/api/parts/requests/${id}/return`, { reason }).then((r) => r.data),
  resubmit: (id, body) => api.post(`/api/parts/requests/${id}/resubmit`, body || {}).then((r) => r.data),
  supplied: (id, note) => api.post(`/api/parts/requests/${id}/supplied`, { note }).then((r) => r.data),
  discuss: (id, message) => api.post(`/api/parts/requests/${id}/discuss`, { message }).then((r) => r.data),
};

export const REQUEST_KINDS = [
  { value: "part", label: "Spare part" },
  { value: "expense", label: "Expense" },
  { value: "ondemand", label: "On demand (not in catalogue)" },
  { value: "unit", label: "Whole unit replacement" },
];

export const REQUIRED_PHOTOS = { part: 4, expense: 0, ondemand: 0, unit: 5 };
