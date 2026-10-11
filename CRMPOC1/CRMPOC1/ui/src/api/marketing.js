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
  metaDiagnose: () => get("/api/marketing/meta/diagnose"),
  metaAdAccounts: () => get("/api/marketing/meta/ad-accounts"),
  metaUseAccount: (id, inUse) => api.put(`/api/marketing/meta/ad-accounts/${id}`, null, { params: { in_use: inUse } }).then((r) => r.data),
  metaCampaigns: (account) => get("/api/marketing/meta/campaigns", { account }),
};
