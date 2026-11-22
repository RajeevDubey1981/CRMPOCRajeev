import { api } from "./client.js";

export const callsApi = {
  list: (params) => api.get("/api/calls", { params }).then((r) => r.data),
  get: (id) => api.get(`/api/calls/${id}`).then((r) => r.data),
  recordingLink: (id) => api.get(`/api/calls/${id}/recording-link`).then((r) => r.data),
  recording: (id) => api.get(`/api/calls/${id}/recording`, { responseType: "blob" }).then((r) => r.data),
  create: (body) => api.post("/api/calls", body).then((r) => r.data),
  update: (id, body) => api.put(`/api/calls/${id}`, body).then((r) => r.data),
  remove: (id) => api.delete(`/api/calls/${id}`),
  transfer: (id, body) => api.post(`/api/calls/${id}/transfer`, body).then((r) => r.data),
  completeFollowup: (id) => api.post(`/api/calls/${id}/complete-followup`).then((r) => r.data),
  pendingFollowups: (params) => api.get("/api/calls/pending-follow-ups", { params }).then((r) => r.data),
  calendarEvents: (params) => api.get("/api/calls/calendar-events", { params }).then((r) => r.data),
};
