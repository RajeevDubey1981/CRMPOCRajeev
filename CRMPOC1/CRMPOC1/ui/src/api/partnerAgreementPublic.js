import axios from "axios";

const publicApi = axios.create({
  baseURL: (import.meta.env.VITE_API_BASE_URL || "").trim() || (import.meta.env.DEV ? "http://localhost:8010" : window.location.origin),
  timeout: 60000,
});

export const partnerAgreementPublicApi = {
  get: (token) => publicApi.get(`/api/partner-agreements/public/${token}`).then((r) => r.data),
  sendOtp: (token) =>
    publicApi.post(`/api/partner-agreements/public/${token}/send-otp`).then((r) => r.data),
  verifyOtp: (token, otp) =>
    publicApi.post(`/api/partner-agreements/public/${token}/verify-otp`, { otp }).then((r) => r.data),
};
