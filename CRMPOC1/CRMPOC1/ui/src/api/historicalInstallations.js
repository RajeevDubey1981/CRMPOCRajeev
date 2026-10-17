import { api } from "./client.js";

export const historicalInstallationsApi = {
  search: (q) => api.get("/api/historical-installations/search", { params: { q } }).then((r) => r.data),
  preview: (orderId) => api.get(`/api/historical-installations/${orderId}/preview`).then((r) => r.data),
  complete: (body, proof) => {
    const form = new FormData();
    form.append("payload", JSON.stringify(body));
    if (proof) form.append("proof", proof);
    return api.post("/api/historical-installations/complete", form).then((r) => r.data);
  },
};
