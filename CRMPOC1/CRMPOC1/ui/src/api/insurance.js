import { api } from "./client.js";

export const insuranceApi = {
  list: (params) => api.get("/api/insurance", { params }).then(r => r.data),
  get: (id) => api.get(`/api/insurance/${id}`).then(r => r.data),
  create: (body) => api.post("/api/insurance", body).then(r => r.data),
  update: (id, body) => api.put(`/api/insurance/${id}`, body).then(r => r.data),
  remove: (id) => api.delete(`/api/insurance/${id}`),
};
