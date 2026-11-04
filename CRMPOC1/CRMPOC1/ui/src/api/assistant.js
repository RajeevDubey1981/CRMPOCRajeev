import { api } from "./client.js";

export const assistantApi = {
  ask: (message) => api.post("/api/assistant/ask", { message }).then((r) => r.data),
};
