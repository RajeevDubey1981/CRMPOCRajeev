import { api } from "./client.js";

export const accountLedgerApi = {
  listVendors: (params) => api.get("/api/ledger/vendors", { params }).then((r) => r.data),
  listEngineers: (params) => api.get("/api/ledger/engineers", { params }).then((r) => r.data),
  get: (partyType, partyId) => api.get(`/api/ledger/${partyType}/${partyId}`).then((r) => r.data),
  setOpeningBalance: (partyType, partyId, body) =>
    api.post(`/api/ledger/${partyType}/${partyId}/opening-balance`, body).then((r) => r.data),
  setCycle: (partyType, partyId, body) =>
    api.post(`/api/ledger/${partyType}/${partyId}/cycle`, body).then((r) => r.data),
  addEntry: (partyType, partyId, body) =>
    api.post(`/api/ledger/${partyType}/${partyId}/entries`, body).then((r) => r.data),
  dashboard: () => api.get("/api/ledger/dashboard").then((r) => r.data),
};
