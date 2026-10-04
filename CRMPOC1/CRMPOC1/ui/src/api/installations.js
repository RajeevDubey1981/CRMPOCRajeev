import { api } from "./client.js";

export const installationsApi = {
  list: (params) => api.get("/api/installations", { params }).then((r) => r.data),
  paymentHistory: (params) => api.get("/api/installations/payment-history", { params }).then((r) => r.data),
  engineerAssignmentOptions: () => api.get("/api/installations/engineer-assignment-options").then((r) => r.data),
  serviceUsers: () => api.get("/api/installations/lookup/service-users").then((r) => r.data),
  get: (id) => api.get(`/api/installations/${id}`).then((r) => r.data),
  create: (body) => api.post("/api/installations", body).then((r) => r.data),
  update: (id, body) => api.put(`/api/installations/${id}`, body).then((r) => r.data),
  updatePaymentAmount: (id, body) => api.patch(`/api/installations/${id}/payment-amount`, body).then((r) => r.data),
  remove: (id) => api.delete(`/api/installations/${id}`),
  updateStatus: (id, formData) =>
    api.put(`/api/installations/${id}/status`, formData).then((r) => r.data),
  bulkUpdateStatus: (formData) =>
    api.post("/api/installations/bulk-status-update", formData).then((r) => r.data),
  bulkAssign: (assignments) =>
    api.post("/api/installations/bulk-assign", { assignments }).then((r) => r.data),
  cancel: (id) => api.post(`/api/installations/${id}/cancel`).then((r) => r.data),
  bulkCancel: (installationIds) =>
    api.post("/api/installations/bulk-cancel", { installation_ids: installationIds }).then((r) => r.data),
  searchOrders: (params) => api.get("/api/installations/orders/search", { params }).then((r) => r.data),
  documents: (id) => api.get(`/api/installations/${id}/documents`).then((r) => r.data),
  history: (id) => api.get(`/api/installations/${id}/history`).then((r) => r.data),
  requestDocumentLink: (id) => api.post(`/api/installations/${id}/documents/request-link`).then((r) => r.data),
  verifyOrder: (id, body) => api.post(`/api/installations/${id}/verify-order`, body).then((r) => r.data),
  engineerSerial: (id, body) => api.post(`/api/installations/${id}/engineer-serial`, body).then((r) => r.data),
  verifySerial: (id, body) => api.post(`/api/installations/${id}/verify-serial`, body).then((r) => r.data),
  engineerSerials: (id) => api.get(`/api/installations/${id}/engineer-serials`).then((r) => r.data),
  submitEngineerSerials: (id, body) => api.post(`/api/installations/${id}/engineer-serials/submit`, body).then((r) => r.data),
  finalizeEngineerSerials: (id, body) => api.post(`/api/installations/${id}/engineer-serials/finalize`, body).then((r) => r.data),
  completeInstallation: (id, formData) =>
    api.post(`/api/installations/${id}/complete-installation`, formData).then((r) => r.data),
  resumeWorkflow: (id) => api.post(`/api/installations/${id}/resume-workflow`).then((r) => r.data),
  reviewCompletion: (id, body) => api.post(`/api/installations/${id}/completion-approval`, body).then((r) => r.data),
  requestPayment: (id, formData) =>
    api.post(`/api/installations/${id}/payment-request`, formData).then((r) => r.data),
  requestBulkPayment: (formData) =>
    api.post("/api/installations/bulk-payment-request", formData).then((r) => r.data),
  sendToServiceReview: (id, formData) =>
    api.post(`/api/installations/${id}/send-to-service-review`, formData).then((r) => r.data),
  reviewServiceObservation: (id, formData) =>
    api.post(`/api/installations/${id}/service-review`, formData).then((r) => r.data),
  resetWorkflow: (id, { target_step = 1, remarks } = {}) => {
    const body = new FormData();
    body.append("target_step", String(target_step));
    if (remarks) body.append("remarks", remarks);
    return api.post(`/api/installations/${id}/reset-workflow`, body).then((r) => r.data);
  },
  assignServiceUser: (id, body) => api.post(`/api/installations/${id}/assign-service-user`, body).then((r) => r.data),
  returnToServiceManager: (id, body = {}) => api.post(`/api/installations/${id}/return-to-service-manager`, body).then((r) => r.data),
  publicDocumentContext: (token) => api.get(`/api/installations/public/${token}`).then((r) => r.data),
  publicUploadDocuments: (token, formData) =>
    api.post(`/api/installations/public/${token}/upload`, formData).then((r) => r.data),
};
