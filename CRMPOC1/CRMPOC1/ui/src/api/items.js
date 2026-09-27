import { api } from "./client.js";

export const itemsApi = {
  categories: () => api.get("/api/items/categories").then((r) => r.data),
  list: (params) => api.get("/api/items", { params }).then((r) => r.data),
  get: (id) => api.get(`/api/items/${id}`).then((r) => r.data),
  create: (body) => api.post("/api/items", body).then((r) => r.data),
  update: (id, body) => api.put(`/api/items/${id}`, body).then((r) => r.data),
  remove: (id) => api.delete(`/api/items/${id}`),
  exportUrl: (params) => {
    const u = new URL("/api/items/export", api.defaults.baseURL);
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") u.searchParams.set(k, v);
    });
    return u.toString();
  },
};
