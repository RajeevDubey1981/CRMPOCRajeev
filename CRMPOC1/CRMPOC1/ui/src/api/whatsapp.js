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
  aiSwitch: (on) => api.post("/api/whatsapp/ai-switch", { on }).then((r) => r.data),
  resume: (id) => api.post(`/api/whatsapp/conversations/${id}/resume`).then((r) => r.data),
  kList: () => api.get("/api/whatsapp/knowledge").then((r) => r.data),
  kGet: (id) => api.get(`/api/whatsapp/knowledge/${id}`).then((r) => r.data),
  kCreate: (body) => api.post("/api/whatsapp/knowledge", body).then((r) => r.data),
  kUpdate: (id, body) => api.put(`/api/whatsapp/knowledge/${id}`, body).then((r) => r.data),
  kDelete: (id) => api.delete(`/api/whatsapp/knowledge/${id}`).then((r) => r.data),
  kImport: () => api.post("/api/whatsapp/knowledge-import").then((r) => r.data),
  kUpload: (file, category, alwaysSend) => {
    const f = new FormData();
    f.append("file", file);
    f.append("category", category || "");
    f.append("always_send", alwaysSend ? "true" : "false");
    return api.post("/api/whatsapp/knowledge-upload", f).then((r) => r.data);
  },
  kPreview: (question) => api.post("/api/whatsapp/knowledge-preview", { question }).then((r) => r.data),
  addNote: (id, body) => api.post(`/api/whatsapp/conversations/${id}/notes`, { body }).then((r) => r.data),
};
