import { api } from "./client.js";

const get = (url, params) => api.get(url, { params }).then((r) => r.data);
const put = (url, body) => api.put(url, body || {}).then((r) => r.data);

export const marketingApi = {
  enabled: () => get("/api/marketing/enabled"),
  status: () => get("/api/marketing/status"),
  people: () => get("/api/marketing/people"),
  ticks: () => get("/api/marketing/ticks"),
  setKindTicks: (kind, ticks) => put(`/api/marketing/ticks/role/${kind}`, { ticks }),
  setUserTicks: (userId, ticks) => put(`/api/marketing/ticks/user/${userId}`, { ticks }),
  ticksHistory: () => get("/api/marketing/ticks/history"),
  updateSettings: (body) => put("/api/marketing/settings", body),
  metaStatus: () => get("/api/marketing/meta/status"),
  metaConnect: () => get("/api/marketing/meta/connect"),
  metaDisconnect: () => api.post("/api/marketing/meta/disconnect").then((r) => r.data),
  metaSystemToken: (token) => api.post("/api/marketing/meta/system-token", { token }).then((r) => r.data),
  metaDiagnose: () => get("/api/marketing/meta/diagnose"),
  metaAdAccounts: () => get("/api/marketing/meta/ad-accounts"),
  metaUseAccount: (id, inUse) => api.put(`/api/marketing/meta/ad-accounts/${id}`, null, { params: { in_use: inUse } }).then((r) => r.data),
  metaCampaigns: (account) => get("/api/marketing/meta/campaigns", { account }),
  banners: () => get("/api/marketing/banners"),
  createBanner: (body) => api.post("/api/marketing/banners", body).then((r) => r.data),
  updateBanner: (id, body) => put(`/api/marketing/banners/${id}`, body),
  deleteBanner: (id) => api.delete(`/api/marketing/banners/${id}`).then((r) => r.data),
  bannerImageGuide: () => get("/api/marketing/banners/image-guide"),
  uploadBannerImage: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post("/api/marketing/banners/upload-image", fd, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
  },
  consent: () => get("/api/marketing/consent"),
  addConsent: (body) => api.post("/api/marketing/consent", body).then((r) => r.data),
  removeConsent: (id) => api.delete(`/api/marketing/consent/${id}`).then((r) => r.data),
  audiences: () => get("/api/marketing/audiences"),
  audienceCount: (params) => get("/api/marketing/audiences/count", params),
  createAudience: (body) => api.post("/api/marketing/audiences", body).then((r) => r.data),
  updateAudience: (id, body) => put(`/api/marketing/audiences/${id}`, body),
  deleteAudience: (id) => api.delete(`/api/marketing/audiences/${id}`).then((r) => r.data),
};
