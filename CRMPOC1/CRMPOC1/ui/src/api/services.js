import { api } from "./client.js";

export const servicesApi = {
  list: (params) => api.get("/api/services", { params }).then((r) => r.data),
  get: (id) => api.get(`/api/services/${id}`).then((r) => r.data),
  create: (body) => api.post("/api/services", body).then((r) => r.data),
  update: (id, body) => api.put(`/api/services/${id}`, body).then((r) => r.data),
  updateStatus: (id, body) => api.post(`/api/services/${id}/status`, body).then((r) => r.data),
  summary: () => api.get("/api/services/summary").then((r) => r.data),
  history: (id) => api.get(`/api/services/${id}/history`).then((r) => r.data),
  searchCustomers: (params) => api.get("/api/services/customers/search", { params }).then((r) => r.data),
  engineers: () => api.get("/api/services/lookup/engineers").then((r) => r.data),
  vendors: () => api.get("/api/services/lookup/vendors").then((r) => r.data),
  verifyOrder: (id, body) => api.post(`/api/services/${id}/verify-order`, body).then((r) => r.data),
  restartTeamReview: (id) => api.post(`/api/services/${id}/restart-team-review`).then((r) => r.data),
  listUnits: (id, params) => api.get(`/api/services/${id}/units`, { params }).then((r) => r.data),
  assignUnits: (id, body) => api.post(`/api/services/${id}/assign-units`, body).then((r) => r.data),
  myAssignedUnits: () => api.get("/api/services/my-assigned-units").then((r) => r.data),
  identifyCustomer: (id, body) => api.post(`/api/services/${id}/identify-customer`, body).then((r) => r.data),
  assign: (id, body) => api.post(`/api/services/${id}/assign`, body).then((r) => r.data),
  cancelAssignment: (id) => api.post(`/api/services/${id}/assignment-cancel`).then((r) => r.data),
  verifySerial: (id, body) => api.post(`/api/services/${id}/verify-serial`, body).then((r) => r.data),
  reviewSerial: (id, body) => api.post(`/api/services/${id}/serial-verification-review`, body).then((r) => r.data),
  verifySerialsBulk: (id, body) => api.post(`/api/services/${id}/verify-serials-bulk`, body).then((r) => r.data),
  submitObservation: (id, body) => api.post(`/api/services/${id}/observations`, body).then((r) => r.data),
  submitObservationsBulk: (id, body) => api.post(`/api/services/${id}/observations/bulk`, body).then((r) => r.data),
  cancelObservation: (id, body = {}) => api.post(`/api/services/${id}/observations/cancel`, body).then((r) => r.data),
  approve: (id, body) => api.post(`/api/services/${id}/approval`, body).then((r) => r.data),
  approveBulk: (id, body) => api.post(`/api/services/${id}/approval/bulk`, body).then((r) => r.data),
  cancelApproval: (id) => api.post(`/api/services/${id}/approval/cancel`).then((r) => r.data),
  complete: (id, body) => api.post(`/api/services/${id}/completion`, body).then((r) => r.data),
  reviewCompletion: (id, body) => {
    const formData = new FormData();
    if (body.unit_id != null) formData.append("unit_id", String(body.unit_id));
    formData.append("decision", body.decision);
    if (body.remarks) formData.append("remarks", body.remarks);
    return api.post(`/api/services/${id}/completion-approval`, formData).then((r) => r.data);
  },
  cancelCompletion: (id) => api.post(`/api/services/${id}/completion/cancel`).then((r) => r.data),
  requestPayment: (id, body) => api.post(`/api/services/${id}/payment-request`, body).then((r) => r.data),
  cancelPaymentRequest: (id, body = {}) => {
    const formData = new FormData();
    if (body.unit_id != null) formData.append("unit_id", String(body.unit_id));
    if (body.remarks) formData.append("remarks", body.remarks);
    if (body.reject) formData.append("reject", "true");
    return api.post(`/api/services/${id}/payment-request/cancel`, formData).then((r) => r.data);
  },
  approvePayment: (id, body) => api.post(`/api/services/${id}/payment-approval`, body).then((r) => r.data),
  updatePaymentAmount: (id, body) => api.patch(`/api/services/${id}/payment-amount`, body).then((r) => r.data),
  close: (id, body = {}) => {
    const formData = new FormData();
    if (body.remarks) formData.append("remarks", body.remarks);
    return api.post(`/api/services/${id}/close`, formData).then((r) => r.data);
  },
  reopenToEngineer: (id, formData) =>
    api.post(`/api/services/${id}/reopen-to-engineer`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data),
  updateStatus: (id, formData) =>
    api.post(`/api/services/${id}/status`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data),
  documents: (id) => api.get(`/api/services/${id}/documents`).then((r) => r.data),
  uploadDocument: (id, formData) =>
    api.post(`/api/services/${id}/documents/upload`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data),
  reviewDocument: (id, documentId, body) =>
    api.post(`/api/services/${id}/documents/${documentId}/review`, body).then((r) => r.data),
  requestDocuments: (id) => api.post(`/api/services/${id}/documents/request-link`).then((r) => r.data),
  resendDocuments: (id) => api.post(`/api/services/${id}/documents/resend-link`).then((r) => r.data),
  ensureDocumentLink: (id) => api.post(`/api/services/${id}/documents/ensure-link`).then((r) => r.data),
  publicDocumentContext: (token) => api.get(`/api/services/public/${token}`).then((r) => r.data),
  publicUploadDocuments: (token, formData) =>
    api.post(`/api/services/public/${token}/upload`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data),
  serialLookup: (serial_no) => api.get("/api/services/serials/lookup", { params: { serial_no } }).then((r) => r.data),
};
