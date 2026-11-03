import { api } from "./client.js";

export const couriersApi = {
  list: (params) => api.get("/api/couriers", { params }).then(r => r.data),
  get: (id) => api.get(`/api/couriers/${id}`).then(r => r.data),
  create: (body) => api.post("/api/couriers", body).then(r => r.data),
  update: (id, body) => api.put(`/api/couriers/${id}`, body).then(r => r.data),
  remove: (id) => api.delete(`/api/couriers/${id}`),
  getRateProfile: (id) => api.get(`/api/couriers/${id}/rate-profile`).then(r => r.data),
  saveRateProfile: (id, profile) => api.put(`/api/couriers/${id}/rate-profile`, profile).then(r => r.data),
  calculateFreight: (id, body) => api.post(`/api/couriers/${id}/calculate-freight`, body).then(r => r.data),
  exportUrl: (params) => {
    const u = new URL("/api/couriers/export", api.defaults.baseURL);
    Object.entries(params || {}).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") u.searchParams.set(k, v); });
    return u.toString();
  },
};
