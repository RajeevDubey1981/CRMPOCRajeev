import { api } from "./client.js";

export const ordersApi = {
  list: (params) => api.get("/api/orders", { params }).then((r) => r.data),
  autocomplete: (params) => api.get("/api/orders/search/autocomplete", { params }).then((r) => r.data),
  get: (id) => api.get(`/api/orders/${id}`).then((r) => r.data),
  create: (body, file) => {
    const fd = new FormData();
    fd.append("payload", JSON.stringify(body));
    if (file) fd.append("document", file);
    return api
      .post("/api/orders", fd, { headers: { "Content-Type": "multipart/form-data" } })
      .then((r) => r.data);
  },
  update: (id, body) => api.put(`/api/orders/${id}`, body).then((r) => r.data),
  updateInstallationRequirement: (id, installation_required) => api.put(`/api/orders/${id}/installation-requirement`, { installation_required }).then((r) => r.data),
  updateConsignees: (id, consignee_addresses) => api.put(`/api/orders/${id}/consignee-addresses`, { consignee_addresses }).then((r) => r.data),
  updateItemConsignee: (id, itemId, consignee_address_id) => api.patch(`/api/orders/${id}/items/${itemId}/consignee`, { consignee_address_id }).then((r) => r.data),
  replaceVendorLineItems: (id, body) => api.put(`/api/orders/${id}/vendor-line-items`, body).then((r) => r.data),
  remove: (id) => api.delete(`/api/orders/${id}`),
  submitSerials: (id, body) => api.post(`/api/orders/${id}/submit-serials`, body).then((r) => r.data),
  importItemsCsv: (id, file, itemCode, fileName = "order_items.csv") => {
    const fd = new FormData();
    fd.append("file", file, fileName);
    if (itemCode) fd.append("item_code", itemCode);
    return api.post(`/api/orders/${id}/items/import`, fd).then((r) => r.data);
  },
  exportItemsUrl: (id, itemCode) => {
    const params = new URLSearchParams();
    if (itemCode) params.set("item_code", itemCode);
    const qs = params.toString();
    const path = `/api/orders/${id}/items/export${qs ? `?${qs}` : ""}`;
    const base = (api.defaults.baseURL || "").replace(/\/$/, "");
    return base ? `${base}${path}` : path;
  },
  vendors: () => api.get("/api/orders/lookup/vendors").then((r) => r.data),
  couriers: () => api.get("/api/orders/lookup/couriers").then((r) => r.data),
  items: () => api.get("/api/orders/lookup/items").then((r) => r.data),
  exportUrl: (params) => {
    const u = new URLSearchParams();
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") u.set(k, v);
    });
    const qs = u.toString();
    const path = `/api/orders/export${qs ? `?${qs}` : ""}`;
    const base = (api.defaults.baseURL || "").replace(/\/$/, "");
    return base ? `${base}${path}` : path;
  },
};
