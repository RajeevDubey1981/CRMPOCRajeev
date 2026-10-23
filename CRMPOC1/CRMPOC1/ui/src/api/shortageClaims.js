import { api } from "./client.js";

export const shortageClaimsApi = {
  list: (params) => api.get("/api/shortage-claims", { params }).then((r) => r.data),
  get: (id) => api.get(`/api/shortage-claims/${id}`).then((r) => r.data),
  raise: (body) => api.post("/api/shortage-claims", body).then((r) => r.data),
  uploadPhoto: (id, file, label) => {
    const fd = new FormData();
    fd.append("photo", file);
    if (label) fd.append("label", label);
    return api.post(`/api/shortage-claims/${id}/photos`, fd).then((r) => r.data);
  },
  decide: (id, body) => api.post(`/api/shortage-claims/${id}/decide`, body).then((r) => r.data),
  approve: (id) => api.post(`/api/shortage-claims/${id}/approve`, {}).then((r) => r.data),
  reject: (id, reason) => api.post(`/api/shortage-claims/${id}/reject`, { reason }).then((r) => r.data),
  parties: () => api.get("/api/shortage-claims/parties").then((r) => r.data),
  exportUrl: (params) => {
    const u = new URL("/api/shortage-claims/export", api.defaults.baseURL);
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") u.searchParams.set(k, v);
    });
    return u.toString();
  },
};

export const ITEMS_MISSING = ["Copper pipe", "Remote control", "Gas charge", "Stabilizer", "Drain pipe", "Power cord", "Installation kit", "Other"];
export const RESP_LABEL = { mfg: "Manufacturer", trans: "Transporter", ins: "Insurance", company: "Company" };
