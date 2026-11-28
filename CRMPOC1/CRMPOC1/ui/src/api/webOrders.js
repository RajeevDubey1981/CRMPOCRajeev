import { api } from "./client.js";

export const webOrdersApi = {
  summary: () => api.get("/api/web-orders/summary").then((r) => r.data),
  list: (params) => api.get("/api/web-orders", { params }).then((r) => r.data),
  get: (id) => api.get(`/api/web-orders/${id}`).then((r) => r.data),
  exportCsv: (params) => api.get("/api/web-orders/export", { params, responseType: "blob" }).then((r) => r.data),
};
