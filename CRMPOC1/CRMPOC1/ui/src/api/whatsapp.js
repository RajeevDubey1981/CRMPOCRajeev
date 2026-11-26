import { api } from "./client.js";

export const whatsappApi = {
  status: () => api.get("/api/whatsapp/status").then((r) => r.data),
  list: (params) => api.get("/api/whatsapp/conversations", { params }).then((r) => r.data),
  get: (id) => api.get(`/api/whatsapp/conversations/${id}`).then((r) => r.data),
  read: (id) => api.post(`/api/whatsapp/conversations/${id}/read`).then((r) => r.data),
  reply: (id, text) => api.post(`/api/whatsapp/conversations/${id}/reply`, { text }).then((r) => r.data),
  assign: (id, toMe) => api.post(`/api/whatsapp/conversations/${id}/assign`, { to_me: toMe }).then((r) => r.data),
  setStatus: (id, status) => api.post(`/api/whatsapp/conversations/${id}/status`, { status }).then((r) => r.data),
  aiPause: (id, paused) => api.post(`/api/whatsapp/conversations/${id}/ai-pause`, { paused }).then((r) => r.data),
  addNote: (id, body) => api.post(`/api/whatsapp/conversations/${id}/notes`, { body }).then((r) => r.data),
};
