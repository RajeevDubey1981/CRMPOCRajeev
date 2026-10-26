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

  // Returns / cancellations (Accounts-driven, material-receipt gated)
  listPendingReturns: () => api.get("/api/ledger/returns/pending").then((r) => r.data),
  confirmMaterialReceipt: (orderId) => api.post(`/api/ledger/returns/${orderId}/confirm-receipt`).then((r) => r.data),
  processReturn: (orderId, body) => api.post(`/api/ledger/returns/${orderId}/process`, body).then((r) => r.data),

  // Vendor-approved extra expense (Sales/Service raise, vendor approves on their own portal)
  raiseVendorExpense: (body) => api.post("/api/ledger/vendor-expenses", body).then((r) => r.data),
  listVendorExpenses: (params) => api.get("/api/ledger/vendor-expenses", { params }).then((r) => r.data),
  decideVendorExpense: (id, body) => api.post(`/api/ledger/vendor-expenses/${id}/decide`, body).then((r) => r.data),

  // Bank statement upload (CSV) and review
  uploadStatement: (file) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/api/ledger/statements/upload", form, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
  },
  getStatement: (importId) => api.get(`/api/ledger/statements/${importId}`).then((r) => r.data),
  confirmStatementLine: (importId, lineId, body) =>
    api.post(`/api/ledger/statements/${importId}/lines/${lineId}/confirm`, body).then((r) => r.data),
  ignoreStatementLine: (importId, lineId) =>
    api.post(`/api/ledger/statements/${importId}/lines/${lineId}/ignore`).then((r) => r.data),
};
