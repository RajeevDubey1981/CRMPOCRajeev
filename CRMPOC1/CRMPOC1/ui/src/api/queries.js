import { api } from "./client.js";

// Queries: users raise questions to the Admin and Sub Admin and talk them through in a thread.
export const queriesApi = {
  summary: () => api.get("/api/queries/summary").then((r) => r.data),
  list: (params) => api.get("/api/queries", { params }).then((r) => r.data),
  get: (id) => api.get(`/api/queries/${id}`).then((r) => r.data),
  create: (body) => api.post("/api/queries", body).then((r) => r.data),
  reply: (id, body) => api.post(`/api/queries/${id}/messages`, { body }).then((r) => r.data),
  close: (id) => api.post(`/api/queries/${id}/close`).then((r) => r.data),
  reopen: (id) => api.post(`/api/queries/${id}/reopen`).then((r) => r.data),
  people: (params) => api.get("/api/queries/people", { params }).then((r) => r.data),
  forward: (id, to_user_id, note) => api.post(`/api/queries/${id}/forward`, { to_user_id, note: note || "" }).then((r) => r.data),
  addMember: (id, user_id, kind, share_history = true) => api.post(`/api/queries/${id}/members`, { user_id, kind, share_history }).then((r) => r.data),
  removeMember: (id, user_id) => api.delete(`/api/queries/${id}/members/${user_id}`).then((r) => r.data),
  setPriority: (id, priority) => api.put(`/api/queries/${id}/priority`, { priority }).then((r) => r.data),
  ring: (id) => api.post(`/api/queries/${id}/ring`).then((r) => r.data),
};

export const QUERY_CATEGORIES = ["General", "Order", "Service request", "Installation", "Complaint", "Payment", "Bid", "App or login", "Other"];

// the sidebar badge and the dashboard panel listen for this to refresh at once after something changed
export function announceQueriesChanged() {
  window.dispatchEvent(new Event("queries-changed"));
}
