import { api } from "./client.js";

export const manufacturersApi = {
  list: (params) => api.get("/api/manufacturers", { params }).then(r => r.data),
  get: (id) => api.get(`/api/manufacturers/${id}`).then(r => r.data),
  create: (body) => api.post("/api/manufacturers", body).then(r => r.data),
  update: (id, body) => api.put(`/api/manufacturers/${id}`, body).then(r => r.data),
  remove: (id) => api.delete(`/api/manufacturers/${id}`),
};
