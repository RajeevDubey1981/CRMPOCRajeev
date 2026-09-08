import { api } from "./client.js";

// GST lookups are cached client-side for an hour so re-validating the same
// registration (e.g. reopening the review page) doesn't re-hit the GSP on
// every click. Bump VITE_GST_CACHE_RESET_KEY to invalidate every cached
// entry at once (e.g. after a provider account change) without waiting out
// the TTL.
const GST_CACHE_TTL_MS = 60 * 60 * 1000;
const GST_CACHE_RESET_KEY = String(import.meta.env.VITE_GST_CACHE_RESET_KEY || "").trim();
const GST_CACHE_STORAGE_KEY = `admin_gst_validate_cache:${GST_CACHE_RESET_KEY}`;

function readGstCache() {
  try {
    return JSON.parse(localStorage.getItem(GST_CACHE_STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function writeGstCache(cache) {
  try {
    localStorage.setItem(GST_CACHE_STORAGE_KEY, JSON.stringify(cache));
  } catch {
    // Storage unavailable (private mode, quota) - caching is best-effort only.
  }
}

export const partnerRegistrationsApi = {
  meta: () => api.get("/api/partner-registrations/meta").then((r) => r.data),
  list: (params) => api.get("/api/partner-registrations", { params }).then((r) => r.data),
  get: (id) => api.get(`/api/partner-registrations/${id}`).then((r) => r.data),
  resendEmail: (id) => api.post(`/api/partner-registrations/${id}/resend-email`).then((r) => r.data),
  invite: (body) => api.post("/api/partner-registrations/invite", body).then((r) => r.data),
  update: (id, body) => api.put(`/api/partner-registrations/${id}`, body).then((r) => r.data),
  reject: (id, body) => api.post(`/api/partner-registrations/${id}/reject`, body).then((r) => r.data),
  agreement: (id) => api.get(`/api/partner-registrations/${id}/agreement`).then((r) => r.data),
  delete: (id) => api.delete(`/api/partner-registrations/${id}`),
  validateGst: async (id) => {
    const key = String(id);
    const cache = readGstCache();
    const cached = cache[key];
    if (cached && Date.now() - cached.cachedAt < GST_CACHE_TTL_MS) {
      return cached.result;
    }

    const result = await api.get(`/api/partner-registrations/${id}/gst/validate`).then((r) => r.data);

    cache[key] = { result, cachedAt: Date.now() };
    writeGstCache(cache);
    return result;
  },
};
