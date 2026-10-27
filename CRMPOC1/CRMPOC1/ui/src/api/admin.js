import { api } from "./client.js";

export const usersAdminApi = {
  list: (params) => api.get("/api/users", { params }).then((r) => r.data),
  get: (id) => api.get(`/api/users/${id}`).then((r) => r.data),
  create: (body, files = {}) => userMutation("post", "/api/users", body, files),
  update: (id, body, files = {}) => userMutation("put", `/api/users/${id}`, body, files),
  idProof: (id) => api.get(`/api/users/${id}/id-proof`, { responseType: "blob" }).then((r) => r.data),
  profilePicture: (id) => api.get(`/api/users/${id}/profile-picture`, { responseType: "blob" }).then((r) => r.data),
  bankDetails: (id) => api.get(`/api/users/${id}/bank-details`).then((r) => r.data),
  deactivate: (id) => api.delete(`/api/users/${id}`),
  resetPassword: (id, new_password) =>
    api.put(`/api/users/${id}/reset-password`, { new_password }),
};

function userMutation(method, url, body, files) {
  if (!files?.idProof && !files?.profilePicture) {
    return api.request({ method, url, data: body }).then((r) => r.data);
  }
  const form = new FormData();
  form.append("payload", JSON.stringify(body));
  if (files.idProof) form.append("id_proof", files.idProof);
  if (files.profilePicture) form.append("profile_picture", files.profilePicture);
  return api.request({ method, url, data: form }).then((r) => r.data);
}

export const rolesApi = {
  list: () => api.get("/api/roles").then((r) => r.data),
  get: (id) => api.get(`/api/roles/${id}`).then((r) => r.data),
  create: (body) => api.post("/api/roles", body).then((r) => r.data),
  update: (id, body) => api.put(`/api/roles/${id}`, body).then((r) => r.data),
  remove: (id) => api.delete(`/api/roles/${id}`),
  setPermissions: (id, permissions) =>
    api.put(`/api/roles/${id}/permissions`, { permissions }).then((r) => r.data),
  modules: () => api.get("/api/roles/modules").then((r) => r.data),
  matrix: () => api.get("/api/roles/matrix").then((r) => r.data),
};
