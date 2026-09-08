import axios from "axios";

const publicApi = axios.create({
  baseURL: (import.meta.env.VITE_API_BASE_URL || "").trim() || (import.meta.env.DEV ? "http://localhost:8010" : window.location.origin),
  timeout: 60000,
});

export const partnerRegistrationPublicApi = {
  get: (token) => publicApi.get(`/api/partner-registrations/public/${token}`).then((r) => r.data),
  saveStep: (token, step, data) =>
    publicApi.put(`/api/partner-registrations/public/${token}/step`, { step, data }).then((r) => r.data),
  uploadDocument: (token, documentKey, file) => {
    const body = new FormData();
    body.append("file", file);
    return publicApi
      .post(`/api/partner-registrations/public/${token}/documents/${documentKey}`, body, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
  submit: (token) =>
    publicApi
      .post(`/api/partner-registrations/public/${token}/submit`, { declaration_accepted: true })
      .then((r) => r.data),
};
