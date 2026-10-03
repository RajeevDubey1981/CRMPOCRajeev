import { api } from "./client.js";

export const complaintsApi = {
  list: (params) => api.get("/api/complaints", { params }).then((r) => r.data),
  get: (id) => api.get(`/api/complaints/${id}`).then((r) => r.data),
  create: (body) => api.post("/api/complaints", body).then((r) => r.data),
  update: (id, body) => api.put(`/api/complaints/${id}`, body).then((r) => r.data),
  remove: (id) => api.delete(`/api/complaints/${id}`),
  setPriority: (id, priority) => api.put(`/api/complaints/${id}/priority`, { priority }).then((r) => r.data),
  setPriority: (id, priority) => api.put(`/api/complaints/${id}/priority`, { priority }).then((r) => r.data),
  updateStatus: (id, formData) =>
    api.put(`/api/complaints/${id}/status`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data),
  recordAction: (id, body) =>
    api.post(`/api/complaints/${id}/action`, body).then((r) => r.data),
  history: (id) => api.get(`/api/complaints/${id}/history`).then((r) => r.data),
  linkedServiceRequest: (id) => api.get(`/api/complaints/${id}/service-request`).then((r) => r.data),
  linkedInstallationRequest: (id) => api.get(`/api/complaints/${id}/installation-request`).then((r) => r.data),
  ensureInstallationRequest: (id) => api.post(`/api/complaints/${id}/installation-request`).then((r) => r.data),
  verifyInstallationOrder: (id) => api.post(`/api/complaints/${id}/installation-request/verify-order`).then((r) => r.data),
  requestInstallationUploadLink: (id) => api.post(`/api/complaints/${id}/installation-documents/request-link`).then((r) => r.data),
  modelOptions: () => api.get("/api/complaints/model-options").then((r) => r.data),
  searchCustomers: (params) => api.get("/api/complaints/customers/search", { params }).then((r) => r.data),
  linkCustomer: (id, body) => api.post(`/api/complaints/${id}/link-customer`, body).then((r) => r.data),
  ensureServiceRequest: (id) => api.post(`/api/complaints/${id}/service-request`).then((r) => r.data),
  requestCustomerUploadLink: (id, resend = false) =>
    api.post(`/api/complaints/${id}/documents/request-link`, null, { params: resend ? { resend: true } : undefined }).then((r) => r.data),
  exportUrl: (params) => {
    const u = new URL("/api/complaints/export", api.defaults.baseURL);
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") u.searchParams.set(k, v);
    });
    return u.toString();
  },
};

export const usersApi = {
  list: (params) => api.get("/api/users", { params }).then((r) => r.data),
};

export const serialsApi = {
  lookup: (serial_no) =>
    api.get("/api/serials/lookup", { params: { serial_no } }).then((r) => r.data),
};
